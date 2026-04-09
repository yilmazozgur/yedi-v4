"""Smoke tests for the dashboard web UI.

These tests don't render JavaScript — they just verify that:
  - every page route returns 200 with the layout shell present
  - the left-nav points at every registered page
  - shared static assets (CSS + JS) are served from /static/
  - the active-slug highlight works
  - the gym_server wires both the API routers and the web UI together so the
    dashboard can talk to the same FastAPI app that hosts /api/...

The page bodies hydrate via fetch() to the API endpoints, so as long as the
template + base layout + JS file load, the rest is exercised by test_api.py.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yedi_benchmark.api import mount_api_routers
from yedi_benchmark.api import deps as api_deps
from yedi_benchmark.api import run_executor as run_executor_mod
from yedi_benchmark.web import mount_web_ui
from yedi_benchmark.web.pages import PAGES


@pytest.fixture
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    runs_dir = tmp_path / "runs"
    data_dir.mkdir()
    runs_dir.mkdir()
    monkeypatch.setenv("YEDI_DATA_DIR", str(data_dir))
    monkeypatch.setenv("YEDI_RUNS_DIR", str(runs_dir))

    api_deps.reset_registry_singletons()
    run_executor_mod.reset_run_executor()

    app = FastAPI()
    mount_api_routers(app)
    mount_web_ui(app)

    with TestClient(app) as c:
        yield c


# ──────────────────────────────────────────────────────────────────────────────
# Page route smoke tests
# ──────────────────────────────────────────────────────────────────────────────


PAGE_ROUTES = [
    ("/",          "Home"),
    ("/agents",    "Agents"),
    ("/prompts",   "Prompts"),
    ("/benchmark", "Benchmark"),
    ("/runs",      "Runs"),
    ("/game",      "Game"),
    ("/analysis",  "Analysis"),
]


class TestPageRoutes:
    @pytest.mark.parametrize("path,title", PAGE_ROUTES)
    def test_page_returns_html_with_layout(self, client, path, title):
        r = client.get(path)
        assert r.status_code == 200
        body = r.text
        # Layout shell from base.html
        assert '<aside class="sidebar">' in body
        assert '<main class="content">' in body
        assert "/static/css/app.css" in body
        assert "/static/js/app.js" in body
        # Page-specific title shown in <h1> and <title>
        assert f"<h1>{title}</h1>" in body
        assert f"Yedi Benchmark · {title}" in body

    def test_left_nav_lists_every_registered_page(self, client):
        r = client.get("/")
        assert r.status_code == 200
        for page in PAGES:
            # Each page registry entry should appear as a nav-link href
            assert f'href="{page["path"]}"' in r.text
            assert f">\n                    {page['title']}\n                </a>" in r.text or \
                   f'>{page["title"]}</a>' in r.text or \
                   page["title"] in r.text

    def test_active_slug_highlight(self, client):
        r = client.get("/agents")
        assert r.status_code == 200
        # The agents nav-link should be the only is-active one
        assert 'href="/agents"\n                   class="nav-link is-active"' in r.text or \
               'class="nav-link is-active"' in r.text and 'href="/agents"' in r.text

    def test_unknown_page_via_render_helper_404(self, client):
        # /not-a-page is just unmounted — FastAPI returns 404 itself
        r = client.get("/not-a-page")
        assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# Static asset serving
# ──────────────────────────────────────────────────────────────────────────────


class TestStaticAssets:
    def test_css_served(self, client):
        r = client.get("/static/css/app.css")
        assert r.status_code == 200
        assert "Yedi Benchmark dashboard" in r.text
        assert "--accent" in r.text  # CSS custom property

    def test_js_served(self, client):
        r = client.get("/static/js/app.js")
        assert r.status_code == 200
        assert "YediApp" in r.text
        assert "apiRequest" in r.text

    def test_missing_static_asset_404(self, client):
        r = client.get("/static/does-not-exist.png")
        assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# Page-specific markup smoke tests
# ──────────────────────────────────────────────────────────────────────────────


class TestPageContent:
    def test_home_has_stat_grid_and_recent_runs_table(self, client):
        r = client.get("/")
        assert "stat-grid" in r.text
        assert "recent-runs" in r.text

    def test_agents_page_has_form_modal(self, client):
        r = client.get("/agents")
        assert 'id="agent-modal"' in r.text
        assert 'id="agent-form"' in r.text
        assert "btn-new-agent" in r.text

    def test_prompts_page_has_clone_modal(self, client):
        r = client.get("/prompts")
        assert 'id="prompt-modal"' in r.text
        assert 'id="clone-modal"' in r.text
        assert "btn-new-prompt" in r.text

    def test_benchmark_page_has_config_picker(self, client):
        r = client.get("/benchmark")
        assert "config-picker" in r.text
        assert 'id="b-mode"' in r.text
        assert 'value="metadata-b"' in r.text  # default mode

    def test_runs_page_has_runs_table(self, client):
        r = client.get("/runs")
        assert "runs-tbody" in r.text
        assert 'id="run-detail-card"' in r.text

    def test_runs_page_has_live_trace_card(self, client):
        r = client.get("/runs")
        # Trace UI surface
        assert 'id="run-trace-card"' in r.text
        assert 'id="trace-stream"' in r.text
        assert 'id="trace-system-host"' in r.text
        assert 'id="trace-status"' in r.text
        # Polling JS hooks
        assert "startTrace" in r.text
        assert "pollTrace" in r.text
        assert "/trace?since=" in r.text

    def test_game_page_iframes_embed(self, client):
        r = client.get("/game")
        assert 'src="/game/embed"' in r.text
        assert 'id="game-frame"' in r.text

    def test_analysis_page_loads_plotly(self, client):
        r = client.get("/analysis")
        assert "plot.ly" in r.text
        assert 'id="dimension-charts"' in r.text

    def test_analysis_page_has_filter_controls(self, client):
        """Every filter control the Analysis JS wires up must exist in the
        rendered template — catches accidental id renames or deletions that
        would silently break the page's load-time wiring."""
        r = client.get("/analysis")
        expected_ids = [
            "a-mode-filter",
            "a-agent-filter",
            "a-max-steps-filter",
            "a-show-previews-filter",
            "a-perfect-memory-filter",
            "a-tier-buttons",
            "a-config-picker",
            "a-reset-filters",
            "a-filter-summary",
            "a-stat-runs",
            "a-stat-episodes",
            "a-stat-mean-mana",
            "a-stat-best-mana",
            "a-ablation-card",
            "a-ablation-charts",
            "a-distribution-card",
            "a-distribution-chart",
            "leaderboard-tbody",
        ]
        for el_id in expected_ids:
            assert f'id="{el_id}"' in r.text, f"missing filter control: {el_id}"


