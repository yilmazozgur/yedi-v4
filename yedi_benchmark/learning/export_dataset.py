"""CLI: walk a logs directory and export a Parquet BC dataset.

Example:

    python -m yedi_benchmark.learning.export_dataset \\
        --logs-dir logs \\
        --out datasets/yedi_bc.parquet \\
        --sources human greedy

Reads every ``episode_*/events.jsonl`` under ``--logs-dir``, featurizes
step records, and writes a single Parquet file. An ``agent_source``
column lets a BC trainer filter by provider (e.g. train on human only,
or mix human+greedy with ratios).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

import pyarrow as pa
import pyarrow.parquet as pq

from .featurizer import (
    DIMENSIONS_DIM,
    NUM_ACTIONS,
    NUM_SLOTS,
    SLOT_FEATURE_DIM,
    WORD_HASH_DIM,
    featurize_episode,
)


# Pinning the schema (instead of letting Arrow infer) catches subtle drift
# — e.g. an old log with mana stored as int would otherwise produce a
# Parquet file with an incompatible column type.
SCHEMA = pa.schema([
    ("episode_id",      pa.string()),
    ("step",            pa.int32()),
    ("agent_name",      pa.string()),
    ("agent_source",    pa.string()),
    ("config_key",      pa.string()),
    ("action",          pa.int16()),
    ("reward",          pa.float32()),
    ("terminated",      pa.bool_()),
    ("truncated",       pa.bool_()),
    ("mana",            pa.float32()),
    ("mana_max",        pa.float32()),
    ("timer_remaining", pa.float32()),
    ("beat_phase",      pa.float32()),
    ("slots",           pa.list_(pa.float32(), NUM_SLOTS * SLOT_FEATURE_DIM)),
    ("word_hash",       pa.list_(pa.float32(), NUM_SLOTS * WORD_HASH_DIM)),
    ("dims_active",     pa.list_(pa.float32(), DIMENSIONS_DIM)),
    ("action_mask",     pa.list_(pa.int8(), NUM_ACTIONS)),
])


def _iter_episode_files(logs_dir: Path) -> Iterable[Path]:
    for d in sorted(logs_dir.iterdir()):
        if not d.is_dir() or not d.name.startswith("episode_"):
            continue
        events_path = d / "events.jsonl"
        if events_path.exists():
            yield events_path


def _read_events(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                # Skip truncated last line from a crashed run rather
                # than losing the whole episode — BC data is resilient
                # to a few dropped steps.
                continue
    return out


def _episode_quality(events: list[dict]) -> dict:
    """Inspect an events stream for trajectory-completion markers.

    The replay logger writes ``episode_end`` only when the runner
    cleanly shuts down the episode. An ``episode_end`` with
    ``game_over=True`` additionally means the game terminated
    naturally (mana hit zero or step cap reached) instead of the user
    cancelling from the browser. BC trainers should normally require
    both, since partial trajectories bias the state distribution the
    model sees at the end of an episode.
    """
    end = next((e for e in reversed(events) if e.get("type") == "episode_end"), None)
    return {
        "has_end": end is not None,
        "game_over": bool(end.get("game_over", False)) if end else False,
    }


def export(
    logs_dir: Path,
    out_path: Path,
    *,
    sources: set[str] | None = None,
    min_steps: int = 1,
    require_end: bool = False,
    require_game_over: bool = False,
) -> dict:
    """Write the Parquet dataset. Returns a summary dict for the CLI.

    ``require_end=True``       → skip orphaned episodes (no ``episode_end``).
    ``require_game_over=True`` → also skip episodes that ended via user
                                 cancel rather than a natural game-end.
    """
    rows: list[dict] = []
    ep_counts: dict[str, int] = {}
    skipped_short = 0
    skipped_filtered = 0
    skipped_no_end = 0
    skipped_not_game_over = 0

    for events_path in _iter_episode_files(logs_dir):
        events = _read_events(events_path)
        quality = _episode_quality(events)
        if require_end and not quality["has_end"]:
            skipped_no_end += 1
            continue
        if require_game_over and not quality["game_over"]:
            skipped_not_game_over += 1
            continue

        ep_rows = list(featurize_episode(events))
        if not ep_rows:
            continue

        agent_source = ep_rows[0]["agent_source"]
        if sources is not None and agent_source not in sources:
            skipped_filtered += 1
            continue
        if len(ep_rows) < min_steps:
            skipped_short += 1
            continue

        rows.extend(ep_rows)
        ep_counts[agent_source] = ep_counts.get(agent_source, 0) + 1

    if not rows:
        raise SystemExit("No featurizable episodes found — is --logs-dir correct?")

    # Column-wise dict is what pa.Table.from_pydict wants. Keep int/bool
    # columns as-is; cast only where Arrow's type inference is wrong
    # (it wouldn't infer float32 for the list columns, for instance).
    columns = {name: [r[name] for r in rows] for name in SCHEMA.names}
    table = pa.Table.from_pydict(columns, schema=SCHEMA)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out_path, compression="zstd")

    return {
        "out_path": str(out_path),
        "num_rows": len(rows),
        "num_episodes": sum(ep_counts.values()),
        "episodes_by_source": ep_counts,
        "skipped_filtered": skipped_filtered,
        "skipped_short": skipped_short,
        "skipped_no_end": skipped_no_end,
        "skipped_not_game_over": skipped_not_game_over,
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--logs-dir", type=Path, default=Path("logs"),
                   help="Directory containing episode_*/events.jsonl (default: logs)")
    p.add_argument("--out", type=Path, required=True,
                   help="Output Parquet path (will be created)")
    p.add_argument("--sources", nargs="*",
                   choices=["human", "greedy", "random", "llm", "unknown"],
                   help="Only include episodes from these agent sources")
    p.add_argument("--min-steps", type=int, default=1,
                   help="Skip episodes with fewer featurizable steps than this")
    p.add_argument("--require-end", action="store_true",
                   help="Only include episodes that wrote an episode_end record "
                        "(drops orphaned/crashed sessions)")
    p.add_argument("--require-game-over", action="store_true",
                   help="Only include episodes that ended naturally "
                        "(mana-zero or step cap). Implies --require-end.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    sources = set(args.sources) if args.sources else None
    summary = export(
        args.logs_dir, args.out,
        sources=sources, min_steps=args.min_steps,
        require_end=args.require_end or args.require_game_over,
        require_game_over=args.require_game_over,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
