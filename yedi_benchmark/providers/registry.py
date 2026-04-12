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
SUPPORTED_PROVIDERS = [
    "anthropic", "openai", "google", "together", "ollama", "custom",
    "random", "greedy",
]


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
    # Together.ai — OpenAI-compatible hosted inference. Models routed via
    # LiteLLM's `together_ai/` prefix (auto-prepended in create_provider).
    # Vision-capable first (needed for the vision-* agent modes), then strong
    # text-only models.
    "together": [
        "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
        "meta-llama/Llama-4-Scout-17B-16E-Instruct",
        "Qwen/Qwen2.5-VL-72B-Instruct",
        "meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo",
        "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "Qwen/Qwen2.5-72B-Instruct-Turbo",
        "deepseek-ai/DeepSeek-V3",
        "deepseek-ai/DeepSeek-R1",
    ],
    # Local Ollama server. Models listed here are the ones we've validated
    # against the bridge; users can type any `ollama pull` tag.
    #
    # Vision-capable (recommended for the agent UI):
    #   qwen3-vl:4b-instruct-q8_0   — Qwen3-VL 4B, ~4.5 GB, fits 16 GB VRAM
    #                                 with huge context headroom. Stable default
    #                                 for local development.
    #   qwen3-vl:4b-instruct         — default q4 variant, ~2.5 GB
    #   qwen3-vl:8b                  — Qwen3-VL 8B, ~5 GB, stronger reasoning
    #   qwen2.5vl:7b                 — older gen Qwen2.5-VL, ~14 GB (tight on 16 GB)
    #   qwen2.5vl:3b                 — older gen, smaller variant
    #   minicpm-v:8b                 — MiniCPM-V 2.6, strong OCR
    #   llama3.2-vision:11b          — Meta Llama 3.2 Vision, ~11 GB at Q4
    #   llava:13b                    — older but widely available
    #
    # Text-only (still useful for metadata-mode runs):
    #   qwen2.5:7b-instruct
    #   llama3.1:8b-instruct
    "ollama": [
        "qwen3-vl:4b-instruct-q8_0",
        "qwen3-vl:4b-instruct",
        "qwen3-vl:8b",
        "qwen2.5vl:7b",
        "qwen2.5vl:3b",
        "minicpm-v:8b",
        "llama3.2-vision:11b",
        "llava:13b",
        "qwen2.5:7b-instruct",
        "llama3.1:8b-instruct",
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
    "together": "TOGETHER_API_KEY",
    "ollama": "",  # local server, no auth
    "custom": "",
    "random": "",
    "greedy": "",
}


# Default base_url suggested for each provider. Only local / self-hosted
# providers have a sensible default here — the cloud providers rely on LiteLLM's
# own routing. Exposed in the ProviderInfo endpoint so the Add-Agent form can
# prefill the field.
DEFAULT_BASE_URLS: dict[str, str] = {
    "anthropic": "",
    "openai": "",
    "google": "",
    "together": "",  # LiteLLM routes via the together_ai/ prefix
    "ollama": "http://localhost:11434",
    "custom": "",
    "random": "",
    "greedy": "",
}


# LiteLLM prefix used to route Ollama models through the /api/chat endpoint.
# Using `ollama_chat/` (rather than the older `ollama/`) gives us multi-turn
# chat, system prompts, and multimodal content blocks — all of which we need
# for the benchmark.
_OLLAMA_MODEL_PREFIX = "ollama_chat/"

# LiteLLM prefix used to route Together.ai models through their OpenAI-compatible
# hosted inference API. The Together model menu in DEFAULT_MODELS stores the bare
# "org/model" slug; create_provider auto-prepends this prefix so users don't
# have to type it.
_TOGETHER_MODEL_PREFIX = "together_ai/"


# Default Ollama context window when the agent config doesn't specify one.
# Ollama's own default is 4096 tokens, which silently truncates our ~18 KB
# (4500-token) system prompt and causes "model runner unexpectedly stopped"
# crashes when a screenshot is also attached. 16384 gives comfortable room
# for system prompt + screenshot tokens + state dump on modest local models.
DEFAULT_OLLAMA_NUM_CTX = 16384


