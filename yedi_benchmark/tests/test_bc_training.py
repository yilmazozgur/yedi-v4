"""BC training pipeline tests.

Covers the three places BC can silently break:

  1. **Episode-level split leakage** — a row-level shuffle would let the
     model memorize the state it saw at training time.
  2. **Masked logits** — if the mask isn't applied before cross-entropy,
     the model can learn to pick illegal actions (and the runner would
     then fall back to DRAW, hiding the bug).
  3. **Feature-layout drift between offline and live** — the inference
     code path (``_featurize_live``) must produce the same vector as the
     offline featurizer, or a loaded checkpoint predicts nonsense.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from yedi_benchmark.agents.bc_agent import BehaviorCloningAgent, _featurize_live
from yedi_benchmark.learning.dataset import (
    OBS_DIM,
    BCDataset,
    load_parquet,
    split_by_episode,
)
from yedi_benchmark.learning.export_dataset import export
from yedi_benchmark.learning.featurizer import (
    NUM_ACTIONS,
    NUM_SLOTS,
    featurize_step,
)
from yedi_benchmark.learning.model import (
    BCModelConfig,
    BCPolicy,
    bc_cross_entropy,
)
from yedi_benchmark.learning.train_bc import train


# ──────────────────────────────────────────────────────────────────────────────
# Shared fixture: a tiny synthetic dataset on disk. Using real export +
# load paths catches drift in the whole pipeline, not just the model.
# ──────────────────────────────────────────────────────────────────────────────


def _slot(**kw) -> dict:
    base = {"occupied": False, "card_mana": 0.0, "merges_done": 0,
            "number_value": 0.0, "color_r": 0.0, "color_g": 0.0, "color_b": 0.0,
            "shape_index": 0, "word_value": "", "memory_hidden": False}
    base.update(kw)
    return base


def _state(mana: float, signal: float = 0.0) -> dict:
    """``signal`` goes into slot[0].number_value so a tiny MLP has a
    crystal-clear input→label mapping for convergence tests."""
    slots = [_slot() for _ in range(NUM_SLOTS)]
    slots[0] = _slot(occupied=True, card_mana=10, number_value=signal,
                     word_value="apple")
    return {
        "mana": mana, "mana_max": mana, "timer_remaining": 10.0,
        "beat_phase": 0.1, "config_key": "math-add",
        "valid_actions": [0, 1, 2], "slots": slots,
    }


def _write_dataset(tmp_path: Path, num_eps: int = 6, steps_per_ep: int = 5) -> Path:
    """Write a synthetic logs dir.

    The featurizer shifts action onto the previous step's state, so we
    have to encode the "right answer for step k" into step k-1's signal
    feature — otherwise the pairs produced by the shift don't contain
    any learnable pattern.
    """
    logs = tmp_path / "logs"
    logs.mkdir()
    for i in range(num_eps):
        ep_dir = logs / f"episode_ep{i:02d}"
        ep_dir.mkdir()
        with (ep_dir / "events.jsonl").open("w") as f:
            name = "Greedy" if i % 2 == 0 else "Human-1"
            f.write(json.dumps({"type": "episode_start",
                                "episode_id": f"ep{i:02d}",
                                "agent_name": name, "config": {}}) + "\n")
            for s in range(steps_per_ep):
                action = s % 3  # label for this step (valid_actions={0,1,2})
                # Signal lives in step k's state so it can predict step
                # k+1's action after the shift. The shifted pair is
                # (state_from_step_{k-1}, action_k), i.e. signal_{k-1}
                # must equal action_k.
                next_action = (s + 1) % 3
                signal = float(next_action)
                step = {"type": "step", "step": s, "action": action,
                        "command": {"type": "draw_card"},
                        "observation": {"action_mask":
                            [1 if a in (0, 1, 2) else 0 for a in range(37)]},
                        "reward": 0.01, "terminated": False,
                        "truncated": False,
                        "raw_state": _state(100.0 + s, signal=signal)}
                f.write(json.dumps(step) + "\n")
            f.write(json.dumps({"type": "episode_end"}) + "\n")
    out = tmp_path / "data.parquet"
    export(logs, out)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Split
# ──────────────────────────────────────────────────────────────────────────────


class TestEpisodeSplit:
    def test_no_episode_appears_in_both_splits(self, tmp_path):
        ds = load_parquet(_write_dataset(tmp_path, num_eps=10))
        train_ds, eval_ds, _ = split_by_episode(ds, eval_fraction=0.3, seed=0)
        train_eps = set(train_ds.episode_ids.tolist())
        eval_eps = set(eval_ds.episode_ids.tolist())
        assert train_eps.isdisjoint(eval_eps)
        assert len(train_eps) + len(eval_eps) == 10

    def test_split_is_deterministic_with_seed(self, tmp_path):
        ds = load_parquet(_write_dataset(tmp_path, num_eps=8))
        _, eval1, _ = split_by_episode(ds, eval_fraction=0.25, seed=7)
        _, eval2, _ = split_by_episode(ds, eval_fraction=0.25, seed=7)
        assert np.array_equal(eval1.episode_ids, eval2.episode_ids)


# ──────────────────────────────────────────────────────────────────────────────
# Masking behaviour
# ──────────────────────────────────────────────────────────────────────────────


class TestMaskingBehavior:
    def test_inference_mask_zeros_illegal_probability(self):
        """At inference the mask is applied to logits so the model
        never assigns probability to illegal actions, even if training
        left some mass there."""
        model = BCPolicy(BCModelConfig(hidden_sizes=(16,), dropout=0.0))
        feats = torch.randn(4, OBS_DIM)
        mask = torch.zeros(4, NUM_ACTIONS)
        mask[:, [0, 1, 2]] = 1
        logits = model(feats, mask)
        probs = torch.softmax(logits, dim=1)
        assert probs[:, 3:].sum().item() < 1e-4

    def test_training_forward_is_unmasked(self):
        """Calling forward without a mask should leave logits
        unmodified — the train loop relies on this to compute plain
        cross-entropy without touching possibly-stale dataset masks."""
        model = BCPolicy(BCModelConfig(hidden_sizes=(16,), dropout=0.0))
        feats = torch.randn(2, OBS_DIM)
        logits_no_mask = model(feats)
        target = torch.tensor([0, 5])
        loss = bc_cross_entropy(logits_no_mask, target)
        loss.backward()
        assert torch.isfinite(loss)
        # Range sanity: CE at random init over 37 classes ≈ log(37) ≈ 3.6.
        # If the forward accidentally applied a -1e9 mask, loss would
        # be ~1e8.
        assert loss.item() < 100.0


# ──────────────────────────────────────────────────────────────────────────────
# Full training loop
# ──────────────────────────────────────────────────────────────────────────────


class TestTrainLoop:
    def test_train_converges_on_tiny_deterministic_dataset(self, tmp_path):
        """With 6 episodes of trivially-patterned actions, a couple
        epochs should push eval accuracy well above random (1/3)."""
        data = _write_dataset(tmp_path, num_eps=6, steps_per_ep=6)
        ds = load_parquet(data)
        summary = train(
            ds,
            out_path=tmp_path / "ckpt.pt",
            eval_fraction=0.34,  # ~2 eval episodes
            epochs=60,
            batch_size=8,
            lr=3e-3,
            dropout=0.0,
            seed=0,
            device="cpu",
            k_folds=1,  # single split keeps the convergence target tight
            log_fn=lambda *a, **k: None,
        )
        assert summary["best_eval_acc"] > 0.9
        assert (tmp_path / "ckpt.pt").exists()
        # training summary is self-describing
        assert summary["obs_dim"] == OBS_DIM
        assert summary["num_actions"] == NUM_ACTIONS

    def test_kfold_produces_mean_and_std_over_folds(self, tmp_path):
        """Default path: k-fold CV reports mean/std/per-fold accs and ships
        a checkpoint retrained on the full dataset (eval_rows=0)."""
        data = _write_dataset(tmp_path, num_eps=6, steps_per_ep=4)
        ds = load_parquet(data)
        summary = train(
            ds, out_path=tmp_path / "ckpt.pt",
            epochs=5, batch_size=8, lr=3e-3, dropout=0.0, seed=0,
            device="cpu", k_folds=3, log_fn=lambda *a, **k: None,
        )
        assert summary["k_folds"] == 3
        assert len(summary["fold_eval_accs"]) == 3
        assert summary["std_eval_acc"] >= 0.0
        # Shipped checkpoint was retrained on all rows — no held-out eval.
        assert summary["eval_rows"] == 0
        assert summary["train_rows"] == len(ds)

    def test_kfold_clamps_to_leave_one_out_for_tiny_data(self, tmp_path):
        """k_folds larger than num_episodes should clamp, not crash."""
        data = _write_dataset(tmp_path, num_eps=3, steps_per_ep=3)
        ds = load_parquet(data)
        summary = train(
            ds, out_path=tmp_path / "ckpt.pt",
            epochs=2, batch_size=8, device="cpu",
            k_folds=10, log_fn=lambda *a, **k: None,
        )
        # 3 episodes → 3 folds (leave-one-out)
        assert len(summary["fold_eval_accs"]) == 3

    def test_raises_when_split_is_empty(self, tmp_path):
        data = _write_dataset(tmp_path, num_eps=1, steps_per_ep=3)
        ds = load_parquet(data)
        with pytest.raises(ValueError):
            train(ds, out_path=tmp_path / "ckpt.pt", epochs=1,
                  eval_fraction=0.5, device="cpu", k_folds=1,
                  log_fn=lambda *a, **k: None)


# ──────────────────────────────────────────────────────────────────────────────
# Live featurizer parity
# ──────────────────────────────────────────────────────────────────────────────


class TestLiveInferenceParity:
    def test_live_featurizer_matches_offline_featurizer(self):
        """``BehaviorCloningAgent`` must featurize observations byte-for-byte
        the same way the Parquet exporter did — otherwise the model sees
        a different distribution at inference than at training."""
        raw = _state(150.0)
        step = {"type": "step", "step": 0, "action": 1,
                "command": {}, "observation": {"action_mask": [1]*37},
                "reward": 0.0, "terminated": False, "truncated": False,
                "raw_state": raw}
        offline = featurize_step(step, episode_id="e", agent_name="x",
                                 agent_source="human")
        # Offline concatenates [scalars, slots, word_hash, dims_active].
        offline_vec = np.concatenate([
            np.array([offline["mana"], offline["mana_max"],
                      offline["timer_remaining"], offline["beat_phase"]],
                     dtype=np.float32),
            np.array(offline["slots"], dtype=np.float32),
            np.array(offline["word_hash"], dtype=np.float32),
            np.array(offline["dims_active"], dtype=np.float32),
            np.array(offline["sub_modes_active"], dtype=np.float32),
        ])
        live_vec = _featurize_live(raw)
        np.testing.assert_array_equal(offline_vec, live_vec)


class TestBCAgent:
    def test_loaded_agent_acts_and_respects_mask(self, tmp_path):
        data = _write_dataset(tmp_path, num_eps=4, steps_per_ep=4)
        ds = load_parquet(data)
        train(ds, out_path=tmp_path / "ckpt.pt", eval_fraction=0.25,
              epochs=3, batch_size=8, lr=1e-3, dropout=0.0, seed=0,
              device="cpu", k_folds=1, log_fn=lambda *a, **k: None)

        agent = BehaviorCloningAgent(tmp_path / "ckpt.pt", device="cpu")
        raw = _state(123.0)
        # Only actions 0 and 2 are legal here — any chosen action must
        # be one of them.
        obs = {"action_mask": [1 if a in (0, 2) else 0 for a in range(37)]}
        info = {"raw_state": raw}
        action = agent.act(obs, info)
        assert action in (0, 2)

    def test_runner_factory_routes_bc_provider(self, tmp_path):
        """create_agent_from_registry("bc") returns a live BC agent loaded from
        the checkpoint in AgentConfig.model. This is the end-to-end check that
        the "bc" pseudo-provider is reachable from the benchmark runner."""
        from yedi_benchmark.benchmark_runner import create_agent_from_registry
        from yedi_benchmark.registries.models import AgentConfig, AgentMode

        data = _write_dataset(tmp_path, num_eps=4, steps_per_ep=3)
        ds = load_parquet(data)
        ckpt = tmp_path / "ckpt.pt"
        train(ds, out_path=ckpt, eval_fraction=0.25, epochs=1,
              batch_size=8, device="cpu", k_folds=1,
              log_fn=lambda *a, **k: None)

        cfg = AgentConfig(name="bc-test", provider="bc", model=str(ckpt))
        agent = create_agent_from_registry(
            cfg, prompt=None, mode_enum=AgentMode.METADATA_STATELESS,
        )
        assert isinstance(agent, BehaviorCloningAgent)

    def test_runner_factory_rejects_bad_bc_checkpoint(self, tmp_path):
        """A missing or wrong-extension checkpoint must raise at factory time,
        not at the first act() call mid-run."""
        from yedi_benchmark.benchmark_runner import create_agent_from_registry
        from yedi_benchmark.registries.models import AgentConfig, AgentMode

        cfg = AgentConfig(name="bc-bad", provider="bc",
                          model=str(tmp_path / "does_not_exist.pt"))
        with pytest.raises(ValueError, match="not found"):
            create_agent_from_registry(
                cfg, prompt=None, mode_enum=AgentMode.METADATA_STATELESS,
            )

    def test_load_rejects_dim_drift(self, tmp_path):
        data = _write_dataset(tmp_path, num_eps=4, steps_per_ep=3)
        ds = load_parquet(data)
        train(ds, out_path=tmp_path / "ckpt.pt", eval_fraction=0.25,
              epochs=1, batch_size=8, device="cpu", k_folds=1,
              log_fn=lambda *a, **k: None)

        # Tamper with the saved summary to simulate a future featurizer change.
        ckpt = torch.load(tmp_path / "ckpt.pt", weights_only=False)
        ckpt["summary"]["obs_dim"] = OBS_DIM + 1
        torch.save(ckpt, tmp_path / "bad.pt")

        with pytest.raises(ValueError, match="obs_dim"):
            BehaviorCloningAgent(tmp_path / "bad.pt", device="cpu")