# ──────────────────────────────────────────────────────────────────────────────
# Wiring: dashboard + API live on the same app
# ──────────────────────────────────────────────────────────────────────────────


class TestDashboardWiring:
    def test_api_endpoints_still_work_alongside_pages(self, client):
        # Page routes don't shadow API routes
        agents_page = client.get("/agents")
        agents_api = client.get("/api/agents")
        assert agents_page.status_code == 200
        assert agents_api.status_code == 200
        assert agents_page.headers["content-type"].startswith("text/html")
        assert agents_api.headers["content-type"].startswith("application/json")

    def test_runs_active_endpoint_used_by_poller(self, client):
        # The base layout's poller calls this — it must answer when idle
        r = client.get("/api/runs/active")
        assert r.status_code == 200
        assert r.json() == {
            "active": False,
            "run_id": None,
            "status": None,
            "episodes_done": 0,
            "episodes_total": 0,
        }

    def test_bridge_status_endpoint_used_by_poller(self, client):
        # The other sidebar poller — must answer with the disconnected shape
        # by default (no WebSocket open in tests)
        r = client.get("/api/bridge/status")
        assert r.status_code == 200
        body = r.json()
        assert body["game_connected"] is False
        assert body["agent_connected"] is False


class TestBridgeUiBindings:
    def test_base_layout_has_bridge_status_pill(self, client):
        r = client.get("/")
        assert 'id="bridge-status"' in r.text
        assert 'id="bridge-status-body"' in r.text
        assert "Game bridge" in r.text

    def test_app_js_polls_bridge_endpoint(self, client):
        r = client.get("/static/js/app.js")
        assert "/api/bridge/status" in r.text
        assert "renderBridgeStatus" in r.text
        assert "onBridgeStatusChange" in r.text

    def test_benchmark_page_has_no_game_card(self, client):
        r = client.get("/benchmark")
        assert 'id="b-no-game-card"' in r.text
        assert "applyBridgeState" in r.text
