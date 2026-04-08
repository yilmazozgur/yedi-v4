"""Base LLM provider interface.

A provider wraps the act of sending a prompt (with optional images) to an LLM
and getting back a text response. The Yedi LLMAgent uses providers without
caring which underlying API (Anthropic, OpenAI, Google, etc.) is in use.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional


class ProviderError(Exception):
    """Raised when an LLM provider call fails."""


class ProviderCancelled(ProviderError):
    """Raised when an in-progress provider call is interrupted by the caller.

    Distinct from ProviderError so the agent can re-raise this all the way to
    the run executor instead of swallowing it as a transient API error and
    falling back to a default action.
    """


class LLMProvider(ABC):
    """Abstract LLM provider.

    Implementations:
      - LiteLLMProvider: dispatches to Anthropic/OpenAI/Google/custom via LiteLLM
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: int = 512,
        supports_vision: bool = False,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.supports_vision = supports_vision

    @abstractmethod
    def complete(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> str:
        """Send a chat completion request and return the assistant's text reply.

        Args:
            messages: list of {"role": "user"|"assistant", "content": str | list}
                For vision: content can be a list of blocks with {"type": "text", ...}
                or {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}.
                The provider implementation translates to its native API format.
            system: optional system prompt string.
            should_cancel: optional callable returning True when the caller
                wants to abort. The provider checks it during long internal
                waits (e.g. rate-limit backoff sleeps) and raises
                ProviderCancelled instead of finishing the wait. The actual
                in-flight HTTP request is not interruptible.

        Returns:
            The assistant's text content.

        Raises:
            ProviderError: on API failure or empty response.
            ProviderCancelled: if ``should_cancel()`` returned True during a
                cancellable wait.
        """
        ...

    def test_connection(self) -> tuple[bool, str]:
        """Send a tiny ping request to verify credentials and connectivity.

        Returns:
            (success, message). On failure, message contains the error string.
        """
        try:
            reply = self.complete(
                messages=[{"role": "user", "content": "Reply with the single word 'ok'."}],
                system=None,
            )
            return True, f"OK ({reply.strip()[:40]})"
        except Exception as e:
            return False, str(e)
