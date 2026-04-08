"""/api/configs — read-only listing of available game configs and tiers.

The Benchmark page uses this to populate the "select games" picker.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..benchmark_configs import ALL_BENCHMARKS, TIERS

router = APIRouter(prefix="/api/configs", tags=["configs"])


@router.get("")
def list_configs() -> dict:
    """Return all configs grouped by tier and a flat all-configs map.

    Shape:
        {
          "tiers": { "EASY": ["easy_math_add", ...], ... },
          "configs": { "easy_math_add": {"number": "add"}, ... }
        }
    """
    return {
        "tiers": {tier_name: list(tier.keys()) for tier_name, tier in TIERS.items()},
        "configs": {name: dict(modes) for name, modes in ALL_BENCHMARKS.items()},
    }
