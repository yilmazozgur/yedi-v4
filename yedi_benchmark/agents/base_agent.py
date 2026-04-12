"""Base agent interface for Yedi benchmark."""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract base class for all Yedi agents."""

    def __init__(self, name: str = "base"):
        self.name = name

    @abstractmethod
    def act(self, observation: dict, info: dict = None) -> int:
        """Choose an action given the current observation.

        Args:
            observation: Gymnasium observation dict
            info: Additional info dict from env.step() or env.reset()

        Returns:
            Action index (0-36)
        """
        ...

    def reset(self):
        """Called at the start of each episode."""
        pass

    def on_step_result(self, action: int, reward: float, terminated: bool, info: dict):
        """Called after each step with the result. Useful for learning agents."""
        pass
