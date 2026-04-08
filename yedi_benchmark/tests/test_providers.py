"""Tests for the provider abstraction.

LiteLLM is mocked at the call boundary so the tests don't hit any real API.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from yedi_benchmark.providers.base import LLMProvider, ProviderError
from yedi_benchmark.providers.litellm_provider import LiteLLMProvider
from yedi_benchmark.providers.registry import (
    SUPPORTED_PROVIDERS,
    DEFAULT_API_KEY_ENVS,
    DEFAULT_MODELS,
    create_provider,
    resolve_api_key,
)


def _fake_response(text: str):
    """Build a MagicMock that mimics the OpenAI/LiteLLM response shape."""
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Provider registry
# ──────────────────────────────────────────────────────────────────────────────


class TestProviderRegistry:
    def test_supported_providers_listed(self):
        for p in ["anthropic", "openai", "google", "custom", "random"]:
            assert p in SUPPORTED_PROVIDERS

    def test_default_models_present(self):
        assert DEFAULT_MODELS["anthropic"]
        assert DEFAULT_MODELS["openai"]
        assert DEFAULT_MODELS["google"]

    def test_default_envs(self):
        assert DEFAULT_API_KEY_ENVS["anthropic"] == "ANTHROPIC_API_KEY"
        assert DEFAULT_API_KEY_ENVS["openai"] == "OPENAI_API_KEY"
        assert DEFAULT_API_KEY_ENVS["google"] == "GEMINI_API_KEY"

    def test_resolve_api_key_returns_value(self, monkeypatch):
        monkeypatch.setenv("MY_TEST_KEY", "secret-123")
        assert resolve_api_key("MY_TEST_KEY") == "secret-123"

    def test_resolve_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("NEVER_SET", raising=False)
        assert resolve_api_key("NEVER_SET") is None

    def test_resolve_none_env(self):
        assert resolve_api_key(None) is None

    def test_create_provider_random_rejected(self):
        with pytest.raises(ProviderError, match="random is not"):
            create_provider("random", "")

    def test_create_provider_unknown(self):
        with pytest.raises(ProviderError, match="Unknown provider"):
            create_provider("totally-fake", "x")

    def test_create_provider_missing_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ProviderError, match="requires an API key"):
            create_provider("anthropic", "claude-sonnet-4-5", api_key_env="ANTHROPIC_API_KEY")

    def test_create_provider_success(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        p = create_provider(
            "anthropic", "claude-sonnet-4-5",
            api_key_env="ANTHROPIC_API_KEY", max_tokens=128, supports_vision=True,
        )
        assert isinstance(p, LiteLLMProvider)
        assert p.model == "claude-sonnet-4-5"
        assert p.api_key == "fake-key"
        assert p.max_tokens == 128
        assert p.supports_vision is True

    def test_custom_provider_no_key_ok(self, monkeypatch):
        monkeypatch.delenv("CUSTOM_KEY", raising=False)
        p = create_provider("custom", "openai/local-model", base_url="http://localhost:8080")
        assert p.base_url == "http://localhost:8080"


# ──────────────────────────────────────────────────────────────────────────────
# LiteLLMProvider — completion path mocked
# ──────────────────────────────────────────────────────────────────────────────


class TestLiteLLMProvider:
    def test_complete_returns_text(self):
        p = LiteLLMProvider(model="claude-sonnet-4-5", api_key="fake")
        with patch("litellm.completion", return_value=_fake_response("hello")) as mock:
            out = p.complete(messages=[{"role": "user", "content": "hi"}])

        assert out == "hello"
        mock.assert_called_once()
        kwargs = mock.call_args.kwargs
        assert kwargs["model"] == "claude-sonnet-4-5"
        assert kwargs["api_key"] == "fake"

    def test_complete_prepends_system(self):
        p = LiteLLMProvider(model="gpt-4o", api_key="fake")
        with patch("litellm.completion", return_value=_fake_response("ok")) as mock:
            p.complete(
                messages=[{"role": "user", "content": "x"}],
                system="You are helpful.",
            )
        sent_msgs = mock.call_args.kwargs["messages"]
        assert sent_msgs[0]["role"] == "system"
        assert sent_msgs[0]["content"] == "You are helpful."
        assert sent_msgs[1]["role"] == "user"

    def test_complete_passes_base_url(self):
        p = LiteLLMProvider(
            model="openai/local", api_key="x", base_url="http://localhost:8080",
        )
        with patch("litellm.completion", return_value=_fake_response("ok")) as mock:
            p.complete(messages=[{"role": "user", "content": "x"}])
        assert mock.call_args.kwargs["base_url"] == "http://localhost:8080"

    def test_complete_max_tokens_passed(self):
        p = LiteLLMProvider(model="x", api_key="k", max_tokens=42)
        with patch("litellm.completion", return_value=_fake_response("ok")) as mock:
            p.complete(messages=[{"role": "user", "content": "x"}])
        assert mock.call_args.kwargs["max_tokens"] == 42

    def test_complete_no_system_omits_message(self):
        p = LiteLLMProvider(model="x", api_key="k")
        with patch("litellm.completion", return_value=_fake_response("ok")) as mock:
            p.complete(messages=[{"role": "user", "content": "x"}])
        sent = mock.call_args.kwargs["messages"]
        assert all(m["role"] != "system" for m in sent)

    def test_complete_wraps_litellm_error(self):
        p = LiteLLMProvider(model="x", api_key="k")
        with patch("litellm.completion", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderError, match="LLM call failed"):
                p.complete(messages=[{"role": "user", "content": "x"}])

    def test_complete_empty_choices_errors(self):
        p = LiteLLMProvider(model="x", api_key="k")
        bad = MagicMock()
        bad.choices = []
        with patch("litellm.completion", return_value=bad):
            with pytest.raises(ProviderError, match="Empty choices"):
                p.complete(messages=[{"role": "user", "content": "x"}])

    def test_complete_empty_content_errors(self):
        p = LiteLLMProvider(model="x", api_key="k")
        with patch("litellm.completion", return_value=_fake_response("")):
            with pytest.raises(ProviderError, match="Empty content"):
                p.complete(messages=[{"role": "user", "content": "x"}])

    def test_test_connection_success(self):
        p = LiteLLMProvider(model="x", api_key="k")
        with patch("litellm.completion", return_value=_fake_response("ok")):
            ok, msg = p.test_connection()
        assert ok is True
        assert "ok" in msg.lower()

    def test_test_connection_failure(self):
        p = LiteLLMProvider(model="x", api_key="k")
        with patch("litellm.completion", side_effect=RuntimeError("nope")):
            ok, msg = p.test_connection()
        assert ok is False
        assert "nope" in msg


# ──────────────────────────────────────────────────────────────────────────────
# LiteLLMProvider — rate-limit retry path
#
# We hit a hard production failure where a benchmark run died because Anthropic
# returned 429 ("30,000 input tokens per minute exceeded") and our provider
# wrapped it as a generic ProviderError immediately. The agent loop then took
# the fallback path and the trace's MODEL OUTPUT field was a cryptic
# "LLM call failed: litellm.RateLimitError" line. These tests pin the retry
# behavior so the provider sleeps & retries instead of failing the run on the
# first 429.
# ──────────────────────────────────────────────────────────────────────────────


def _rate_limit_error(msg: str = "rate limited"):
    """Build a real litellm.RateLimitError instance for use as side_effect.

    The constructor signature requires (message, llm_provider, model), so we
    can't just `raise RateLimitError("foo")`.
    """
    from litellm.exceptions import RateLimitError
    return RateLimitError(msg, llm_provider="anthropic", model="claude-sonnet-4-5")


class TestLiteLLMProviderRateLimitRetry:
    def test_retries_then_succeeds(self):
        """One 429, then a 200 — should sleep once and return the second result."""
        p = LiteLLMProvider(model="claude-sonnet-4-5", api_key="k")
        side_effects = [_rate_limit_error("first hit"), _fake_response("hello")]

        with patch("litellm.completion", side_effect=side_effects) as mock_complete, \
             patch("yedi_benchmark.providers.litellm_provider.time.sleep") as mock_sleep:
            out = p.complete(messages=[{"role": "user", "content": "hi"}])

        assert out == "hello"
        assert mock_complete.call_count == 2
        # First retry uses the first backoff slot
        mock_sleep.assert_called_once_with(30.0)

    def test_exhausts_retries_then_raises(self):
        """Every attempt 429s — should sleep N times, then raise ProviderError."""
        p = LiteLLMProvider(model="claude-sonnet-4-5", api_key="k")

        with patch(
            "litellm.completion",
            side_effect=[_rate_limit_error("hit") for _ in range(10)],
        ) as mock_complete, \
             patch("yedi_benchmark.providers.litellm_provider.time.sleep") as mock_sleep:
            with pytest.raises(ProviderError, match="rate limited after 3 retries"):
                p.complete(messages=[{"role": "user", "content": "hi"}])

        # 4 attempts: initial + 3 retries
        assert mock_complete.call_count == 4
        # 3 sleeps in between, in the configured backoff order
        assert [c.args[0] for c in mock_sleep.call_args_list] == [30.0, 60.0, 120.0]

    def test_non_rate_limit_error_does_not_retry(self):
        """A regular RuntimeError must fail fast without sleeping."""
        p = LiteLLMProvider(model="x", api_key="k")
        with patch(
            "litellm.completion", side_effect=RuntimeError("transport boom"),
        ) as mock_complete, \
             patch("yedi_benchmark.providers.litellm_provider.time.sleep") as mock_sleep:
            with pytest.raises(ProviderError, match="LLM call failed"):
                p.complete(messages=[{"role": "user", "content": "x"}])

        assert mock_complete.call_count == 1
        mock_sleep.assert_not_called()

    def test_success_first_try_no_sleep(self):
        """Sanity: the happy path doesn't go anywhere near time.sleep."""
        p = LiteLLMProvider(model="x", api_key="k")
        with patch(
            "litellm.completion", return_value=_fake_response("ok"),
        ), patch("yedi_benchmark.providers.litellm_provider.time.sleep") as mock_sleep:
            out = p.complete(messages=[{"role": "user", "content": "x"}])
        assert out == "ok"
        mock_sleep.assert_not_called()

    def test_recovery_after_two_rate_limits(self):
        """Two 429s in a row, then success. Sleeps should be 30s and 60s."""
        p = LiteLLMProvider(model="x", api_key="k")
        side_effects = [
            _rate_limit_error("first"),
            _rate_limit_error("second"),
            _fake_response("recovered"),
        ]
        with patch("litellm.completion", side_effect=side_effects), \
             patch("yedi_benchmark.providers.litellm_provider.time.sleep") as mock_sleep:
            out = p.complete(messages=[{"role": "user", "content": "x"}])

        assert out == "recovered"
        # With should_cancel=None we hit the fast path that does a single
        # time.sleep(backoff), so two retries == two sleeps in [30, 60].
        assert [c.args[0] for c in mock_sleep.call_args_list] == [30.0, 60.0]

    def test_cancel_during_backoff_aborts_immediately(self):
        """The whole point of this fix: a Cancel click in the dashboard must
        not have to wait out a 120-second rate-limit backoff. The provider
        polls should_cancel ~once per second during the sleep and raises
        ProviderCancelled instead of going back around for another retry."""
        from yedi_benchmark.providers.base import ProviderCancelled

        p = LiteLLMProvider(model="x", api_key="k")
        cancel_state = {"set": False}

        def fake_sleep(_seconds):
            # Simulate the user clicking Cancel during the sleep
            cancel_state["set"] = True

        with patch("litellm.completion", side_effect=_rate_limit_error("hit")), \
             patch(
                 "yedi_benchmark.providers.litellm_provider.time.sleep",
                 side_effect=fake_sleep,
             ) as mock_sleep:
            with pytest.raises(ProviderCancelled, match="cancelled"):
                p.complete(
                    messages=[{"role": "user", "content": "x"}],
                    should_cancel=lambda: cancel_state["set"],
                )

        # We slept at most one chunk before noticing the cancel.
        assert mock_sleep.call_count >= 1

    def test_cancel_check_skipped_when_no_callback(self):
        """should_cancel=None must keep the legacy behaviour: a single
        time.sleep(backoff) per retry, no chunking. This guards against
        accidentally regressing the no-callback path into a slow polling loop."""
        p = LiteLLMProvider(model="x", api_key="k")
        with patch(
            "litellm.completion",
            side_effect=[_rate_limit_error("hit"), _fake_response("ok")],
        ), patch(
            "yedi_benchmark.providers.litellm_provider.time.sleep",
        ) as mock_sleep:
            out = p.complete(messages=[{"role": "user", "content": "x"}])
        assert out == "ok"
        # Exactly one sleep call (the first backoff slot), one chunk worth.
        assert mock_sleep.call_count == 1
        assert mock_sleep.call_args.args[0] == 30.0


# ──────────────────────────────────────────────────────────────────────────────
# Base abstract enforcement
# ──────────────────────────────────────────────────────────────────────────────


class TestLLMProviderBase:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            LLMProvider(model="x")  # type: ignore[abstract]
