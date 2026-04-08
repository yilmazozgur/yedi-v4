"""Web UI dashboard — Jinja2 templates + vanilla JS, mounted on the FastAPI
app via mount_web_ui().
"""

from .pages import mount_web_ui

__all__ = ["mount_web_ui"]
