"""LLM provider abstraction wrapping LiteLLM for Yedi benchmark agents.

Providers normalize the call signature across Anthropic, OpenAI, Google, and
OpenAI-compatible custom endpoints. The benchmark code talks to a single
LLMProvider interface; LiteLLM dispatches to the underlying SDK.
"""

from .base import LLMProvider, ProviderError
from .litellm_provider import LiteLLMProvider
from .registry import (
    SUPPORTED_PROVIDERS,
    DEFAULT_MODELS,
    create_provider,
)

__all__ = [
    "LLMProvider",
    "ProviderError",
    "LiteLLMProvider",
    "SUPPORTED_PROVIDERS",
    "DEFAULT_MODELS",
    "create_provider",
]
