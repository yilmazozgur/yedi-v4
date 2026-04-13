"""LiteLLM-backed provider.

Routes all chat completions through litellm.completion(), which dispatches to
Anthropic, OpenAI, Google, Cohere, Ollama, OpenRouter, vLLM, etc. transparently.

Model naming follows LiteLLM conventions:
  - "claude-sonnet-4-5"           -> Anthropic
  - "anthropic/claude-..."        -> Anthropic explicit
  - "gpt-4o"                      -> OpenAI
  - "openai/gpt-4o"               -> OpenAI explicit
  - "gemini/gemini-2.5-pro"       -> Google
  - "openai/<model>" + base_url   -> any OpenAI-compatible custom endpoint
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from .base import LLMProvider, ProviderCancelled, ProviderError

logger = logging.getLogger("provider.litellm")

# Rate-limit retry policy. The Anthropic free tier we hit during benchmark runs
# (30k input tokens/min) recovers in ≤60s, so a single 30s sleep is usually
# enough; we keep three attempts as a safety net for repeat hits within one
# benchmark batch. Total worst-case wait: 30 + 60 + 120 = 210s.
RATE_LIMIT_BACKOFFS_SECONDS = (30.0, 60.0, 120.0)

# How many times to retry when the API returns an empty response body (choices
# present but content is None/""). This typically means the inference backend
# (e.g. Together) hit a server-side timeout before the model produced its
# first token — a transient failure that almost always resolves on retry.
EMPTY_CONTENT_MAX_RETRIES = 2

# How often to wake from a backoff sleep to check should_cancel(). Smaller =
# more responsive cancel, more no-op wakeups. 1 second is plenty.
_CANCEL_POLL_INTERVAL = 1.0


def _interruptible_sleep(
    seconds: float,
    should_cancel: Optional[Callable[[], bool]],
) -> None:
    """Sleep for ``seconds``, breaking early if should_cancel() returns True.

    Raises:
        ProviderCancelled: if the cancel callback returns True at any point.
    """
    if should_cancel is None:
        time.sleep(seconds)
        return
    elapsed = 0.0
    while elapsed < seconds:
        if should_cancel():
            raise ProviderCancelled("cancelled during rate-limit backoff")
        chunk = min(_CANCEL_POLL_INTERVAL, seconds - elapsed)
        time.sleep(chunk)
        elapsed += chunk
    # Final check so a cancel that arrived in the last chunk is honoured.
    if should_cancel():
        raise ProviderCancelled("cancelled during rate-limit backoff")


class LiteLLMProvider(LLMProvider):
    """Universal provider using LiteLLM under the hood."""

    def complete(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
        timeout: Optional[float] = None,
    ) -> str:
        # LiteLLM expects messages in OpenAI format. The system prompt is
        # prepended as a {"role": "system"} message.
        api_messages: list[dict] = []
        if system:
            api_messages.append({"role": "system", "content": system})
        api_messages.extend(messages)

        # Build kwargs for litellm.completion
        kwargs: dict = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": self.max_tokens,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["base_url"] = self.base_url
        if timeout is not None:
            # LiteLLM forwards `timeout` to the underlying HTTP client. Without
            # it, a dead local server (e.g. Ollama crashed mid-run) hangs for
            # ~10 minutes — not acceptable for a pre-run smoke test.
            kwargs["timeout"] = timeout
        if self.num_ctx is not None and self.model.startswith(
            ("ollama_chat/", "ollama/")
        ):
            # For Ollama backends only, bump the KV-cache/context window. The
            # Ollama default of 4096 silently truncates our 18 KB system
            # prompt and crashes the model runner on vision requests. LiteLLM
            # passes this through to Ollama's /api/chat options block.
            kwargs["num_ctx"] = self.num_ctx

        # Imported lazily so unit tests that mock at the call site work.
        from litellm import completion
        from litellm.exceptions import RateLimitError

        # Try once, then once per backoff interval. A run of N+1 attempts where
        # the first N attempts each consume one backoff slot if they fail with
        # a rate-limit error.
        max_attempts = len(RATE_LIMIT_BACKOFFS_SECONDS) + 1
        for attempt in range(max_attempts):
            try:
                response = completion(**kwargs)
                break
            except RateLimitError as e:
                if attempt == max_attempts - 1:
                    logger.error(
                        "LiteLLM rate-limited for model=%s after %d retries: %s",
                        self.model, len(RATE_LIMIT_BACKOFFS_SECONDS), e,
                    )
                    raise ProviderError(
                        f"LLM call failed (rate limited after "
                        f"{len(RATE_LIMIT_BACKOFFS_SECONDS)} retries): {e}"
                    ) from e
                backoff = RATE_LIMIT_BACKOFFS_SECONDS[attempt]
                logger.warning(
                    "LiteLLM rate-limited for model=%s (attempt %d/%d), "
                    "sleeping %.0fs before retry: %s",
                    self.model, attempt + 1, max_attempts, backoff, e,
                )
                # Cancellable sleep — a Cancel click in the dashboard breaks
                # us out of this within ~1s instead of waiting up to 120s.
                _interruptible_sleep(backoff, should_cancel)
            except ProviderCancelled:
                # Don't wrap — let the runner see the cancel intent.
                raise
            except Exception as e:
                logger.error("LiteLLM call failed for model=%s: %s", self.model, e)
                raise ProviderError(f"LLM call failed: {e}") from e

        # Extract text from the OpenAI-format response, retrying on empty
        # content. Some inference backends (notably Together) occasionally
        # return a well-formed response with null/empty content when the
        # model times out server-side (~35s). A simple retry almost always
        # succeeds because the timeout is transient.
        for empty_retry in range(EMPTY_CONTENT_MAX_RETRIES + 1):
            try:
                choices = response.choices  # type: ignore[attr-defined]
                if not choices:
                    raise ProviderError("Empty choices in LLM response")
                content = choices[0].message.content
                if content:
                    return str(content)
                # Content is empty — retry if we have attempts left.
                if empty_retry < EMPTY_CONTENT_MAX_RETRIES:
                    logger.warning(
                        "Empty content from model=%s (attempt %d/%d), retrying…",
                        self.model, empty_retry + 1,
                        EMPTY_CONTENT_MAX_RETRIES + 1,
                    )
                    response = completion(**kwargs)
                    continue
                raise ProviderError("Empty content in LLM response")
            except AttributeError as e:
                raise ProviderError(f"Malformed LLM response: {e}") from e
