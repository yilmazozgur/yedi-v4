"""
Benchmark configurations for Yedi AI Benchmark.

Four difficulty tiers (Easy → BrainFry), designed to measure both
metadata-only and screenshot/VLM agent capabilities.

Motor and beat/rhythm dimensions are excluded — motor requires physical
noise modelling that bypasses the API agent paradigm, and beat timing
is not yet supported in step-based mode.

Usage:
    python -m yedi_benchmark.benchmark_runner --configs EASY --episodes 5
    python -m yedi_benchmark.benchmark_runner --configs HARD --episodes 3
    python -m yedi_benchmark.benchmark_runner --configs ALL --episodes 1
"""

# ── EASY ─────────────────────────────────────────────────────────────
# Single dimension, simplest sub-modes.
# Purpose: per-dimension calibration baseline.
EASY = {
    # Math — pure arithmetic, metadata agents should excel
    "easy_math_add":        {"number": "add"},
    "easy_math_multiply":   {"number": "multiply"},
    # Visual — color mixing, VLM has natural advantage
    "easy_visual_add":      {"color": "add"},
    "easy_visual_subtract": {"color": "subtract"},
    # Spatial — shape rotation matching
    "easy_spatial_triangle":  {"shape": "triangle"},
    "easy_spatial_rectangle": {"shape": "rectangle"},
    # Verbal — word categorization, tests language understanding
    "easy_verbal_verbs":    {"word": "verbs"},
    "easy_verbal_nouns":    {"word": "nouns"},
}

# ── MEDIUM ───────────────────────────────────────────────────────────
# Harder single-dimension modes + first 2D combinations.
# Purpose: test deeper per-dimension reasoning and multi-objective play.
MEDIUM = {
    # Harder single dimensions
    "med_math_gcd":         {"number": "gcd"},
    "med_visual_gray":      {"color": "gray"},
    "med_spatial_kanizsa":  {"shape": "kanizsa"},         # illusory contours — key VLM test
    "med_verbal_grammar":   {"word": "grammar"},
    # 2D combinations — must optimise across two merge objectives
    "med_math_visual":      {"number": "add", "color": "add"},
    "med_math_spatial":     {"number": "add", "shape": "triangle"},
    "med_visual_verbal":    {"color": "add", "word": "verbs"},
    "med_spatial_verbal":   {"shape": "triangle", "word": "verbs"},
    # First memory combos — "every action" is the gentler memory mode
    # (every interaction briefly re-reveals the whole board).
    "med_math_memory":      {"number": "add", "memory": "every action"},
    "med_visual_memory":    {"color": "add", "memory": "every action"},
}

# ── HARD ─────────────────────────────────────────────────────────────
# Advanced sub-modes + 2D hard-mode combos + 3D combinations.
# Purpose: genuinely challenging reasoning and multi-tasking.
HARD = {
    # Hardest single-dimension sub-modes
    "hard_math_trigon":     {"number": "trigon"},
    "hard_visual_text":     {"color": "text"},            # Stroop effect — key VLM test
    "hard_spatial_hanoi":   {"shape": "hanoi"},
    "hard_verbal_scrabble": {"word": "scrabble"},         # creative word formation
    # 2D with hard sub-modes
    "hard_gcd_gray":        {"number": "gcd", "color": "gray"},
    "hard_multiply_memory": {"number": "multiply", "memory": "every action"},
    "hard_synverbs_memory": {"word": "synVerbs", "memory": "show one"},
    # 3D combinations
    "hard_math_visual_spatial":     {"number": "add", "color": "add", "shape": "triangle"},
    "hard_visual_kanizsa_verbal":   {"color": "add", "shape": "kanizsa", "word": "verbs"},
    "hard_math_verbal_memory":      {"number": "add", "word": "verbs", "memory": "every action"},
}

# ── BRAINFRY ─────────────────────────────────────────────────────────
# 3–5 dimension combos with hardest sub-modes.
# Purpose: stress test — even the best models should struggle.
BRAINFRY = {
    # Classic 4D — the Yedi signature challenge
    "brainfry_4d_classic":  {"number": "add", "color": "add", "shape": "triangle", "word": "verbs"},
    # 4D harder sub-modes
    "brainfry_4d_hard":     {"number": "multiply", "color": "subtract", "shape": "rectangle", "word": "adjectives"},
    # 3D + hard memory
    "brainfry_3d_memory":   {"number": "add", "color": "add", "shape": "triangle", "memory": "every action"},
    # 3D all-hard reasoning modes
    "brainfry_3d_reasoning": {"number": "gcd", "color": "text", "word": "grammar"},
    # 3D extreme sub-modes
    "brainfry_3d_extreme":  {"number": "trigon", "color": "gray", "shape": "hanoi"},
    # 5D — full cognitive load
    "brainfry_5d":          {"number": "add", "color": "add", "shape": "triangle", "word": "verbs", "memory": "every action"},
    # 4D + hardest memory
    "brainfry_4d_memory":   {"number": "multiply", "color": "subtract", "word": "synVerbs", "memory": "show one"},
    # 5D all-hard — the ultimate challenge
    "brainfry_5d_hard":     {"number": "gcd", "color": "gray", "shape": "kanizsa", "word": "grammar", "memory": "every action"},
}

# ── Tier lookup ──────────────────────────────────────────────────────
TIERS = {
    "EASY": EASY,
    "MEDIUM": MEDIUM,
    "HARD": HARD,
    "BRAINFRY": BRAINFRY,
}

# Flat dict of every benchmark config
ALL_BENCHMARKS = {}
for tier in TIERS.values():
    ALL_BENCHMARKS.update(tier)


def tier_for_config(name: str) -> str:
    """Return the tier name for a given config, or 'unknown'."""
    for tier_name, configs in TIERS.items():
        if name in configs:
            return tier_name
    return "unknown"


def build_config_key(modes: dict) -> str:
    """Build the config key matching ScoreManager.BuildConfigKey().

    The key is a sorted, '+'-joined string of 'dimension:mode' pairs.
    """
    dim_map = {
        "number": "math",
        "color": "visual",
        "shape": "spatial",
        "word": "verbal",
        "beat": "music",
        "memory": "memory",
        "motor": "motor",
    }
    parts = []
    for field, mode in modes.items():
        if mode:
            dim_name = dim_map.get(field, field)
            parts.append(f"{dim_name}:{mode}")
    parts.sort()
    return "+".join(parts)
