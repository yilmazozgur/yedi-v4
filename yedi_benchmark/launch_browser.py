"""Launch Chrome with WebGL-friendly flags for benchmark runs.

Why this exists: when the benchmark browser tab is hidden, occluded, or
backgrounded, modern browsers throttle ``requestAnimationFrame`` from 60Hz
down to ~1Hz and can suspend the WebGL context entirely. The Unity main
loop ticks on rAF, so a throttled tab makes ``draw_card`` (and every other
agent command) take >30s and trip the gym server's per-command timeout.
The user-visible symptom is "bridge error for draw_card: timeout" followed
by the consecutive-failure budget aborting the run.

This script launches Chrome (or Chromium / Brave / Edge — anything Chrome
based) with the relevant throttling-disable flags so a benchmark run keeps
ticking even if the user moves the window behind something else, or if
their OS marks it as occluded.

Usage::

    python -m yedi_benchmark.launch_browser
    python -m yedi_benchmark.launch_browser --port 8001
    python -m yedi_benchmark.launch_browser --url http://example.com/?agent=true
    python -m yedi_benchmark.launch_browser --browser /path/to/chromium

The script does NOT replace the gym server — start that separately first
(e.g. ``python -m yedi_benchmark.gym_server``).
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger("yedi_benchmark.launch_browser")


# Chromium-family flags that prevent the WebGL tab from being throttled.
#
# Each flag is documented inline because they all sound generic but each
# one closes a specific throttling path:
#   - background-timer-throttling: rate-limits setTimeout/setInterval in
#     hidden tabs to 1/sec. Doesn't directly throttle rAF but does throttle
#     WebSocket reconnect logic if it leans on timers.
#   - renderer-backgrounding: suspends a renderer process entirely after
#     the tab has been backgrounded for some time.
#   - backgrounding-occluded-windows: same as above but specifically for
#     windows that are *occluded* (covered by another window) rather than
#     hidden tabs. This is the one most users hit on a multi-monitor setup
#     where the Yedi window slips behind another app on the same monitor.
#   - calculate-native-win-occlusion: a Windows-specific feature that
#     marks windows as occluded eagerly. Disabling it stops Chrome from
#     even noticing occlusion in the first place. Harmless on Linux/Mac.
#   - features=IntensiveWakeUpThrottling: this is the deeper rAF throttle
#     introduced in Chrome 87+. Disabling it keeps rAF at 60Hz even for
#     long-backgrounded tabs.
#
# We pass them in the order Chrome's command-line parser likes (positional
# flags first, then --features last).
THROTTLING_DISABLE_FLAGS = [
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows",
    # Allow the AudioContext anti-throttle keepalive to start without a
    # user gesture. Without this, Chrome suspends the AudioContext until
    # the user clicks — which never happens in headless worker tabs.
    "--autoplay-policy=no-user-gesture-required",
    # Skip Chrome's first-run welcome page. Without this, a fresh
    # user-data-dir shows the setup flow instead of navigating to the URL.
    "--no-first-run",
    "--disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling",
]


# Candidate executable names by platform. We try each in order and use
# the first one shutil.which can resolve. The user can always override
# with --browser.
CANDIDATES_LINUX = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "brave-browser",
    "microsoft-edge",
]
CANDIDATES_DARWIN = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
CANDIDATES_WINDOWS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Chromium\Application\chrome.exe",
]


def find_browser() -> str | None:
    """Locate a Chromium-family browser binary, or return None."""
    if sys.platform.startswith("linux"):
        for name in CANDIDATES_LINUX:
            path = shutil.which(name)
            if path:
                return path
    elif sys.platform == "darwin":
        for path in CANDIDATES_DARWIN:
            if os.path.isfile(path):
                return path
        # Also check $PATH for the rare case the user has a CLI alias.
        for name in ("google-chrome", "chromium"):
            path = shutil.which(name)
            if path:
                return path
    elif sys.platform.startswith("win"):
        for path in CANDIDATES_WINDOWS:
            if os.path.isfile(path):
                return path
    return None


def build_command(
    browser: str,
    url: str,
    user_data_dir: str,
    extra_flags: list[str] | None = None,
) -> list[str]:
    """Construct the full argv to launch the browser with anti-throttle flags.

    The user-data-dir is critical: without it, Chrome reuses the user's
    main profile, and the throttling-disable flags only apply to *new*
    Chrome processes. With a separate user-data-dir we always get a fresh
    process that actually honors the flags. We also avoid clobbering the
    user's normal session.
    """
    cmd = [browser]
    cmd.extend(THROTTLING_DISABLE_FLAGS)
    cmd.append(f"--user-data-dir={user_data_dir}")
    # --new-window forces a fresh window so the user always sees a separate
    # icon in the dock/taskbar that's clearly "the benchmark Chrome".
    cmd.append("--new-window")
    if extra_flags:
        cmd.extend(extra_flags)
    cmd.append(url)
    return cmd


def default_user_data_dir() -> str:
    """A persistent dir under the OS temp area so Chrome doesn't redownload
    its first-run state every launch. Per-user, not per-run."""
    return str(Path(tempfile.gettempdir()) / "yedi-benchmark-chrome-profile")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m yedi_benchmark.launch_browser",
        description=(
            "Launch a Chromium-family browser with throttling disabled, "
            "pointed at the Yedi benchmark agent URL. Run the gym server "
            "first (python -m yedi_benchmark.gym_server)."
        ),
    )
    p.add_argument(
        "--url",
        default=None,
        help=(
            "Full URL to open. Defaults to "
            "http://localhost:{port}/?agent=true. Overrides --port."
        ),
    )
    p.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Gym server port (used to build the default URL). Default: 8000.",
    )
    p.add_argument(
        "--browser",
        default=None,
        help=(
            "Path to the browser binary. If omitted, the script auto-detects "
            "Chrome / Chromium / Brave / Edge for the current platform."
        ),
    )
    p.add_argument(
        "--user-data-dir",
        default=None,
        help=(
            "Chrome user-data-dir. Defaults to a persistent temp directory "
            "so the throttling-disable flags actually take effect (Chrome "
            "will only honor them on a fresh process)."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command instead of executing it. Useful for debugging.",
    )
    p.add_argument(
        "extra",
        nargs="*",
        help=(
            "Extra flags to pass through to the browser, e.g. "
            "-- --window-size=1280,720"
        ),
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args(argv)

    browser = args.browser or find_browser()
    if not browser:
        logger.error(
            "could not find a Chromium-family browser. Pass --browser /path/to/chrome "
            "or install google-chrome / chromium."
        )
        return 1
    if not os.path.isfile(browser) and not shutil.which(browser):
        logger.error("browser binary not found: %s", browser)
        return 1

    url = args.url or f"http://localhost:{args.port}/?agent=true"
    user_data_dir = args.user_data_dir or default_user_data_dir()
    os.makedirs(user_data_dir, exist_ok=True)

    cmd = build_command(browser, url, user_data_dir, extra_flags=args.extra or None)

    logger.info("Launching: %s", " ".join(cmd))
    logger.info(
        "Anti-throttle flags active: tab can be backgrounded without timing out."
    )
    logger.info("Open the dashboard at the URL above and start a benchmark run.")

    if args.dry_run:
        return 0

    # Use Popen so we don't block on the browser process — the user wants
    # the shell back. The browser will keep running in the background.
    try:
        subprocess.Popen(cmd, close_fds=True)
    except OSError as e:
        logger.error("failed to launch browser: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
