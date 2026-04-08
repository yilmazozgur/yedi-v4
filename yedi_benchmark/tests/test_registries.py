"""Tests for AgentRegistry, PromptRegistry, and RunRegistry.

What we care about:
  - CRUD round-trips work and persist across reopens.
  - Default seeds appear on first launch.
  - Constraint violations raise the right error type.
  - Snapshot semantics: editing a record after a run does NOT mutate the run.
  - Single-active prompt invariant is enforced.
  - Run aggregates are recomputed correctly.
"""

from __future__ import annotations

import pytest

from yedi_benchmark.registries import (
    AgentConfig,
    AgentMode,
    AgentRegistry,
    ConfigResult,
    EpisodeResult,
    Prompt,
    PromptRegistry,
    RunRegistry,
    RunStatus,
)
from yedi_benchmark.registries.agents import AgentRegistryError
from yedi_benchmark.registries.prompts import PromptRegistryError
from yedi_benchmark.registries.runs import RunRegistryError


# ──────────────────────────────────────────────────────────────────────────────
# AgentRegistry
# ──────────────────────────────────────────────────────────────────────────────


class TestAgentRegistry:
    def test_seeds_defaults_on_first_launch(self, isolated_data_dir):
        reg = AgentRegistry()
        names = [a.name for a in reg.list()]
        assert "Random" in names
        assert "Claude Sonnet 4.5" in names
        assert "GPT-4o" in names
        assert "Gemini 2.5 Pro" in names

    def test_does_not_reseed_on_second_open(self, isolated_data_dir):
        reg = AgentRegistry()
        reg.delete(reg.get_by_name("GPT-4o").id)

        reg2 = AgentRegistry()
        names = [a.name for a in reg2.list()]
        assert "GPT-4o" not in names  # deletion persisted, no re-seed

    def test_create_and_get(self, isolated_data_dir):
        reg = AgentRegistry()
        new = AgentConfig(
            name="My Custom",
            provider="openai",
            model="gpt-4o-mini",
            api_key_env="OPENAI_API_KEY",
        )
        reg.create(new)

        fetched = reg.get(new.id)
        assert fetched.name == "My Custom"
        assert fetched.model == "gpt-4o-mini"

    def test_create_rejects_duplicate_name(self, isolated_data_dir):
        reg = AgentRegistry()
        with pytest.raises(AgentRegistryError, match="already exists"):
            reg.create(AgentConfig(name="Random", provider="random", model=""))

    def test_update_changes_fields(self, isolated_data_dir):
        reg = AgentRegistry()
        target = reg.get_by_name("Claude Sonnet 4.5")

        updated = reg.update(target.id, max_tokens=1024)
        assert updated.max_tokens == 1024
        assert updated.id == target.id  # id unchanged

        # Persisted across reopens
        reg2 = AgentRegistry()
        assert reg2.get(target.id).max_tokens == 1024

    def test_update_rejects_id_change(self, isolated_data_dir):
        reg = AgentRegistry()
        target = reg.get_by_name("Random")
        updated = reg.update(target.id, id="agent_evil_value")
        assert updated.id == target.id  # id silently dropped

    def test_update_rejects_duplicate_name(self, isolated_data_dir):
        reg = AgentRegistry()
        target = reg.get_by_name("Random")
        with pytest.raises(AgentRegistryError, match="already exists"):
            reg.update(target.id, name="Claude Sonnet 4.5")

    def test_delete_missing_raises(self, isolated_data_dir):
        reg = AgentRegistry()
        with pytest.raises(AgentRegistryError, match="not found"):
            reg.delete("agent_does_not_exist")

    def test_provider_validation(self, isolated_data_dir):
        with pytest.raises(ValueError, match="provider must be one of"):
            AgentConfig(name="bad", provider="totally-fake", model="x")

    def test_name_must_be_nonempty(self, isolated_data_dir):
        with pytest.raises(ValueError, match="non-empty"):
            AgentConfig(name="   ", provider="random", model="")


# ──────────────────────────────────────────────────────────────────────────────
# PromptRegistry
# ──────────────────────────────────────────────────────────────────────────────