def resolve_api_key(api_key_env: Optional[str]) -> Optional[str]:
    """Resolve an environment variable name to its value, or None if missing."""
    if not api_key_env:
        return None
    return os.environ.get(api_key_env)


def smoke_test_agent(agent_cfg, timeout: float = 30.0) -> tuple[bool, str]:
    """Pre-run connectivity + credential check for an AgentConfig.

    Used by the /api/runs POST handler to fail fast if a run would just
    crash on the first LLM call (bad key, local server down, model not
    pulled, etc). Programmatic baselines (random, greedy) short-circuit
    to success — they have no provider to probe.

    Returns:
        (success, message). On failure, message is the upstream error
        string, formatted for direct display to the user in an HTTP error.
    """
    provider = getattr(agent_cfg, "provider", None)
    if provider in ("random", "greedy"):
        return True, f"{provider} baseline (no provider to test)"

    try:
        llm = create_provider(
            provider=agent_cfg.provider,
            model=agent_cfg.model,
            api_key_env=agent_cfg.api_key_env,
            base_url=agent_cfg.base_url,
            max_tokens=agent_cfg.max_tokens,
            supports_vision=agent_cfg.supports_vision,
            num_ctx=getattr(agent_cfg, "num_ctx", None),
        )
    except ProviderError as e:
        return False, str(e)

    return llm.test_connection(timeout=timeout)


def create_provider(
    provider: str,
    model: str,
    api_key_env: Optional[str] = None,
    base_url: Optional[str] = None,
    max_tokens: int = 512,
    supports_vision: bool = False,
    num_ctx: Optional[int] = None,
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

    # Anthropic, OpenAI, Google, Together all need a key. Custom and ollama may or may not.
    if provider in ("anthropic", "openai", "google", "together") and not api_key:
        raise ProviderError(
            f"Provider {provider!r} requires an API key. "
            f"Set env var {api_key_env or DEFAULT_API_KEY_ENVS[provider]!r}."
        )

    # Together.ai: hosted inference, LiteLLM routes via the together_ai/ prefix.
    # Let users type either "meta-llama/Llama-4-Scout-17B-16E-Instruct" or the
    # fully qualified "together_ai/meta-llama/..." — we only prepend when missing.
    if provider == "together":
        if not model:
            raise ProviderError(
                "Together.ai provider requires a model "
                "(e.g. 'meta-llama/Llama-4-Scout-17B-16E-Instruct')."
            )
        if not model.startswith(_TOGETHER_MODEL_PREFIX):
            model = _TOGETHER_MODEL_PREFIX + model

    # Ollama: local server with no auth. Apply sensible defaults and rewrite
    # the model string so LiteLLM routes through its ollama_chat backend.
    if provider == "ollama":
        if not base_url:
            base_url = DEFAULT_BASE_URLS["ollama"]
        if not model:
            raise ProviderError(
                "Ollama provider requires a model (e.g. 'qwen2.5vl:7b'). "
                "Pull it first with `ollama pull <model>`."
            )
        # Allow the user to type either "qwen2.5vl:7b" or the fully qualified
        # "ollama_chat/qwen2.5vl:7b"; only prepend the prefix if missing. Also
        # tolerate the older `ollama/` prefix (LiteLLM supports both).
        if not model.startswith(("ollama_chat/", "ollama/")):
            model = _OLLAMA_MODEL_PREFIX + model
        # LiteLLM refuses a None api_key for some backends; "" is safer.
        api_key = api_key or ""
        # Apply the default context window if the caller didn't override it.
        # See DEFAULT_OLLAMA_NUM_CTX above for the rationale.
        if num_ctx is None:
            num_ctx = DEFAULT_OLLAMA_NUM_CTX

    return LiteLLMProvider(
        model=model,
        api_key=api_key,
        base_url=base_url,
        max_tokens=max_tokens,
        supports_vision=supports_vision,
        num_ctx=num_ctx,
    )
