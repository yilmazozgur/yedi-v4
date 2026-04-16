"""Manage a single worker server subprocess for parallel benchmark runs.

Each WorkerServer instance:
  1. Spawns ``python -m yedi_benchmark.gym_server --worker-mode --port PORT``
  2. Starts a virtual X display via Xvfb (so Chrome thinks it's always focused)
  3. Launches Chrome on that virtual display
  4. Polls ``/api/bridge/status`` until the game WebSocket connects
  5. Provides ``ws_agent_url`` for the benchmark runner to create envs against
  6. Cleans up all processes on ``stop()``

The Xvfb approach is critical: Chrome aggressively throttles
requestAnimationFrame in background/unfocused windows (even with
``--disable-backgrounding-occluded-windows`` flags). By giving each
worker its own virtual display, Chrome always believes it is the
focused foreground window and runs rAF at full speed.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from .launch_browser import build_command, find_browser

logger = logging.getLogger("yedi_benchmark.worker_server")

# Display numbers for Xvfb start at this offset to avoid colliding with
# the user's real X display (usually :0 or :1).
_XVFB_DISPLAY_BASE = 100


class WorkerStartupError(Exception):
    """A worker server or its browser tab failed to start."""


class WorkerServer:
    """Lifecycle wrapper around one worker server + browser tab."""

    def __init__(
        self,
        port: int,
        build_dir: Optional[str] = None,
        worker_index: int = 0,
        total_workers: int = 1,
    ):
        self.port = port
        self._build_dir = build_dir or str(
            Path(__file__).resolve().parent.parent / "WebGLBuild"
        )
        self._worker_index = worker_index
        self._total_workers = total_workers
        self._server_proc: Optional[subprocess.Popen] = None
        self._xvfb_proc: Optional[subprocess.Popen] = None
        self._xvfb_display: Optional[str] = None
        self._browser_proc: Optional[subprocess.Popen] = None
        self._user_data_dir: Optional[str] = None

    @property
    def ws_agent_url(self) -> str:
        return f"ws://localhost:{self.port}/ws/agent"

    @property
    def http_base(self) -> str:
        return f"http://localhost:{self.port}"

    # ---- lifecycle ----

    def start(self, timeout: float = 30.0) -> None:
        """Spawn the server process and wait until it accepts HTTP."""
        cmd = [
            sys.executable, "-m", "yedi_benchmark.gym_server",
            "--worker-mode",
            "--port", str(self.port),
            "--host", "127.0.0.1",
            "--build-dir", self._build_dir,
        ]
        self._server_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            close_fds=True,
        )
        self._wait_http_ready(timeout)

    @staticmethod
    def _get_screen_size() -> tuple[int, int]:
        """Best-effort screen resolution detection. Falls back to 1920x1080."""
        # Try xdpyinfo (X11), then xrandr, then give up.
        for cmd, parser in [
            (
                ["xdpyinfo"],
                lambda out: next(
                    (
                        tuple(map(int, tok.split("x")))
                        for line in out.splitlines()
                        if "dimensions:" in line
                        for tok in line.split()
                        if "x" in tok and tok[0].isdigit()
                    ),
                    None,
                ),
            ),
            (
                ["xrandr", "--current"],
                lambda out: next(
                    (
                        tuple(map(int, tok.split("x")))
                        for line in out.splitlines()
                        if " connected " in line and "+" in line
                        for tok in line.split()
                        if "x" in tok and tok[0].isdigit() and "+" not in tok
                    ),
                    None,
                ),
            ),
        ]:
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    size = parser(result.stdout)
                    if size and size[0] > 0 and size[1] > 0:
                        return size
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return (1920, 1080)

    def _tile_flags(self) -> list[str]:
        """Compute --window-position and --window-size for a tiled grid.

        Chrome throttles requestAnimationFrame in occluded (behind another
        window) tabs. The only reliable fix is to make every worker window
        visible simultaneously by tiling them on screen. We use a simple
        grid layout: up to 2 columns, as many rows as needed.
        """
        sw, sh = self._get_screen_size()
        n = self._total_workers
        cols = min(n, 2)
        rows = (n + cols - 1) // cols
        w = sw // cols
        h = sh // rows
        col = self._worker_index % cols
        row = self._worker_index // cols
        x = col * w
        y = row * h
        return [f"--window-position={x},{y}", f"--window-size={w},{h}"]

    def _start_xvfb(self) -> str:
        """Start an Xvfb virtual display for this worker.

        Returns the DISPLAY string (e.g. ":101").
        """
        display_num = _XVFB_DISPLAY_BASE + self._worker_index
        display = f":{display_num}"
        # 960x540x24 matches the Unity canvas size; 24-bit color depth.
        cmd = ["Xvfb", display, "-screen", "0", "960x540x24", "-nolisten", "tcp"]
        self._xvfb_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        # Give Xvfb a moment to create the display socket.
        time.sleep(0.5)
        if self._xvfb_proc.poll() is not None:
            raise WorkerStartupError(
                f"Xvfb failed to start on display {display}. "
                f"Is display {display_num} already in use?"
            )
        self._xvfb_display = display
        logger.info("Worker port %d: Xvfb started on %s", self.port, display)
        return display

    def launch_browser(self) -> None:
        """Launch Chrome for this worker.

        With a single worker, Chrome opens on the real display so the user
        can watch the game. With multiple workers, each gets its own Xvfb
        virtual display so Chrome always thinks it's focused (no rAF
        throttling).
        """
        browser = find_browser()
        if not browser:
            raise WorkerStartupError(
                "Cannot find a Chromium-family browser. Install google-chrome "
                "or pass --browser to launch_browser.py."
            )

        # Per-worker user-data-dir to avoid Chrome profile conflicts.
        self._user_data_dir = tempfile.mkdtemp(
            prefix=f"yedi-worker-{self.port}-"
        )
        url = f"{self.http_base}/?agent=true"

        if self._total_workers == 1:
            # Single worker: visible Chrome on the real display.
            cmd = build_command(browser, url, self._user_data_dir)
            self._browser_proc = subprocess.Popen(cmd, close_fds=True)
        else:
            # Multiple workers: headless via Xvfb to avoid throttling.
            display = self._start_xvfb()
            cmd = build_command(browser, url, self._user_data_dir, extra_flags=[
                "--window-size=960,540",
                "--window-position=0,0",
                # Xvfb has no real GPU — force SwiftShader for WebGL.
                "--use-gl=egl",
                "--use-angle=swiftshader",
                "--ignore-gpu-blocklist",
            ])
            env = os.environ.copy()
            env["DISPLAY"] = display
            self._browser_proc = subprocess.Popen(cmd, close_fds=True, env=env)

    def wait_game_connected(self, timeout: float = 60.0) -> None:
        """Poll /api/bridge/status until game_connected is True."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._server_proc and self._server_proc.poll() is not None:
                raise WorkerStartupError(
                    f"Worker server on port {self.port} died during startup"
                )
            try:
                with urllib.request.urlopen(
                    f"{self.http_base}/api/bridge/status", timeout=2.0
                ) as resp:
                    status = json.loads(resp.read().decode())
                    if status.get("game_connected"):
                        logger.info(
                            "Worker port %d: game connected", self.port
                        )
                        return
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                pass
            time.sleep(1.0)
        raise WorkerStartupError(
            f"Worker port {self.port}: game did not connect within {timeout}s"
        )

    def stop(self) -> None:
        """Terminate browser, Xvfb, and server processes."""
        for label, proc in [
            ("browser", self._browser_proc),
            ("xvfb", self._xvfb_proc),
            ("server", self._server_proc),
        ]:
            if proc is None:
                continue
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
            except Exception as e:
                logger.warning(
                    "Worker port %d: failed to stop %s: %s",
                    self.port, label, e,
                )
        self._browser_proc = None
        self._xvfb_proc = None
        self._xvfb_display = None
        self._server_proc = None

        # Clean up the temporary Chrome profile directory.
        if self._user_data_dir:
            try:
                shutil.rmtree(self._user_data_dir, ignore_errors=True)
            except Exception:
                pass
            self._user_data_dir = None

    # ---- internals ----

    def _wait_http_ready(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._server_proc.poll() is not None:
                stderr = self._server_proc.stderr.read().decode() if self._server_proc.stderr else ""
                raise WorkerStartupError(
                    f"Worker server on port {self.port} exited immediately. "
                    f"stderr: {stderr[:500]}"
                )
            try:
                with urllib.request.urlopen(
                    f"{self.http_base}/api/bridge/status", timeout=2.0
                ) as resp:
                    if resp.status == 200:
                        logger.info(
                            "Worker port %d: HTTP ready", self.port
                        )
                        return
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(0.5)
        raise WorkerStartupError(
            f"Worker server on port {self.port} did not become ready "
            f"within {timeout}s"
        )
