"""Page routes for the dashboard.

Each route renders a Jinja2 template and lets vanilla JS in the browser pull
data from the JSON API endpoints. There's no server-side data fetching here —
templates are dumb shells that the JS hydrates on load.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


WEB_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

_templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


# Page registry — single source of truth for left-nav generation
PAGES = [
    {"slug": "home",       "title": "Home",       "path": "/",          "template": "index.html"},
    {"slug": "agents",     "title": "Agents",     "path": "/agents",    "template": "agents.html"},
    {"slug": "prompts",    "title": "Prompts",    "path": "/prompts",   "template": "prompts.html"},
    {"slug": "benchmark",  "title": "Benchmark",  "path": "/benchmark", "template": "benchmark.html"},
    {"slug": "runs",       "title": "Runs",       "path": "/runs",      "template": "runs.html"},
    {"slug": "game",       "title": "Game",       "path": "/game",      "template": "game.html"},
    {"slug": "analysis",   "title": "Analysis",   "path": "/analysis",  "template": "analysis.html"},
]


def _render(request: Request, slug: str) -> HTMLResponse:
    page = next((p for p in PAGES if p["slug"] == slug), None)
    if page is None or page["template"] is None:
        return HTMLResponse(f"unknown page: {slug}", status_code=404)
    return _templates.TemplateResponse(
        request,
        page["template"],
        {
            "pages": PAGES,
            "active_slug": slug,
            "page_title": page["title"],
        },
    )


def mount_web_ui(app: FastAPI) -> None:
    """Mount Jinja templates + static files + page routes on the FastAPI app."""
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def page_home(request: Request) -> HTMLResponse:
        return _render(request, "home")

    @app.get("/agents", response_class=HTMLResponse, include_in_schema=False)
    def page_agents(request: Request) -> HTMLResponse:
        return _render(request, "agents")

    @app.get("/prompts", response_class=HTMLResponse, include_in_schema=False)
    def page_prompts(request: Request) -> HTMLResponse:
        return _render(request, "prompts")

    @app.get("/benchmark", response_class=HTMLResponse, include_in_schema=False)
    def page_benchmark(request: Request) -> HTMLResponse:
        return _render(request, "benchmark")

    @app.get("/runs", response_class=HTMLResponse, include_in_schema=False)
    def page_runs(request: Request) -> HTMLResponse:
        return _render(request, "runs")

    @app.get("/game", response_class=HTMLResponse, include_in_schema=False)
    def page_game(request: Request) -> HTMLResponse:
        return _render(request, "game")

    @app.get("/analysis", response_class=HTMLResponse, include_in_schema=False)
    def page_analysis(request: Request) -> HTMLResponse:
        return _render(request, "analysis")
