"""Decision Transformer pipeline tests.

Covers the four places DT can silently break:

  1. **Return-to-go** — wrong RTG means the policy conditions on the
     wrong scalar and nothing downstream notices (no exception, just
     degraded accuracy).
  2. **Left-padding + attention mask** — short prefixes must not leak
     zeros into the transformer's decisions; pad positions must be
     ignored by attention and by the loss.
  3. **Causal masking** — no s_t token may attend to a_t or any token
     from a later timestep.
  4. **Convergence on a trivially-patterned dataset** — signal → next
     action. Same pattern as the BC convergence test, adapted to
     sequence input.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from yedi_benchmark.learning.dataset import OBS_DIM, load_parquet
from yedi_benchmark.learning.dt_dataset import (
    DTDataset,
    attach_rewards,
    compute_returns_to_go,
    load_dt_parquet,
)
from yedi_benchmark.learning.dt_model import (
    DecisionTransformer,
    DTModelConfig,
    dt_accuracy,
    dt_soft_cross_entropy,
)
from yedi_benchmark.learning.export_dataset import export
from yedi_benchmark.learning.featurizer import NUM_ACTIONS, NUM_SLOTS
from yedi_benchmark.learning.train_dt import _load_rewards, train

from yedi_benchmark.agents.dt_agent import (
    DEFAULT_TARGET_RETURN,
    DecisionTransformerAgent,
)


# Reuse the BC synthetic-dataset helper shape so both test suites share
# the same ground truth about how episodes are laid out on disk.


def _slot(**kw) -> dict:
    base = {"occupied": False, "card_mana": 0.0, "merges_done": 0,
            "number_value": 0.0, "color_r": 0.0, "color_g": 0.0, "color_b": 0.0,
            "shape_index": 0, "word_value": "", "memory_hidden": False}
    base.update(kw)
    return base


def _state(mana: float, signal: float = 0.0) -> dict:
    slots = [_slot() for _ in range(NUM_SLOTS)]
    slots[0] = _slot(occupied=True, card_mana=10, number_value=signal,
                     word_value="apple")
    return {
        "mana": mana, "mana_max": mana, "timer_remaining": 10.0,
        "beat_phase": 0.1, "config_key": "math-add",
        "valid_actions": [0, 1, 2], "slots": slots,
    }


def _write_dataset(tmp_path: Path, num_eps: int = 6, steps_per_ep: int = 5) -> Path:
    logs = tmp_path / "logs"
    logs.mkdir()
    for i in range(num_eps):
        ep_dir = logs / f"episode_ep{i:02d}"
        ep_dir.mkdir()
        with (ep_dir / "events.jsonl").open("w") as f:
            f.write(json.dumps({"type": "episode_start",
                                "episode_id": f"ep{i:02d}",
                                "agent_name": "Human-1", "config": {}}) + "\n")
            for s in range(steps_per_ep):
                action = s % 3
                next_action = (s + 1) % 3
                signal = float(next_action)
                step = {"type": "step", "step": s, "action": action,
                        "command": {"type": "draw_card"},
                        "observation": {"action_mask":
                            [1 if a in (0, 1, 2) else 0 for a in range(37)]},
                        "reward": 0.01 * (s + 1),
                        "terminated": False, "truncated": False,
                        "raw_state": _state(100.0 + s, signal=signal)}
                f.write(json.dumps(step) + "\n")
            f.write(json.dumps({"type": "episode_end"}) + "\n")
    out = tmp_path / "data.parquet"
    export(logs, out)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Return-to-go
# ──────────────────────────────────────────────────────────────────────────────


class TestReturnToGo:
    def test_rtg_is_reverse_cumsum(self):
        r = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        rtg = compute_returns_to_go(r)
        np.testing.assert_allclose(rtg, [1.0, 0.9, 0.7, 0.4], atol=1e-6)

    def test_rtg_zero_on_empty(self):
        rtg = compute_returns_to_go(np.array([], dtype=np.float32))
        assert rtg.shape == (0,)


# ──────────────────────────────────────────────────────────────────────────────
# Padding + attention mask
# ──────────────────────────────────────────────────────────────────────────────


class TestWindowing:
    def test_first_step_window_is_left_padded(self, tmp_path):
        data = _write_dataset(tmp_path, num_eps=2, steps_per_ep=4)
        ds = load_dt_parquet(data, context_length=5)
        # The first sample of the first episode has only 1 real step,
        # so 4 pad positions at the front, real data at the last slot.
        sample = ds[0]
        states, actions, rtgs, timesteps, attn, equivs, _cfg = sample
        assert attn.shape == (5,)
        # Expect the last position to be real; earlier positions padded.
        assert attn[-1].item() == 1
        assert attn[:-1].sum().item() == 0
        # Pad states must be exactly zero (not random memory).
        assert torch.all(states[:-1] == 0)
        # The real position's action is the action at step 0 after the
        # pre→post shift — a value in {0,1,2}.
        assert 0 <= int(actions[-1]) <= 2

    def test_late_step_window_is_full(self, tmp_path):
        data = _write_dataset(tmp_path, num_eps=1, steps_per_ep=6)
        ds = load_dt_parquet(data, context_length=3)
        # featurize_episode emits N-1 rows for an N-step episode.
        # With steps_per_ep=6 we get 5 rows; any sample index ≥2 should
        # yield a fully-populated window.
        states, actions, rtgs, timesteps, attn, _eq, _cfg = ds[-1]
        assert attn.sum().item() == 3  # all three positions are real
        # Timesteps must be contiguous ascending.
        ts = timesteps.tolist()
        assert ts == sorted(ts) and all(b - a == 1 for a, b in zip(ts, ts[1:]))


# ──────────────────────────────────────────────────────────────────────────────
# Causal masking + pad behaviour
# ──────────────────────────────────────────────────────────────────────────────


class TestCausalAndPadMasking:
    def test_s_token_does_not_leak_future_action(self):
        """Changing a FUTURE action token must not change the current
        s-token's prediction — that's what causal masking buys us."""
        cfg = DTModelConfig(context_length=4, d_model=16, n_heads=2, n_layers=1,
                            dropout=0.0)
        model = DecisionTransformer(cfg).eval()
        B, K = 1, cfg.context_length
        states = torch.randn(B, K, OBS_DIM)
        actions_a = torch.zeros(B, K, dtype=torch.long)
        actions_b = actions_a.clone()
        actions_b[0, -1] = 5  # perturb the last timestep's action
        rtgs = torch.zeros(B, K)
        ts = torch.arange(K).unsqueeze(0)
        attn = torch.ones(B, K)
        with torch.no_grad():
            logits_a = model(states, actions_a, rtgs, ts, attn)
            logits_b = model(states, actions_b, rtgs, ts, attn)
        # s-tokens for positions 0..K-2 should be identical: those s
        # positions sit strictly before a_{K-1} in the interleaved
        # sequence, so causal attention cannot see the changed token.
        torch.testing.assert_close(
            logits_a[:, :-1, :], logits_b[:, :-1, :], atol=1e-6, rtol=1e-6,
        )

    def test_loss_ignores_pad_positions(self):
        """A fully-padded sample contributes zero loss, never NaN."""
        cfg = DTModelConfig(context_length=3, d_model=16, n_heads=2, n_layers=1)
        model = DecisionTransformer(cfg).eval()
        B, K = 2, cfg.context_length
        states = torch.randn(B, K, OBS_DIM)
        actions = torch.zeros(B, K, dtype=torch.long)
        rtgs = torch.zeros(B, K)
        ts = torch.zeros(B, K, dtype=torch.long)
        attn = torch.zeros(B, K)
        attn[0, -1] = 1   # sample 0 has one real position; sample 1 is all pad
        equivs = torch.zeros(B, K, NUM_ACTIONS)
        equivs[0, -1, 2] = 1
        logits = model(states, actions, rtgs, ts, attn)
        loss = dt_soft_cross_entropy(logits, equivs, attn)
        assert torch.isfinite(loss)
        # Only one real position across the batch contributed.
        correct, total = dt_accuracy(logits, equivs, attn)
        assert total == 1


# ──────────────────────────────────────────────────────────────────────────────
# End-to-end training
# ──────────────────────────────────────────────────────────────────────────────


class TestTrainLoop:
    def test_train_converges_on_tiny_deterministic_dataset(self, tmp_path):
        """Same input→label pattern as the BC convergence test. With
        enough epochs a 2-layer DT should beat random (≈1/3)."""
        data = _write_dataset(tmp_path, num_eps=6, steps_per_ep=6)
        ds = load_parquet(data)
        rewards = _load_rewards(data, sources=None)
        summary = train(
            ds, rewards=rewards, out_path=tmp_path / "ckpt.pt",
            context_length=5,
            d_model=32, n_heads=2, n_layers=1, dropout=0.0,
            epochs=80, batch_size=8, lr=3e-3, seed=0, device="cpu",
            k_folds=1, eval_fraction=0.34,
            log_fn=lambda *a, **k: None,
        )
        assert summary["best_eval_acc"] > 0.8
        assert (tmp_path / "ckpt.pt").exists()
        assert summary["model_kind"] == "decision_transformer"
        assert summary["context_length"] == 5

    def test_kfold_reports_per_fold_and_retrains_on_all(self, tmp_path):
        data = _write_dataset(tmp_path, num_eps=6, steps_per_ep=5)
        ds = load_parquet(data)
        rewards = _load_rewards(data, sources=None)
        summary = train(
            ds, rewards=rewards, out_path=tmp_path / "ckpt.pt",
            context_length=4,
            d_model=16, n_heads=2, n_layers=1, dropout=0.0,
            epochs=3, batch_size=8, seed=0, device="cpu",
            k_folds=3, log_fn=lambda *a, **k: None,
        )
        assert len(summary["fold_eval_accs"]) == 3
        # Shipped checkpoint re-trained on all rows — no held-out eval.
        assert summary["eval_rows"] == 0
        assert summary["train_rows"] == len(ds)


# ──────────────────────────────────────────────────────────────────────────────
# Live DT agent
# ──────────────────────────────────────────────────────────────────────────────


def _train_small_dt(tmp_path: Path, *, context_length: int = 4) -> Path:
    """Helper: produce a tiny DT checkpoint for agent-level tests."""
    data = _write_dataset(tmp_path, num_eps=4, steps_per_ep=4)
    ds = load_parquet(data)
    rewards = _load_rewards(data, sources=None)
    ckpt = tmp_path / "dt.pt"
    train(
        ds, rewards=rewards, out_path=ckpt,
        context_length=context_length,
        d_model=16, n_heads=2, n_layers=1, dropout=0.0,
        epochs=2, batch_size=8, seed=0, device="cpu",
        k_folds=1, eval_fraction=0.25,
        log_fn=lambda *a, **k: None,
    )
    return ckpt


class TestDTAgent:
    def test_loaded_agent_acts_and_respects_mask(self, tmp_path):
        ckpt = _train_small_dt(tmp_path)
        agent = DecisionTransformerAgent(ckpt, device="cpu")

        raw = {"mana": 123.0, "mana_max": 123.0, "timer_remaining": 10.0,
               "beat_phase": 0.1, "config_key": "math-add",
               "valid_actions": [0, 2],
               "slots": [{"occupied": False, "card_mana": 0.0, "merges_done": 0,
                          "number_value": 0.0, "color_r": 0.0, "color_g": 0.0,
                          "color_b": 0.0, "shape_index": 0, "word_value": "",
                          "memory_hidden": False} for _ in range(NUM_SLOTS)]}
        obs = {"action_mask": [1 if a in (0, 2) else 0 for a in range(NUM_ACTIONS)]}
        action = agent.act(obs, {"raw_state": raw})
        assert action in (0, 2)

    def test_rtg_decrements_with_realised_reward(self, tmp_path):
        """After ``on_step_result`` the remaining return must drop by the
        reward just seen — this is the whole point of DT's rolling RTG."""
        ckpt = _train_small_dt(tmp_path)
        agent = DecisionTransformerAgent(ckpt, device="cpu", target_return=10.0)
        assert agent._remaining_return == pytest.approx(10.0)
        agent.on_step_result(action=0, reward=0.25, terminated=False, info={})
        assert agent._remaining_return == pytest.approx(9.75)
        agent.on_step_result(action=1, reward=-0.5, terminated=False, info={})
        assert agent._remaining_return == pytest.approx(10.25)

    def test_reset_clears_context_between_episodes(self, tmp_path):
        """``reset`` must drop rolling buffers so episode N+1 doesn't attend
        to tokens from episode N. If it didn't, the agent would condition on
        a stale RTG + 100+ steps of phantom history."""
        ckpt = _train_small_dt(tmp_path)
        agent = DecisionTransformerAgent(ckpt, device="cpu")
        raw = {"mana": 50.0, "mana_max": 50.0, "timer_remaining": 5.0,
               "beat_phase": 0.3, "config_key": "math-add",
               "valid_actions": [0],
               "slots": [{"occupied": False, "card_mana": 0.0, "merges_done": 0,
                          "number_value": 0.0, "color_r": 0.0, "color_g": 0.0,
                          "color_b": 0.0, "shape_index": 0, "word_value": "",
                          "memory_hidden": False} for _ in range(NUM_SLOTS)]}
        obs = {"action_mask": [1] + [0] * (NUM_ACTIONS - 1)}
        agent.act(obs, {"raw_state": raw})
        agent.on_step_result(action=0, reward=0.1, terminated=False, info={})
        assert len(agent._states) == 1
        assert agent._t == 1
        assert agent._remaining_return != DEFAULT_TARGET_RETURN

        agent.reset()
        assert agent._states == []
        assert agent._actions == []
        assert agent._rtgs == []
        assert agent._timesteps == []
        assert agent._t == 0
        assert agent._remaining_return == pytest.approx(DEFAULT_TARGET_RETURN)

    def test_load_rejects_dim_drift(self, tmp_path):
        ckpt = _train_small_dt(tmp_path)
        raw = torch.load(ckpt, weights_only=False)
        raw["summary"]["obs_dim"] = OBS_DIM + 1
        bad = tmp_path / "bad.pt"
        torch.save(raw, bad)
        with pytest.raises(ValueError, match="obs_dim"):
            DecisionTransformerAgent(bad, device="cpu")

    def test_load_rejects_wrong_model_kind(self, tmp_path):
        """If a BC checkpoint is loaded with the DT agent the load must fail
        with a clear message — not silently run with scrambled tensors."""
        ckpt = _train_small_dt(tmp_path)
        raw = torch.load(ckpt, weights_only=False)
        raw["summary"]["model_kind"] = "behavior_cloning"
        bad = tmp_path / "bc_like.pt"
        torch.save(raw, bad)
        with pytest.raises(ValueError, match="model_kind"):
            DecisionTransformerAgent(bad, device="cpu")

    def test_runner_factory_routes_dt_provider(self, tmp_path):
        """create_agent_from_registry("dt") returns a live DT agent loaded
        from the checkpoint path in AgentConfig.model."""
        from yedi_benchmark.benchmark_runner import create_agent_from_registry
        from yedi_benchmark.registries.models import AgentConfig, AgentMode

        ckpt = _train_small_dt(tmp_path)
        cfg = AgentConfig(name="dt-test", provider="dt", model=str(ckpt))
        agent = create_agent_from_registry(
            cfg, prompt=None, mode_enum=AgentMode.METADATA_STATELESS,
        )
        assert isinstance(agent, DecisionTransformerAgent)

    def test_runner_factory_rejects_bad_dt_checkpoint(self, tmp_path):
        from yedi_benchmark.benchmark_runner import create_agent_from_registry
        from yedi_benchmark.registries.models import AgentConfig, AgentMode

        cfg = AgentConfig(name="dt-bad", provider="dt",
                          model=str(tmp_path / "does_not_exist.pt"))
        with pytest.raises(ValueError, match="not found"):
            create_agent_from_registry(
                cfg, prompt=None, mode_enum=AgentMode.METADATA_STATELESS,
            )
