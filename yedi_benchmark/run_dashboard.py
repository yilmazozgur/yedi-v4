#!/usr/bin/env python3
"""Single entry point for the Yedi benchmark dashboard.

Starts the FastAPI server (REST API + dashboard pages + WebSocket bridge)
and optionally pops a browser tab at the home page once it's reachable.

Usage:
    python -m yedi_benchmark.run_dashboard
    python -m yedi_benchmark.run_dashboard --no-browser
    python -m yedi_benchmark.run_dashboard --port 8001 --build-dir ../WebGLBuild
"""

from __future__ import annotations

import argparse
import logging
import os
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

from .gym_server import _reconcile_orphan_runs, app, setup_static_files

logger = logging.getLogger("yedi.dashboard")

# Resolve the default WebGL build relative to the repo (parent of this package),
# so the launcher works no matter what directory you cd'd into.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_BUILD_DIR = str(_REPO_ROOT / "WebGLBuild")


def _wait_then_open_browser(url: str, timeout_s: float = 10.0) -> None:
    """Poll the home page until it answers, then open it in the browser."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as resp:
                if resp.status == 200:
                    break
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.2)
    else:
        logger.warning("dashboard did not become reachable within %.1fs — skipping browser open", timeout_s)
        return
    try:
        webbrowser.open(url)
    except Exception as exc:  # pragma: no cover — best-effort
        logger.warning("could not open browser: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Yedi benchmark dashboard launcher")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--build-dir",
        default=os.environ.get("YEDI_WEBGL_BUILD", _DEFAULT_BUILD_DIR),
        help="Path to the Unity WebGL build (for the embedded /game iframe). "
             "Defaults to <repo>/WebGLBuild regardless of CWD.",
    )
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't auto-open the dashboard in a browser")
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level.upper())

    setup_static_files(os.path.abspath(args.build_dir))
    _reconcile_orphan_runs()

    url = f"http://{args.host}:{args.port}/"
    logger.info("Yedi dashboard:    %s", url)
    logger.info("API docs:          %s/docs", url.rstrip("/"))
    logger.info("Game iframe URL:   %s/game", url.rstrip("/"))
    logger.info("Agent WebSocket:   ws://%s:%s/ws/agent", args.host, args.port)
    logger.info("Game WebSocket:    ws://%s:%s/ws/game", args.host, args.port)

    if not args.no_browser:
        threading.Thread(
            target=_wait_then_open_browser,
            args=(url,),
            daemon=True,
        ).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