class TestPromptRegistry:
    def test_seeds_default_v1(self, isolated_data_dir):
        reg = PromptRegistry()
        prompts = reg.list()
        assert len(prompts) == 1
        assert prompts[0].name == "Default v1"
        assert prompts[0].is_active is True
        assert len(prompts[0].dimension_rules) > 0

    def test_get_active(self, isolated_data_dir):
        reg = PromptRegistry()
        active = reg.get_active()
        assert active.name == "Default v1"

    def test_create_is_inactive_by_default(self, isolated_data_dir):
        reg = PromptRegistry()
        new = Prompt(
            name="My Prompt",
            core_rules="Play well.",
            dimension_rules={"number:add": "Add things."},
            is_active=True,  # claim active — registry must override
        )
        created = reg.create(new)
        assert created.is_active is False
        # Default is still the only active prompt
        assert reg.get_active().name == "Default v1"

    def test_activate_swaps_single_active(self, isolated_data_dir):
        reg = PromptRegistry()
        new = reg.create(Prompt(name="Other", core_rules="x"))
        reg.activate(new.id)

        active = reg.get_active()
        assert active.id == new.id

        # Old default should no longer be active
        actives = [p for p in reg.list() if p.is_active]
        assert len(actives) == 1
        assert actives[0].id == new.id

    def test_cannot_delete_active(self, isolated_data_dir):
        reg = PromptRegistry()
        active = reg.get_active()
        with pytest.raises(PromptRegistryError, match="cannot delete the active"):
            reg.delete(active.id)

    def test_delete_inactive_works(self, isolated_data_dir):
        reg = PromptRegistry()
        new = reg.create(Prompt(name="Throwaway", core_rules="x"))
        reg.delete(new.id)
        with pytest.raises(PromptRegistryError, match="not found"):
            reg.get(new.id)

    def test_clone_bumps_version(self, isolated_data_dir):
        reg = PromptRegistry()
        active = reg.get_active()
        cloned = reg.clone(active.id, "Default v2")
        assert cloned.version == active.version + 1
        assert cloned.is_active is False
        assert cloned.core_rules == active.core_rules
        assert cloned.dimension_rules == active.dimension_rules

    def test_create_rejects_duplicate_name(self, isolated_data_dir):
        reg = PromptRegistry()
        with pytest.raises(PromptRegistryError, match="already exists"):
            reg.create(Prompt(name="Default v1", core_rules="x"))

    def test_update_forbids_is_active(self, isolated_data_dir):
        reg = PromptRegistry()
        new = reg.create(Prompt(name="Other", core_rules="x"))
        # update() should silently drop is_active — must use activate() instead
        updated = reg.update(new.id, is_active=True, core_rules="y")
        assert updated.is_active is False
        assert updated.core_rules == "y"

    def test_core_rules_must_be_nonempty(self, isolated_data_dir):
        with pytest.raises(ValueError, match="non-empty"):
            Prompt(name="empty-rules", core_rules="   ")


# ──────────────────────────────────────────────────────────────────────────────
# RunRegistry — including snapshot semantics
# ──────────────────────────────────────────────────────────────────────────────


