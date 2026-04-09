"""Tests for the Chromium launcher helper.

We don't actually launch a browser in tests — we cover argv construction,
URL defaulting, browser auto-detection, and the dry-run path. The throttle
flags are the load-bearing piece (the whole reason this script exists),
so we assert on their presence explicitly.
"""

from __future__ import annotations

import sys

import pytest

from yedi_benchmark import launch_browser
from yedi_benchmark.launch_browser import (
    THROTTLING_DISABLE_FLAGS,
    build_command,
    main,
    parse_args,
)


class TestBuildCommand:
    def test_includes_all_throttling_flags(self):
        cmd = build_command(
            browser="/usr/bin/google-chrome",
            url="http://localhost:8000/?agent=true",
            user_data_dir="/tmp/yedi-test",
        )
        for flag in THROTTLING_DISABLE_FLAGS:
            assert flag in cmd, (
                f"throttling flag {flag!r} missing — this is the whole "
                f"reason the launcher exists, regression."
            )

    def test_url_is_last_positional(self):
        """Chromium expects the URL after all flags."""
        cmd = build_command(
            browser="/usr/bin/google-chrome",
            url="http://localhost:8000/?agent=true",
            user_data_dir="/tmp/yedi-test",
        )
        assert cmd[-1] == "http://localhost:8000/?agent=true"

    def test_user_data_dir_passed_through(self):
        cmd = build_command(
            browser="/usr/bin/google-chrome",
            url="http://x/",
            user_data_dir="/some/path",
        )
        assert "--user-data-dir=/some/path" in cmd

    def test_browser_is_first_argv(self):
        cmd = build_command(
            browser="/usr/bin/google-chrome",
            url="http://x/",
            user_data_dir="/tmp/y",
        )
        assert cmd[0] == "/usr/bin/google-chrome"

    def test_extra_flags_appended_before_url(self):
        cmd = build_command(
            browser="/usr/bin/google-chrome",
            url="http://x/",
            user_data_dir="/tmp/y",
            extra_flags=["--window-size=1280,720"],
        )
        assert "--window-size=1280,720" in cmd
        # URL must still be last so chromium picks it up as the page to open
        assert cmd[-1] == "http://x/"


class TestParseArgs:
    def test_default_port_8000(self):
        ns = parse_args([])
        assert ns.port == 8000
        assert ns.url is None

    def test_url_overrides_port(self):
        ns = parse_args(["--url", "http://example.com/"])
        assert ns.url == "http://example.com/"

    def test_browser_override(self):
        ns = parse_args(["--browser", "/opt/firefox"])
        assert ns.browser == "/opt/firefox"

    def test_dry_run_flag(self):
        ns = parse_args(["--dry-run"])
        assert ns.dry_run is True


class TestMainDryRun:
    """Smoke-test the full path without actually spawning a browser."""

    def test_dry_run_with_explicit_browser_succeeds(self, tmp_path, capsys):
        # Use sys.executable as a stand-in for "a binary that definitely
        # exists" — we never actually exec it because of --dry-run.
        rc = main([
            "--dry-run",
            "--browser", sys.executable,
            "--user-data-dir", str(tmp_path),
        ])
        assert rc == 0

    def test_dry_run_with_missing_browser_fails(self, tmp_path):
        rc = main([
            "--dry-run",
            "--browser", "/definitely/not/a/real/browser/binary",
            "--user-data-dir", str(tmp_path),
        ])
        assert rc == 1

    def test_dry_run_uses_port_in_default_url(self, tmp_path, monkeypatch):
        # Force find_browser to return our fake so the test works on hosts
        # without Chrome installed (CI containers etc.).
        monkeypatch.setattr(launch_browser, "find_browser", lambda: sys.executable)
        # Capture the argv that build_command produces by intercepting it.
        captured = {}
        real_build = launch_browser.build_command

        def spy(browser, url, user_data_dir, extra_flags=None):
            captured["url"] = url
            return real_build(browser, url, user_data_dir, extra_flags)

        monkeypatch.setattr(launch_browser, "build_command", spy)
        rc = main(["--dry-run", "--port", "9999", "--user-data-dir", str(tmp_path)])
        assert rc == 0
        assert captured["url"] == "http://localhost:9999/?agent=true"

    def test_main_returns_1_when_no_browser_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr(launch_browser, "find_browser", lambda: None)
        rc = main(["--dry-run", "--user-data-dir", str(tmp_path)])
        assert rc == 1
