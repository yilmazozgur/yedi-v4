"""Path resolution for registry storage.

Default layout (relative to project root):
  yedi_benchmark/data/
    agents.json     — agent registry
    prompts.json    — prompt registry
  logs/
    runs/           — one file per RunRecord

Tests override the data dir via the YEDI_DATA_DIR environment variable so each
test can use a tmp_path fixture without touching real state.
"""

from __future__ import annotations

import os
from pathlib import Path


_PACKAGE_ROOT = Path(__file__).resolve().parent.parent  # yedi_benchmark/
_PROJECT_ROOT = _PACKAGE_ROOT.parent                    # repo root


def get_data_dir() -> Path:
    """Return the directory where agents.json and prompts.json live."""
    override = os.environ.get("YEDI_DATA_DIR")
    if override:
        path = Path(override)
    else:
        path = _PACKAGE_ROOT / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_runs_dir() -> Path:
    """Return the directory where RunRecord JSON files are stored."""
    override = os.environ.get("YEDI_RUNS_DIR")
    if override:
        path = Path(override)
    else:
        path = _PROJECT_ROOT / "logs" / "runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_root() -> Path:
    """Return the directory where per-episode artifacts live.

    Episode paths stored in RunRecord.results[*].episodes[*].episode_log_path
    are recorded relative to the project root as ``logs/episode_...``;
    this helper lets callers resolve and safety-check those paths when
    cascading delete.
    """
    override = os.environ.get("YEDI_LOGS_ROOT")
    if override:
        return Path(override).resolve()
    return (_PROJECT_ROOT / "logs").resolve()