class TestRunRegistry:
    @pytest.fixture
    def setup_env(self, isolated_data_dir, isolated_runs_dir):
        """Both data + runs dirs isolated."""
        return AgentRegistry(), PromptRegistry(), RunRegistry()

    def test_create_freezes_snapshots(self, setup_env):
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Claude Sonnet 4.5")
        prompt = pr.get_active()

        record = rr.create(
            agent=agent,
            prompt=prompt,
            configs=["easy_math_add"],
            episodes_per_config=2,
            max_steps=50,
            mode=AgentMode.METADATA_CONVERSATIONAL,
        )

        # Snapshots are dicts (not foreign keys)
        assert isinstance(record.agent_snapshot, dict)
        assert record.agent_snapshot["name"] == "Claude Sonnet 4.5"
        assert isinstance(record.prompt_snapshot, dict)
        assert record.prompt_snapshot["name"] == "Default v1"
        assert record.status == RunStatus.PENDING
        assert record.episodes_total() == 2

    def test_snapshot_does_not_track_later_edits(self, setup_env):
        """The whole point of snapshots: editing the registry after a run starts
        must NOT retro-modify the run record. This is critical for bookkeeping."""
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Claude Sonnet 4.5")
        prompt = pr.get_active()

        record = rr.create(
            agent=agent,
            prompt=prompt,
            configs=["easy_math_add"],
            episodes_per_config=1,
            max_steps=50,
            mode=AgentMode.METADATA_STATELESS,
        )

        # Mutate the agent and prompt in the registries AFTER the run is created.
        ar.update(agent.id, max_tokens=9999)
        pr.update(prompt.id, core_rules="A WHOLE NEW SET OF RULES")

        # Re-fetch from disk and verify the snapshot is unchanged.
        refetched = rr.get(record.id)
        assert refetched.agent_snapshot["max_tokens"] == agent.max_tokens
        assert refetched.agent_snapshot["max_tokens"] != 9999
        assert refetched.prompt_snapshot["core_rules"] == prompt.core_rules
        assert "WHOLE NEW SET" not in refetched.prompt_snapshot["core_rules"]

    def test_random_agent_run_has_no_prompt(self, setup_env):
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Random")

        record = rr.create(
            agent=agent,
            prompt=None,
            configs=["easy_math_add"],
            episodes_per_config=1,
            max_steps=50,
            mode=AgentMode.METADATA_STATELESS,
        )

        assert record.prompt_snapshot is None

    def test_append_episode_recomputes_aggregates(self, setup_env):
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Random")

        record = rr.create(
            agent=agent,
            prompt=None,
            configs=["easy_math_add"],
            episodes_per_config=3,
            max_steps=50,
            mode=AgentMode.METADATA_STATELESS,
        )

        for i, mana in enumerate([100.0, 200.0, 300.0]):
            rr.append_episode(
                record.id,
                "easy_math_add",
                EpisodeResult(
                    episode_idx=i,
                    max_mana=mana,
                    total_reward=mana - 200.0,
                    steps=50,
                    game_over=False,
                ),
            )

        refetched = rr.get(record.id)
        cfg = refetched.results["easy_math_add"]
        assert len(cfg.episodes) == 3
        assert cfg.mean_max_mana == 200.0
        assert cfg.best_max_mana == 300.0
        assert cfg.std_max_mana > 0  # not zero with 3 distinct values
        assert refetched.episodes_done() == 3

    def test_status_transitions(self, setup_env):
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Random")
        record = rr.create(
            agent=agent,
            prompt=None,
            configs=["easy_math_add"],
            episodes_per_config=1,
            max_steps=50,
            mode=AgentMode.METADATA_STATELESS,
        )
        assert record.status == RunStatus.PENDING

        rr.update_status(record.id, RunStatus.RUNNING)
        assert rr.get(record.id).status == RunStatus.RUNNING
        assert rr.get(record.id).finished_at is None

        rr.update_status(record.id, RunStatus.COMPLETED)
        completed = rr.get(record.id)
        assert completed.status == RunStatus.COMPLETED
        assert completed.finished_at is not None

    def test_set_error_marks_failed(self, setup_env):
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Random")
        record = rr.create(
            agent=agent, prompt=None, configs=["easy_math_add"],
            episodes_per_config=1, max_steps=50,
            mode=AgentMode.METADATA_STATELESS,
        )
        rr.set_error(record.id, "boom")
        failed = rr.get(record.id)
        assert failed.status == RunStatus.FAILED
        assert failed.error == "boom"
        assert failed.finished_at is not None

    def test_list_filters_by_status(self, setup_env):
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Random")
        a = rr.create(
            agent=agent, prompt=None, configs=["easy_math_add"],
            episodes_per_config=1, max_steps=50,
            mode=AgentMode.METADATA_STATELESS,
        )
        b = rr.create(
            agent=agent, prompt=None, configs=["easy_math_add"],
            episodes_per_config=1, max_steps=50,
            mode=AgentMode.METADATA_STATELESS,
        )
        rr.update_status(b.id, RunStatus.COMPLETED)

        pending_ids = {r.id for r in rr.list(status=RunStatus.PENDING)}
        completed_ids = {r.id for r in rr.list(status=RunStatus.COMPLETED)}
        assert a.id in pending_ids
        assert b.id in completed_ids
        assert a.id not in completed_ids

    def test_create_rejects_empty_configs(self, setup_env):
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Random")
        with pytest.raises(RunRegistryError, match="non-empty"):
            rr.create(
                agent=agent, prompt=None, configs=[],
                episodes_per_config=1, max_steps=50,
                mode=AgentMode.METADATA_STATELESS,
            )

    def test_create_rejects_zero_episodes(self, setup_env):
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Random")
        with pytest.raises(RunRegistryError):
            rr.create(
                agent=agent, prompt=None, configs=["easy_math_add"],
                episodes_per_config=0, max_steps=50,
                mode=AgentMode.METADATA_STATELESS,
            )

    def test_reconcile_orphans_marks_running_failed(self, setup_env):
        """A run stranded in RUNNING (because the worker died) must be
        rewritten to FAILED with a clear error so the UI can clean it up.
        Without this the dashboard shows a row that can't be cancelled
        (executor 404s) and used to hide its Delete button."""
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Random")
        stranded = rr.create(
            agent=agent, prompt=None, configs=["easy_math_add"],
            episodes_per_config=1, max_steps=50,
            mode=AgentMode.METADATA_STATELESS,
        )
        rr.update_status(stranded.id, RunStatus.RUNNING)
        # A second run that's already finished — must be left alone.
        finished = rr.create(
            agent=agent, prompt=None, configs=["easy_math_add"],
            episodes_per_config=1, max_steps=50,
            mode=AgentMode.METADATA_STATELESS,
        )
        rr.update_status(finished.id, RunStatus.COMPLETED)

        reconciled = rr.reconcile_orphans()

        assert stranded.id in reconciled
        assert finished.id not in reconciled

        after = rr.get(stranded.id)
        assert after.status == RunStatus.FAILED
        assert after.error is not None
        assert "orphan" in after.error.lower()
        assert after.finished_at is not None

        # The completed run is untouched
        still_done = rr.get(finished.id)
        assert still_done.status == RunStatus.COMPLETED

    def test_reconcile_orphans_handles_pending(self, setup_env):
        """A PENDING run (executor crashed before it ever flipped to RUNNING)
        is also an orphan from the user's perspective."""
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Random")
        pending = rr.create(
            agent=agent, prompt=None, configs=["easy_math_add"],
            episodes_per_config=1, max_steps=50,
            mode=AgentMode.METADATA_STATELESS,
        )
        # Don't transition — leave as PENDING
        assert pending.status == RunStatus.PENDING

        reconciled = rr.reconcile_orphans()
        assert pending.id in reconciled
        assert rr.get(pending.id).status == RunStatus.FAILED

    def test_reconcile_orphans_is_idempotent(self, setup_env):
        """Running reconciliation twice must not re-touch already-failed runs."""
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Random")
        record = rr.create(
            agent=agent, prompt=None, configs=["easy_math_add"],
            episodes_per_config=1, max_steps=50,
            mode=AgentMode.METADATA_STATELESS,
        )
        rr.update_status(record.id, RunStatus.RUNNING)

        first = rr.reconcile_orphans()
        second = rr.reconcile_orphans()

        assert record.id in first
        assert second == []  # nothing left to reconcile

    def test_reconcile_orphans_custom_reason(self, setup_env):
        ar, pr, rr = setup_env
        agent = ar.get_by_name("Random")
        record = rr.create(
            agent=agent, prompt=None, configs=["easy_math_add"],
            episodes_per_config=1, max_steps=50,
            mode=AgentMode.METADATA_STATELESS,
        )
        rr.update_status(record.id, RunStatus.RUNNING)

        rr.reconcile_orphans(reason="killed by sigterm")
        assert rr.get(record.id).error == "killed by sigterm"


