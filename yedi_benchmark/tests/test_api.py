"""HTTP API tests using FastAPI's TestClient.

Strategy:
  - One isolated FastAPI app per test (fresh tmp data dir + runs dir).
  - Registry singletons are dependency-overridden to point at the tmp dirs.
  - The run executor singleton is reset between tests.
  - Run start is exercised against a stubbed `run_benchmark_with_registry` so
    the tests don't need a real WebSocket bridge or LLM provider.

The tests cover the public surface only — internal helpers are tested in the
other test_* files.
"""

from __future__ import annotations

import os
import threading
import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yedi_benchmark import bridge_status as bridge_status_mod
from yedi_benchmark import run_trace as run_trace_mod
from yedi_benchmark.api import mount_api_routers
from yedi_benchmark.api import deps as api_deps
from yedi_benchmark.api import run_executor as run_executor_mod
from yedi_benchmark.registries import (
    AgentRegistry,
    PromptRegistry,
    RunRegistry,
    RunStatus,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Build a TestClient backed by isolated tmp registries + a fresh executor.

    The bridge is marked as game-connected by default so the run-start tests
    don't need to fake a WebSocket. The dedicated guard test below clears it.
    """
    data_dir = tmp_path / "data"
    runs_dir = tmp_path / "runs"
    data_dir.mkdir()
    runs_dir.mkdir()
    monkeypatch.setenv("YEDI_DATA_DIR", str(data_dir))
    monkeypatch.setenv("YEDI_RUNS_DIR", str(runs_dir))

    # Reset cached singletons so they pick up the new env vars
    api_deps.reset_registry_singletons()
    run_executor_mod.reset_run_executor()
    bridge_status_mod.reset_bridge_status()
    bridge_status_mod.get_bridge_status().mark_game_connected()
    run_trace_mod.reset_run_trace_store()

    app = FastAPI()
    mount_api_routers(app)

    with TestClient(app) as c:
        yield c


# ──────────────────────────────────────────────────────────────────────────────
# /api/agents
# ──────────────────────────────────────────────────────────────────────────────


class TestAgentsAPI:
    def test_list_returns_seeded_agents(self, client):
        r = client.get("/api/agents")
        assert r.status_code == 200
        names = [a["name"] for a in r.json()]
        assert "Random" in names
        assert "Claude Sonnet 4.5" in names

    def test_providers_endpoint(self, client):
        r = client.get("/api/agents/providers")
        assert r.status_code == 200
        body = r.json()
        assert "anthropic" in body["providers"]
        assert "openai" in body["providers"]
        assert "ollama" in body["providers"]  # local VLM path
        assert body["default_models"]["anthropic"]
        assert body["default_models"]["ollama"]  # curated VLM menu
        assert body["default_api_key_envs"]["anthropic"] == "ANTHROPIC_API_KEY"
        assert body["default_api_key_envs"]["ollama"] == ""  # no auth for local
        # The Add-Agent form uses default_base_urls to prefill the URL input
        # when the user picks a local provider.
        assert body["default_base_urls"]["ollama"] == "http://localhost:11434"
        assert body["default_base_urls"]["anthropic"] == ""  # cloud = empty

    def test_create_then_get(self, client):
        body = {
            "name": "My Test Agent",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key_env": "OPENAI_API_KEY",
            "max_tokens": 256,
            "supports_vision": True,
        }
        r = client.post("/api/agents", json=body)
        assert r.status_code == 201
        created = r.json()
        assert created["name"] == "My Test Agent"
        assert created["id"].startswith("agent_")

        r2 = client.get(f"/api/agents/{created['id']}")
        assert r2.status_code == 200
        assert r2.json()["model"] == "gpt-4o-mini"

    def test_create_duplicate_name_409(self, client):
        r = client.post("/api/agents", json={
            "name": "Random", "provider": "random", "model": "",
        })
        assert r.status_code == 409

    def test_create_invalid_provider_422(self, client):
        r = client.post("/api/agents", json={
            "name": "Bogus", "provider": "totally-fake", "model": "",
        })
        assert r.status_code == 422

    def test_update_changes_field(self, client):
        existing = client.get("/api/agents").json()
        target = next(a for a in existing if a["name"] == "Claude Sonnet 4.5")
        r = client.put(f"/api/agents/{target['id']}", json={"max_tokens": 1024})
        assert r.status_code == 200
        assert r.json()["max_tokens"] == 1024

    def test_update_missing_404(self, client):
        r = client.put("/api/agents/agent_does_not_exist", json={"max_tokens": 1})
        assert r.status_code == 404

    def test_delete(self, client):
        existing = client.get("/api/agents").json()
        target = next(a for a in existing if a["name"] == "GPT-4o")
        r = client.delete(f"/api/agents/{target['id']}")
        assert r.status_code == 204
        # Confirmed gone
        assert client.get(f"/api/agents/{target['id']}").status_code == 404

    def test_delete_missing_404(self, client):
        assert client.delete("/api/agents/nope").status_code == 404

    def test_test_random_always_succeeds(self, client):
        existing = client.get("/api/agents").json()
        rand = next(a for a in existing if a["provider"] == "random")
        r = client.post(f"/api/agents/{rand['id']}/test")
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_test_missing_key_returns_failure(self, client, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        existing = client.get("/api/agents").json()
        claude = next(a for a in existing if a["name"] == "Claude Sonnet 4.5")
        r = client.post(f"/api/agents/{claude['id']}/test")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is False
        assert "API key" in body["message"] or "key" in body["message"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# /api/prompts
# ──────────────────────────────────────────────────────────────────────────────


class TestPromptsAPI:
    def test_list_seeded(self, client):
        r = client.get("/api/prompts")
        assert r.status_code == 200
        prompts = r.json()
        assert len(prompts) == 1
        assert prompts[0]["name"] == "Default v1"
        assert prompts[0]["is_active"] is True

    def test_get_active(self, client):
        r = client.get("/api/prompts/active")
        assert r.status_code == 200
        assert r.json()["name"] == "Default v1"

    def test_create_inactive_by_default(self, client):
        r = client.post("/api/prompts", json={
            "name": "New Prompt",
            "core_rules": "Play smart.",
            "dimension_rules": {"number:add": "Add carefully."},
        })
        assert r.status_code == 201
        created = r.json()
        assert created["is_active"] is False
        # Default still active
        assert client.get("/api/prompts/active").json()["name"] == "Default v1"

    def test_activate_swap(self, client):
        r = client.post("/api/prompts", json={"name": "Other", "core_rules": "x"})
        new_id = r.json()["id"]
        r2 = client.post(f"/api/prompts/{new_id}/activate")
        assert r2.status_code == 200
        assert r2.json()["is_active"] is True
        assert client.get("/api/prompts/active").json()["id"] == new_id

    def test_cannot_delete_active(self, client):
        active = client.get("/api/prompts/active").json()
        r = client.delete(f"/api/prompts/{active['id']}")
        assert r.status_code == 409

    def test_clone_bumps_version(self, client):
        active = client.get("/api/prompts/active").json()
        r = client.post(f"/api/prompts/{active['id']}/clone", json={"new_name": "Default v2"})
        assert r.status_code == 201
        assert r.json()["version"] == active["version"] + 1
        assert r.json()["is_active"] is False

    def test_create_duplicate_name_409(self, client):
        r = client.post("/api/prompts", json={
            "name": "Default v1", "core_rules": "x",
        })
        assert r.status_code == 409

    def test_update_forbids_is_active(self, client):
        r = client.post("/api/prompts", json={"name": "Other", "core_rules": "x"})
        pid = r.json()["id"]
        r2 = client.put(f"/api/prompts/{pid}", json={"is_active": True, "core_rules": "y"})
        assert r2.status_code == 200
        assert r2.json()["is_active"] is False
        assert r2.json()["core_rules"] == "y"

    def test_get_missing_404(self, client):
        assert client.get("/api/prompts/prompt_does_not_exist").status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# /api/configs
# ──────────────────────────────────────────────────────────────────────────────


class TestConfigsAPI:
    def test_list(self, client):
        r = client.get("/api/configs")
        assert r.status_code == 200
        body = r.json()
        assert "tiers" in body
        assert "configs" in body
        assert "EASY" in body["tiers"]
        assert "easy_math_add" in body["configs"]
        assert body["configs"]["easy_math_add"] == {"number": "add"}


# ──────────────────────────────────────────────────────────────────────────────
# /api/runs — using a stubbed run_benchmark_with_registry so we don't need
# the WebSocket bridge or any LLM call.
# ──────────────────────────────────────────────────────────────────────────────


def _stub_runner(stop_event=None, episodes=1, max_steps=10):
    """Build a stub for run_benchmark_with_registry that creates a run record
    and (optionally) blocks until told to finish."""

    def stub(
        agent_id, prompt_id=None, mode="metadata-b", config_names=None,
        episodes_per_config=1, max_steps=10, server_url="x", log_dir="x",
        cancel_event=None, show_merge_previews=False, perfect_memory=False,
    ):
        from yedi_benchmark.registries import (
            AgentRegistry, PromptRegistry, RunRegistry, AgentMode, RunStatus,
            EpisodeResult,
        )

        ar = AgentRegistry()
        pr = PromptRegistry()
        rr = RunRegistry()
        agent = ar.get(agent_id)
        prompt = None
        if agent.provider != "random":
            prompt = pr.get(prompt_id) if prompt_id else pr.get_active()

        record = rr.create(
            agent=agent, prompt=prompt, configs=list(config_names),
            episodes_per_config=episodes_per_config, max_steps=max_steps,
            mode=AgentMode(mode),
            show_merge_previews=show_merge_previews,
            perfect_memory=perfect_memory,
        )
        rr.update_status(record.id, RunStatus.RUNNING)

        # Optionally block until the test releases us, checking cancel.
        if stop_event is not None:
            while not stop_event.is_set():
                if cancel_event is not None and cancel_event.is_set():
                    rr.update_status(record.id, RunStatus.CANCELLED)
                    return rr.get(record.id)
                time.sleep(0.01)

        # Append a fake episode and finish.
        for cfg_name in config_names:
            for i in range(episodes_per_config):
                rr.append_episode(record.id, cfg_name, EpisodeResult(
                    episode_idx=i, max_mana=200.0, total_reward=0.0,
                    steps=10, game_over=False,
                ))
        rr.update_status(record.id, RunStatus.COMPLETED)
        return rr.get(record.id)

    return stub


class TestRunsAPI:
    def test_list_empty_initially(self, client):
        r = client.get("/api/runs")
        assert r.status_code == 200
        assert r.json() == []

    def test_active_returns_inactive(self, client):
        r = client.get("/api/runs/active")
        assert r.status_code == 200
        body = r.json()
        assert body["active"] is False
        assert body["run_id"] is None

    def _random_agent_id(self, client):
        agents = client.get("/api/agents").json()
        return next(a for a in agents if a["provider"] == "random")["id"]

    def test_create_run_with_stub(self, client):
        agent_id = self._random_agent_id(client)

        with patch(
            "yedi_benchmark.api.run_executor.run_benchmark_with_registry",
            _stub_runner(stop_event=None, episodes=1),
        ):
            r = client.post("/api/runs", json={
                "agent_id": agent_id,
                "mode": "metadata-a",
                "configs": ["easy_math_add"],
                "episodes_per_config": 1,
                "max_steps": 10,
            })
            assert r.status_code == 201, r.text
            record = r.json()
            assert record["id"].startswith("run_")
            assert record["agent_snapshot"]["name"] == "Random"
            # Default canonical-benchmark behaviour: ablations are off.
            assert record["show_merge_previews"] is False
            assert record["perfect_memory"] is False

            # Wait for the worker to finish
            from yedi_benchmark.api.run_executor import get_run_executor
            assert get_run_executor().wait_for_completion(timeout=5.0)

        # Run is now visible in the registry as completed
        r2 = client.get(f"/api/runs/{record['id']}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "completed"
        assert len(r2.json()["results"]["easy_math_add"]["episodes"]) == 1

    def test_create_run_with_ablation_flags(self, client):
        # Both ablation flags must round-trip into the snapshotted RunRecord
        # so the dashboard can render badges and post-hoc analysis can group
        # by ablation. We pin both flags True here and verify they survive
        # the create-then-fetch cycle.
        agent_id = self._random_agent_id(client)

        with patch(
            "yedi_benchmark.api.run_executor.run_benchmark_with_registry",
            _stub_runner(stop_event=None, episodes=1),
        ):
            r = client.post("/api/runs", json={
                "agent_id": agent_id,
                "mode": "metadata-a",
                "configs": ["easy_math_add"],
                "episodes_per_config": 1,
                "max_steps": 10,
                "show_merge_previews": True,
                "perfect_memory": True,
            })
            assert r.status_code == 201, r.text
            record = r.json()
            assert record["show_merge_previews"] is True
            assert record["perfect_memory"] is True

            from yedi_benchmark.api.run_executor import get_run_executor
            assert get_run_executor().wait_for_completion(timeout=5.0)

        r2 = client.get(f"/api/runs/{record['id']}").json()
        assert r2["show_merge_previews"] is True
        assert r2["perfect_memory"] is True

    def test_single_run_lock(self, client):
        agent_id = self._random_agent_id(client)
        gate = threading.Event()  # blocks the stub until set

        with patch(
            "yedi_benchmark.api.run_executor.run_benchmark_with_registry",
            _stub_runner(stop_event=gate),
        ):
            r1 = client.post("/api/runs", json={
                "agent_id": agent_id, "mode": "metadata-a",
                "configs": ["easy_math_add"], "episodes_per_config": 1, "max_steps": 5,
            })
            assert r1.status_code == 201

            # Second concurrent start must be rejected with 409
            r2 = client.post("/api/runs", json={
                "agent_id": agent_id, "mode": "metadata-a",
                "configs": ["easy_math_add"], "episodes_per_config": 1, "max_steps": 5,
            })
            assert r2.status_code == 409
            assert "in progress" in r2.json()["detail"]

            # /api/runs/active reflects the busy state
            active = client.get("/api/runs/active").json()
            assert active["active"] is True
            assert active["run_id"] == r1.json()["id"]

            # Release the worker, wait for it
            gate.set()
            from yedi_benchmark.api.run_executor import get_run_executor
            assert get_run_executor().wait_for_completion(timeout=5.0)

        # Active now empty
        assert client.get("/api/runs/active").json()["active"] is False

    def test_cancel_in_flight(self, client):
        agent_id = self._random_agent_id(client)
        gate = threading.Event()  # never set, so the stub blocks until cancel

        with patch(
            "yedi_benchmark.api.run_executor.run_benchmark_with_registry",
            _stub_runner(stop_event=gate),
        ):
            r = client.post("/api/runs", json={
                "agent_id": agent_id, "mode": "metadata-a",
                "configs": ["easy_math_add"], "episodes_per_config": 1, "max_steps": 5,
            })
            run_id = r.json()["id"]

            # Cancel
            cr = client.post(f"/api/runs/{run_id}/cancel")
            assert cr.status_code == 200

            from yedi_benchmark.api.run_executor import get_run_executor
            assert get_run_executor().wait_for_completion(timeout=5.0)

        final = client.get(f"/api/runs/{run_id}").json()
        assert final["status"] == "cancelled"

    def test_cancel_unknown_404(self, client):
        r = client.post("/api/runs/run_nope/cancel")
        assert r.status_code == 404

    def test_delete_running_409(self, client):
        agent_id = self._random_agent_id(client)
        gate = threading.Event()

        with patch(
            "yedi_benchmark.api.run_executor.run_benchmark_with_registry",
            _stub_runner(stop_event=gate),
        ):
            r = client.post("/api/runs", json={
                "agent_id": agent_id, "mode": "metadata-a",
                "configs": ["easy_math_add"], "episodes_per_config": 1, "max_steps": 5,
            })
            run_id = r.json()["id"]

            d = client.delete(f"/api/runs/{run_id}")
            assert d.status_code == 409

            gate.set()
            from yedi_benchmark.api.run_executor import get_run_executor
            assert get_run_executor().wait_for_completion(timeout=5.0)

        # After completion delete works
        d2 = client.delete(f"/api/runs/{run_id}")
        assert d2.status_code == 204

    def test_list_filter_by_status(self, client):
        agent_id = self._random_agent_id(client)
        with patch(
            "yedi_benchmark.api.run_executor.run_benchmark_with_registry",
            _stub_runner(stop_event=None),
        ):
            client.post("/api/runs", json={
                "agent_id": agent_id, "mode": "metadata-a",
                "configs": ["easy_math_add"], "episodes_per_config": 1, "max_steps": 5,
            })
            from yedi_benchmark.api.run_executor import get_run_executor
            assert get_run_executor().wait_for_completion(timeout=5.0)

        r = client.get("/api/runs?status=completed")
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["status"] == "completed"

        r2 = client.get("/api/runs?status=failed")
        assert r2.json() == []

    def test_create_run_invalid_agent_400(self, client):
        r = client.post("/api/runs", json={
            "agent_id": "agent_does_not_exist",
            "mode": "metadata-a",
            "configs": ["easy_math_add"],
            "episodes_per_config": 1,
        })
        assert r.status_code == 400

    def test_create_run_rejects_vision_with_merge_previews(self, client):
        """Vision mode + show_merge_previews is incoherent: the preview
        block leaks memory-hidden card values and trivialises the visual
        perception test. The UI disables the checkbox on vision modes; the
        API independently rejects the combination so CLI/test callers can't
        bypass the UI guard."""
        agent_id = self._random_agent_id(client)
        r = client.post("/api/runs", json={
            "agent_id": agent_id,
            "mode": "vision-c",
            "configs": ["easy_math_add"],
            "episodes_per_config": 1,
            "max_steps": 5,
            "show_merge_previews": True,
        })
        assert r.status_code == 400
        assert "vision" in r.json()["detail"].lower()
        assert "merge_previews" in r.json()["detail"].lower()
        # And no run record was created.
        assert client.get("/api/runs").json() == []

    def test_create_run_no_game_connected_400(self, client):
        """Run start must refuse when /ws/game has no browser attached."""
        agent_id = self._random_agent_id(client)
        # Fixture marks the bridge as connected by default — clear it.
        bridge_status_mod.get_bridge_status().mark_game_disconnected()
        r = client.post("/api/runs", json={
            "agent_id": agent_id,
            "mode": "metadata-a",
            "configs": ["easy_math_add"],
            "episodes_per_config": 1,
        })
        assert r.status_code == 400
        assert "no browser game" in r.json()["detail"].lower()

    # ──────────────────────────────────────────────────────────────────────
    # Pre-run smoke test
    #
    # The /api/runs POST handler probes the agent's provider before spawning
    # a worker thread, so a misconfigured agent (dead local server, missing
    # API key, wrong model tag) fails at POST time with a clean 400 instead
    # of showing up as a FAILED run record with a cryptic error. These tests
    # pin that contract.
    # ──────────────────────────────────────────────────────────────────────

    def _llm_agent_id(self, client):
        """Return the id of the seeded Claude agent (first non-baseline)."""
        agents = client.get("/api/agents").json()
        return next(
            a for a in agents if a["provider"] not in ("random", "greedy")
        )["id"]

    def test_smoke_test_blocks_run_with_bad_key(self, client, monkeypatch):
        """An LLM agent with no key must produce a 400 before any run record
        gets created and before the stubbed runner is touched."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        agent_id = self._llm_agent_id(client)

        called = {"hit": False}

        def _stub(*args, **kwargs):
            called["hit"] = True
            raise AssertionError("runner should not be invoked when smoke test fails")

        with patch(
            "yedi_benchmark.api.run_executor.run_benchmark_with_registry", _stub,
        ):
            r = client.post("/api/runs", json={
                "agent_id": agent_id,
                "mode": "metadata-a",
                "configs": ["easy_math_add"],
                "episodes_per_config": 1,
                "max_steps": 5,
            })

        assert r.status_code == 400
        assert "smoke test failed" in r.json()["detail"].lower()
        assert called["hit"] is False

        # And no run record was created despite the failed POST.
        assert client.get("/api/runs").json() == []

    def test_smoke_test_passes_starts_run(self, client, monkeypatch):
        """With a working provider (mocked litellm), the smoke test passes and
        the run proceeds normally through the stubbed runner."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        agent_id = self._llm_agent_id(client)

        from unittest.mock import MagicMock
        fake = MagicMock()
        choice = MagicMock()
        choice.message.content = "ok"
        fake.choices = [choice]

        with patch("litellm.completion", return_value=fake), \
             patch(
                 "yedi_benchmark.api.run_executor.run_benchmark_with_registry",
                 _stub_runner(stop_event=None),
             ):
            r = client.post("/api/runs", json={
                "agent_id": agent_id,
                "mode": "metadata-a",
                "configs": ["easy_math_add"],
                "episodes_per_config": 1,
                "max_steps": 5,
            })
            assert r.status_code == 201, r.text

            from yedi_benchmark.api.run_executor import get_run_executor
            assert get_run_executor().wait_for_completion(timeout=5.0)

    def test_smoke_test_skipped_for_random_agent(self, client):
        """Random baselines must skip the smoke test entirely — even if
        litellm would blow up when called. This test kills litellm.completion
        to prove the code path never reaches it for random agents."""
        agent_id = self._random_agent_id(client)

        def _boom(*args, **kwargs):
            raise AssertionError("smoke test must not call litellm for random agents")

        with patch("litellm.completion", side_effect=_boom), \
             patch(
                 "yedi_benchmark.api.run_executor.run_benchmark_with_registry",
                 _stub_runner(stop_event=None),
             ):
            r = client.post("/api/runs", json={
                "agent_id": agent_id,
                "mode": "metadata-a",
                "configs": ["easy_math_add"],
                "episodes_per_config": 1,
                "max_steps": 5,
            })
            assert r.status_code == 201, r.text

            from yedi_benchmark.api.run_executor import get_run_executor
            assert get_run_executor().wait_for_completion(timeout=5.0)


# ──────────────────────────────────────────────────────────────────────────────
# /api/bridge
# ──────────────────────────────────────────────────────────────────────────────


class TestBridgeAPI:
    def test_status_reports_game_connected(self, client):
        # Fixture marks game-connected by default
        r = client.get("/api/bridge/status")
        assert r.status_code == 200
        body = r.json()
        assert body["game_connected"] is True
        assert body["agent_connected"] is False
        assert body["game_connected_at"] is not None

    def test_status_reports_disconnected(self, client):
        bridge_status_mod.get_bridge_status().mark_game_disconnected()
        r = client.get("/api/bridge/status")
        body = r.json()
        assert body["game_connected"] is False
        assert body["game_connected_at"] is None

    def test_status_reflects_agent_connection(self, client):
        bridge_status_mod.get_bridge_status().mark_agent_connected()
        body = client.get("/api/bridge/status").json()
        assert body["agent_connected"] is True
        assert body["agent_connected_at"] is not None

        bridge_status_mod.get_bridge_status().mark_agent_disconnected()
        body = client.get("/api/bridge/status").json()
        assert body["agent_connected"] is False
        assert body["agent_connected_at"] is None

    def test_status_defaults_tab_visible(self, client):
        """Fresh fixture starts with tab_hidden=false (visible). The
        dashboard relies on this to keep the bridge pill green by default."""
        body = client.get("/api/bridge/status").json()
        assert body["tab_hidden"] is False

    def test_status_reflects_tab_hidden_flag(self, client):
        """When the gym_server flips tab_hidden via the visibility message
        from the browser, the API endpoint must surface it so the dashboard
        can render the warning state."""
        bridge_status_mod.get_bridge_status().set_tab_hidden(True)
        body = client.get("/api/bridge/status").json()
        assert body["tab_hidden"] is True

        bridge_status_mod.get_bridge_status().set_tab_hidden(False)
        body = client.get("/api/bridge/status").json()
        assert body["tab_hidden"] is False


# ──────────────────────────────────────────────────────────────────────────────
# /api/runs/{id}/trace
# ──────────────────────────────────────────────────────────────────────────────


class TestRunTraceAPI:
    def _seed_trace(self, run_id: str, n: int = 3, *, config: str = "easy_math_add"):
        """Push n exchanges into the trace store for run_id."""
        trace = run_trace_mod.get_run_trace_store().get_or_create(run_id)
        trace.set_system_prompt(config, "you are a benchmark agent")
        for i in range(n):
            trace.record(
                config=config, episode=0, step=i,
                user_text=f"state {i}", response=f"action {i}",
                action=i, latency_ms=10.0 + i,
            )
        return trace

    def test_trace_unknown_run_returns_empty_unavailable(self, client):
        r = client.get("/api/runs/run_unknown/trace")
        assert r.status_code == 200
        body = r.json()
        assert body["available"] is False
        assert body["entries"] == []
        assert body["cursor"] == 0
        assert body["system_prompts"] == {}

    def test_trace_returns_seeded_entries(self, client):
        self._seed_trace("run_x", n=3)
        r = client.get("/api/runs/run_x/trace")
        assert r.status_code == 200
        body = r.json()
        assert body["available"] is True
        assert body["cursor"] == 3
        assert len(body["entries"]) == 3
        assert body["entries"][0]["user_text"] == "state 0"
        assert body["entries"][0]["response"] == "action 0"
        assert body["entries"][0]["action"] == 0
        assert "easy_math_add" in body["system_prompts"]

    def test_trace_since_cursor_returns_only_new(self, client):
        self._seed_trace("run_x", n=5)
        r = client.get("/api/runs/run_x/trace?since=3")
        body = r.json()
        assert [e["id"] for e in body["entries"]] == [4, 5]
        assert body["cursor"] == 5

    def test_trace_since_at_cursor_is_empty(self, client):
        self._seed_trace("run_x", n=2)
        r = client.get("/api/runs/run_x/trace?since=2")
        body = r.json()
        assert body["entries"] == []
        assert body["cursor"] == 2

    def test_trace_since_negative_rejected(self, client):
        r = client.get("/api/runs/run_x/trace?since=-1")
        assert r.status_code == 422

    def test_delete_run_drops_trace(self, client):
        agent_id = next(
            a for a in client.get("/api/agents").json() if a["provider"] == "random"
        )["id"]
        # Create and finish a run via the stub
        with patch(
            "yedi_benchmark.api.run_executor.run_benchmark_with_registry",
            _stub_runner(stop_event=None),
        ):
            r = client.post("/api/runs", json={
                "agent_id": agent_id, "mode": "metadata-a",
                "configs": ["easy_math_add"], "episodes_per_config": 1, "max_steps": 5,
            })
            run_id = r.json()["id"]
            from yedi_benchmark.api.run_executor import get_run_executor
            assert get_run_executor().wait_for_completion(timeout=5.0)

        # Manually seed a trace under that run id
        self._seed_trace(run_id, n=2)
        assert client.get(f"/api/runs/{run_id}/trace").json()["available"] is True

        # Delete and verify the trace is gone
        d = client.delete(f"/api/runs/{run_id}")
        assert d.status_code == 204
        body = client.get(f"/api/runs/{run_id}/trace").json()
        assert body["available"] is False
        assert body["entries"] == []

    def test_random_agent_run_has_no_trace(self, client):
        """Random agents never call an LLM, so no trace should be recorded."""
        agent_id = next(
            a for a in client.get("/api/agents").json() if a["provider"] == "random"
        )["id"]
        with patch(
            "yedi_benchmark.api.run_executor.run_benchmark_with_registry",
            _stub_runner(stop_event=None),
        ):
            r = client.post("/api/runs", json={
                "agent_id": agent_id, "mode": "metadata-a",
                "configs": ["easy_math_add"], "episodes_per_config": 1, "max_steps": 5,
            })
            run_id = r.json()["id"]
            from yedi_benchmark.api.run_executor import get_run_executor
            assert get_run_executor().wait_for_completion(timeout=5.0)

        body = client.get(f"/api/runs/{run_id}/trace").json()
        assert body["available"] is False
