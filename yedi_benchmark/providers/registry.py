"""Provider registry: known providers, their default models, and the factory.

This module is the bridge between AgentConfig records (in the registry) and
runtime LLMProvider instances. The web UI uses SUPPORTED_PROVIDERS and
DEFAULT_MODELS to populate dropdowns.
"""

from __future__ import annotations

import os
from typing import Optional

from .base import LLMProvider, ProviderError
from .litellm_provider import LiteLLMProvider


# Provider keys used in AgentConfig.provider.
# "random" and "greedy" are programmatic baselines, not LLM providers — they
# live in this list so the registry/UI can pick them, but create_provider()
# refuses to build an LLMProvider for them. The agent factory routes them to
# RandomAgent / GreedyAgent directly.
SUPPORTED_PROVIDERS = ["anthropic", "openai", "google", "custom", "random", "greedy"]


# Curated default model list per provider for the UI dropdown.
# Users can type any model string LiteLLM understands; this is just the menu.
DEFAULT_MODELS: dict[str, list[str]] = {
    "anthropic": [
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ],
    "openai": [
        "gpt-5",
        "gpt-4.1",
        "gpt-4o",
        "gpt-4o-mini",
        "o1",
        "o1-mini",
    ],
    "google": [
        "gemini/gemini-2.5-pro",
        "gemini/gemini-2.5-flash",
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.5-flash",
    ],
    "custom": [],
    "random": [],
    "greedy": [],
}


# Default env var name suggested for each provider on the Add Agent form.
DEFAULT_API_KEY_ENVS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GEMINI_API_KEY",
    "custom": "",
    "random": "",
    "greedy": "",
}


def resolve_api_key(api_key_env: Optional[str]) -> Optional[str]:
    """Resolve an environment variable name to its value, or None if missing."""
    if not api_key_env:
        return None
    return os.environ.get(api_key_env)


def create_provider(
    provider: str,
    model: str,
    api_key_env: Optional[str] = None,
    base_url: Optional[str] = None,
    max_tokens: int = 512,
    supports_vision: bool = False,
) -> LLMProvider:
    """Build an LLMProvider instance from a config tuple.

    Args:
        provider: one of SUPPORTED_PROVIDERS (excluding "random")
        model: model name (LiteLLM-compatible)
        api_key_env: env var name to look up the API key from
        base_url: optional override for OpenAI-compatible endpoints
        max_tokens: response token cap
        supports_vision: hint for the agent layer

    Raises:
        ProviderError: if provider is unknown or required key is missing.
    """
    if provider == "random":
        raise ProviderError("random is not an LLM provider — use RandomAgent directly")
    if provider == "greedy":
        raise ProviderError("greedy is not an LLM provider — use GreedyAgent directly")
    if provider not in SUPPORTED_PROVIDERS:
        raise ProviderError(f"Unknown provider: {provider}")

    api_key = resolve_api_key(api_key_env)

    # Anthropic, OpenAI, Google all need a key. Custom may or may not.
    if provider in ("anthropic", "openai", "google") and not api_key:
        raise ProviderError(
            f"Provider {provider!r} requires an API key. "
            f"Set env var {api_key_env or DEFAULT_API_KEY_ENVS[provider]!r}."
        )

    return LiteLLMProvider(
        model=model,
        api_key=api_key,
        base_url=base_url,
        max_tokens=max_tokens,
        supports_vision=supports_vision,
    )