# ──────────────────────────────────────────────────────────────────────────────
# AgentMode enum properties
# ──────────────────────────────────────────────────────────────────────────────


class TestAgentMode:
    @pytest.mark.parametrize("mode,vision,conversational,compact,memory_label", [
        (AgentMode.METADATA_STATELESS, False, False, False, "stateless"),
        (AgentMode.METADATA_CONVERSATIONAL, False, True, False, "conversational"),
        (AgentMode.METADATA_COMPACT, False, False, True, "compact"),
        (AgentMode.VISION_STATELESS, True, False, False, "stateless"),
        (AgentMode.VISION_CONVERSATIONAL, True, True, False, "conversational"),
        (AgentMode.VISION_COMPACT, True, False, True, "compact"),
    ])
    def test_mode_properties(self, mode, vision, conversational, compact, memory_label):
        assert mode.use_screenshot is vision
        assert mode.is_conversational is conversational
        assert mode.is_compact is compact
        assert mode.memory_label == memory_label

    def test_modes_are_mutually_exclusive(self):
        # A mode can be at most one of stateless/conversational/compact.
        for mode in AgentMode:
            assert sum([
                not mode.is_conversational and not mode.is_compact,  # stateless
                mode.is_conversational,
                mode.is_compact,
            ]) == 1
