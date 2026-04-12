#!/usr/bin/env python3
"""
Validate card initialization integrity across benchmark episodes.

Checks for the Start()/EnsureActivated() race condition:
- Color mode: black (0,0,0) cards on fresh draws
- Shape mode: sentinel shape_index=8 on fresh draws
- Number mode: number_value=0 on fresh draws (non-super, add mode)

Usage:
    python validate_cards.py [LOG_DIR]

Defaults to logs/ in the project root.  Exits 0 if clean, 1 if anomalies found.
"""

import json
import sys
import os
from pathlib import Path
from collections import defaultdict


def analyze_episode(events_path: Path) -> dict:
    """Analyze a single episode for card init anomalies."""
    with open(events_path) as f:
        events = [json.loads(line) for line in f if line.strip()]

    results = {
        "path": str(events_path),
        "total_steps": 0,
        "total_draws": 0,
        "failed_draws": 0,
        "black_color_draws": 0,
        "sentinel_shape_draws": 0,
        "zero_number_draws": 0,
        "anomaly_steps": [],
    }

    # Detect mode from episode_start config
    config = {}
    for e in events:
        if e.get("type") == "episode_start":
            config = e.get("config", {})
            break

    modes = config.get("modes", {})

    for e in events:
        if e.get("type") != "step":
            continue
        results["total_steps"] += 1

        obs = e.get("observation", {})
        cmd = e.get("command", {})
        action = e.get("action", -1)

        # Only check draw_card results
        cmd_type = cmd.get("type", "") if isinstance(cmd, dict) else ""
        if action != 0 and cmd_type != "draw_card":
            continue

        results["total_draws"] += 1

        # Get slot_new — could be array or dict format
        slots = obs.get("slots", [])
        if not slots:
            continue

        # Array format: slot_new is index 6, each slot is 11-element array
        # [occupied, card_mana, merges_done, is_super, number_value,
        #  color_r, color_g, color_b, shape_index, memory_hidden, beat_phase]
        if isinstance(slots, list) and isinstance(slots[0], list):
            slot_new = slots[6] if len(slots) > 6 else slots[-1]
            occupied = slot_new[0] > 0
            if not occupied:
                results["failed_draws"] += 1
                results["anomaly_steps"].append({
                    "step": e.get("step", "?"),
                    "type": "failed_draw",
                })
                continue

            merges = slot_new[2]
            if merges > 0:
                continue  # Not a fresh draw

            number_val = slot_new[4]
            color_r, color_g, color_b = slot_new[5], slot_new[6], slot_new[7]
            shape_idx = slot_new[8]

            # Check for black/clear color (all zeros)
            if "color" in modes:
                if color_r == 0 and color_g == 0 and color_b == 0:
                    results["black_color_draws"] += 1
                    results["anomaly_steps"].append({
                        "step": e.get("step", "?"),
                        "type": "black_color",
                        "color": [color_r, color_g, color_b],
                    })

            # Check for sentinel shape (index 8)
            if "shape" in modes:
                if shape_idx == 8:
                    results["sentinel_shape_draws"] += 1
                    results["anomaly_steps"].append({
                        "step": e.get("step", "?"),
                        "type": "sentinel_shape",
                        "shape_index": shape_idx,
                    })

            # Check for zero number on fresh draw in add mode
            if modes.get("number") == "add":
                if number_val == 0:
                    results["zero_number_draws"] += 1
                    results["anomaly_steps"].append({
                        "step": e.get("step", "?"),
                        "type": "zero_number",
                        "number_value": number_val,
                    })

        # Dict format (raw_state / older trace format)
        elif isinstance(slots, dict):
            slot_new = slots.get("slot_new", {})
            if not slot_new.get("occupied"):
                results["failed_draws"] += 1
                continue

            if slot_new.get("merge_count", 0) > 0:
                continue

            nv = slot_new.get("number_value", 0)
            cr = slot_new.get("color_r", 0)
            cg = slot_new.get("color_g", 0)
            cb = slot_new.get("color_b", 0)
            si = slot_new.get("shape_index", 0)

            if "color" in modes and cr == 0 and cg == 0 and cb == 0:
                results["black_color_draws"] += 1
                results["anomaly_steps"].append({
                    "step": e.get("step", "?"),
                    "type": "black_color",
                })
            if "shape" in modes and si == 8:
                results["sentinel_shape_draws"] += 1
                results["anomaly_steps"].append({
                    "step": e.get("step", "?"),
                    "type": "sentinel_shape",
                })
            if modes.get("number") == "add" and nv == 0:
                results["zero_number_draws"] += 1
                results["anomaly_steps"].append({
                    "step": e.get("step", "?"),
                    "type": "zero_number",
                })

    return results


