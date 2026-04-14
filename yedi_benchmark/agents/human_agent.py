"""Human recorder — passive agent that captures live human gameplay.

The runner detects ``is_human=True`` and dispatches to a dedicated branch
(``_run_episode_human`` in benchmark_runner) that bypasses the act/step
loop entirely. Instead, it puts the bridge into ``recordingMode`` and
drains ``human_step`` events from the bridge as the player drags cards
in the browser.

The class only exists so the registry / UI flow can treat human
recording uniformly — the dataset that comes out is byte-compatible with
AI agent runs (same events.jsonl schema), so it can train a
BehaviorCloningAgent later without any per-source special-casing.
"""

from .base_agent import BaseAgent


class HumanAgent(BaseAgent):
    """Passive recorder. Never picks an action — the human does."""

    is_human = True

    def __init__(self, name: str = "human"):
        super().__init__(name=name)

    def act(self, observation: dict, info: dict = None) -> int:
        raise NotImplementedError(
            "HumanAgent.act() must never be called — the runner branches on "
            "is_human and drains human_step events from the bridge instead."
        )
