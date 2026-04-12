"""Random agent — baseline that picks uniformly from valid actions."""

import numpy as np
from .base_agent import BaseAgent


class RandomAgent(BaseAgent):
    """Baseline agent that selects random valid actions."""

    def __init__(self, seed: int = None):
        super().__init__(name="random")
        self.rng = np.random.default_rng(seed)

    def act(self, observation: dict, info: dict = None) -> int:
        mask = observation.get("action_mask", None)
        if mask is not None:
            valid = np.where(np.array(mask) > 0)[0]
            if len(valid) > 0:
                return int(self.rng.choice(valid))
        # Fallback: DRAW
        return 0