def main():
    log_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("logs")
    if not log_dir.exists():
        print(f"Log directory not found: {log_dir}")
        sys.exit(2)

    episode_dirs = sorted(log_dir.glob("episode_*"))
    if not episode_dirs:
        print(f"No episode directories in {log_dir}")
        sys.exit(2)

    total_anomalies = 0
    summary_by_mode = defaultdict(lambda: {
        "episodes": 0, "draws": 0,
        "black_color": 0, "sentinel_shape": 0, "zero_number": 0,
        "failed_draws": 0,
    })

    for ep_dir in episode_dirs:
        events_file = ep_dir / "events.jsonl"
        if not events_file.exists():
            continue

        result = analyze_episode(events_file)

        # Determine mode key for grouping
        with open(events_file) as f:
            first = json.loads(f.readline())
        modes = first.get("config", {}).get("modes", {}) if first.get("type") == "episode_start" else {}
        mode_key = "+".join(f"{k}:{v}" for k, v in sorted(modes.items())) or "unknown"

        s = summary_by_mode[mode_key]
        s["episodes"] += 1
        s["draws"] += result["total_draws"]
        s["black_color"] += result["black_color_draws"]
        s["sentinel_shape"] += result["sentinel_shape_draws"]
        s["zero_number"] += result["zero_number_draws"]
        s["failed_draws"] += result["failed_draws"]

        ep_anomalies = (result["black_color_draws"] +
                        result["sentinel_shape_draws"] +
                        result["zero_number_draws"] +
                        result["failed_draws"])
        total_anomalies += ep_anomalies

        if ep_anomalies > 0:
            ep_name = ep_dir.name
            print(f"  FAIL {ep_name}: {result['total_draws']} draws, "
                  f"black_color={result['black_color_draws']}, "
                  f"sentinel_shape={result['sentinel_shape_draws']}, "
                  f"zero_number={result['zero_number_draws']}, "
                  f"failed_draws={result['failed_draws']}")

    print(f"\n{'='*70}")
    print(f"CARD INITIALIZATION VALIDATION REPORT")
    print(f"{'='*70}")
    print(f"Episodes analyzed: {sum(s['episodes'] for s in summary_by_mode.values())}")
    print(f"Total anomalies:   {total_anomalies}")
    print()

    for mode_key, s in sorted(summary_by_mode.items()):
        mode_anomalies = s["black_color"] + s["sentinel_shape"] + s["zero_number"] + s["failed_draws"]
        status = "PASS" if mode_anomalies == 0 else "FAIL"
        print(f"[{status}] {mode_key}")
        print(f"      {s['episodes']} episodes, {s['draws']} draws")
        if s["failed_draws"]:
            print(f"      failed_draws: {s['failed_draws']}")
        if s["black_color"]:
            print(f"      black_color:  {s['black_color']} / {s['draws']} ({100*s['black_color']/max(s['draws'],1):.1f}%)")
        if s["sentinel_shape"]:
            print(f"      sentinel_shape: {s['sentinel_shape']} / {s['draws']} ({100*s['sentinel_shape']/max(s['draws'],1):.1f}%)")
        if s["zero_number"]:
            print(f"      zero_number:  {s['zero_number']} / {s['draws']} ({100*s['zero_number']/max(s['draws'],1):.1f}%)")
        print()

    if total_anomalies > 0:
        print(f"RESULT: FAIL — {total_anomalies} card init anomalies detected")
        sys.exit(1)
    else:
        print("RESULT: PASS — all cards initialized correctly")
        sys.exit(0)


if __name__ == "__main__":
    main()
