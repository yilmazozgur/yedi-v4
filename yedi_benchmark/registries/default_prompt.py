"""Default prompt seed.

Reads the current CORE_RULES + DIMENSION_RULES out of agents.llm_agent (the
historical home of the prompt) and converts them into a Prompt model that the
PromptRegistry can persist as the v1 default.

Once the prompts registry is seeded, llm_agent.py will be refactored to read
from the registry instead — the constants in llm_agent.py become legacy.
"""

from __future__ import annotations

from .models import Prompt


def get_default_prompt() -> Prompt:
    """Build the default 'v1' prompt from llm_agent's hardcoded constants.

    The dimension_rules dict in llm_agent.py is keyed by tuples like
    ("number", "add"); we flatten to "number:add" string keys here so the
    Prompt model can serialize cleanly to JSON.
    """
    # Lazy import to avoid loading anthropic SDK at registry init time.
    from ..agents.llm_agent import CORE_RULES, DIMENSION_RULES

    flat_rules: dict[str, str] = {}
    for (dim_field, mode_value), rule_text in DIMENSION_RULES.items():
        flat_rules[f"{dim_field}:{mode_value}"] = rule_text

    return Prompt(
        name="Default v1",
        version=1,
        core_rules=CORE_RULES,
        dimension_rules=flat_rules,
        is_active=True,
    )
