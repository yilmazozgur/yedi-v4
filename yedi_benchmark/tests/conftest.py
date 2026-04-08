"""Shared pytest fixtures.

The registry tests need an isolated data directory so they don't trample the
real yedi_benchmark/data/ tree (or each other). We point YEDI_DATA_DIR and
YEDI_RUNS_DIR at a tmp_path subdir per test.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    """Redirect agent + prompt registries at a fresh tmp directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("YEDI_DATA_DIR", str(data_dir))
    return data_dir


@pytest.fixture
def isolated_runs_dir(tmp_path, monkeypatch):
    """Redirect the run registry at a fresh tmp directory."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    monkeypatch.setenv("YEDI_RUNS_DIR", str(runs_dir))
    return runs_dir
