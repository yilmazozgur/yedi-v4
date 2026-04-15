"""DecisionTransformerAgent — loads a trained DT checkpoint and plays live.

Inference-time bookkeeping
--------------------------
A Decision Transformer is conditioned on **return-to-go**: the model
chooses actions to hit a target cumulative reward. The agent therefore
maintains, across calls within an episode:

  * ``_states``     — flat featurized observations seen so far
  * ``_actions``    — the actions emitted at each step (action at step t
                      is appended *after* we've predicted it)
  * ``_rtgs``       — the remaining return target at each step
  * ``_timesteps``  — episode-position indices

At each ``act()`` we slide the last ``K = context_length`` entries into a
window, left-padded if the episode is younger than ``K`` steps. The
forward pass returns logits at every s-token position; we read the
*last* one (current step) and argmax-after-mask to pick an action.

``on_step_result`` decrements the remaining return by the realised
reward, so the next step's RTG is the *still-needed* return rather than
a constant target — the standard DT inference recipe.

``reset`` clears all rolling state so the agent is safe to reuse across
episodes.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..learning.dataset import OBS_DIM, UNK_CONFIG_ID
from ..learning.dt_model import DecisionTransformer, DTModelConfig
from ..learning.featurizer import NUM_ACTIONS
from .base_agent import BaseAgent
from .bc_agent import _featurize_live  # offline/live featurizer parity


# Default conditioning return when the caller doesn't override it. The
# reward signal is (mana_delta / 100) + 0.1·new_personal_best per step;
# strong human episodes accumulate ~10–15 over a full game (peak RTG seen
# in human_v4 was ~13). Conditioning at the high end of the seen range
# nudges the policy toward the better trajectories without going so far
# above support that the model has nothing to extrapolate from.
DEFAULT_TARGET_RETURN: float = 15.0


class DecisionTransformerAgent(BaseAgent):
    """Loads a DT checkpoint and acts step-by-step under a return target."""

    def __init__(
        self,
        checkpoint_path: str | Path,
        *,
        name: str = "dt",
        device: str | None = None,
        target_return: float = DEFAULT_TARGET_RETURN,
    ):
        super().__init__(name=name)
        # Lazy torch import keeps the runner from hard-requiring torch on
        # non-DT agents. Mirrors the BC agent.
        import torch

        self._torch = torch
        self._device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )

        ckpt = torch.load(checkpoint_path, map_location=self._device,
                          weights_only=False)
        summary = ckpt.get("summary", {})
        if summary.get("obs_dim", OBS_DIM) != OBS_DIM:
            raise ValueError(
                f"Checkpoint obs_dim={summary.get('obs_dim')} doesn't match "
                f"current featurizer OBS_DIM={OBS_DIM} — retrain after a "
                f"feature-layout change."
            )
        if summary.get("num_actions", NUM_ACTIONS) != NUM_ACTIONS:
            raise ValueError(
                f"Checkpoint num_actions={summary.get('num_actions')} doesn't "
                f"match current NUM_ACTIONS={NUM_ACTIONS}."
            )
        if summary.get("model_kind") not in (None, "decision_transformer"):
            raise ValueError(
                f"Checkpoint model_kind={summary.get('model_kind')!r} is not a "
                f"Decision Transformer — load it with the correct agent class."
            )

        cfg = DTModelConfig(**ckpt["config"])
        self._model = DecisionTransformer(cfg).to(self._device)
        self._model.load_state_dict(ckpt["state_dict"])
        self._model.eval()

        self.summary = summary
        self.target_return = float(target_return)
        self.K: int = cfg.context_length
        self._max_episode_length: int = cfg.max_episode_length
        self._config_vocab: dict[str, int] = dict(ckpt.get("config_vocab", {}) or {})

        # Per-episode rolling buffers. ``reset()`` re-initialises them.
        self._states: list[np.ndarray] = []
        self._actions: list[int] = []
        self._rtgs: list[float] = []
        self._timesteps: list[int] = []
        self._t: int = 0
        self._remaining_return: float = self.target_return

    def reset(self) -> None:
        self._states = []
        self._actions = []
        self._rtgs = []
        self._timesteps = []
        self._t = 0
        self._remaining_return = self.target_return

    def act(self, observation: dict, info: dict | None = None) -> int:
        torch = self._torch
        info = info or {}
        raw = info.get("raw_state") or {}

        # 1. Append the new step's state, RTG and timestep. The action
        #    slot gets a placeholder (0) — causal masking guarantees the
        #    s_t token can't attend to a_t in the same step, so the
        #    placeholder doesn't influence this step's prediction. We
        #    overwrite it with the chosen action below, so the *next*
        #    step's window contains the true a_t.
        feats = _featurize_live(raw)
        self._states.append(feats)
        self._actions.append(0)
        self._rtgs.append(self._remaining_return)
        self._timesteps.append(min(self._t, self._max_episode_length - 1))

        # 2. Build a left-padded window of the last K entries.
        K = self.K
        L = len(self._states)
        real_len = min(L, K)
        pad = K - real_len

        states_w = np.zeros((K, OBS_DIM), dtype=np.float32)
        actions_w = np.zeros(K, dtype=np.int64)
        rtgs_w = np.zeros(K, dtype=np.float32)
        ts_w = np.zeros(K, dtype=np.int64)
        attn_w = np.zeros(K, dtype=np.float32)

        states_w[pad:] = np.stack(self._states[-real_len:])
        actions_w[pad:] = np.array(self._actions[-real_len:], dtype=np.int64)
        rtgs_w[pad:] = np.array(self._rtgs[-real_len:], dtype=np.float32)
        ts_w[pad:] = np.array(self._timesteps[-real_len:], dtype=np.int64)
        attn_w[pad:] = 1.0

        # 3. Action mask — prefer the observation's mask (current as of
        #    this turn); fall back to reconstructing from valid_actions
        #    when the obs payload is absent (older logs / replays).
        mask_arr = observation.get("action_mask")
        if mask_arr is None:
            mask_arr = np.zeros(NUM_ACTIONS, dtype=np.float32)
            for a in raw.get("valid_actions", []) or []:
                ai = int(a)
                if 0 <= ai < NUM_ACTIONS:
                    mask_arr[ai] = 1.0
        mask = np.asarray(mask_arr, dtype=np.float32)

        cfg_key = str(raw.get("config_key", "") or "")
        cfg_id = self._config_vocab.get(cfg_key, UNK_CONFIG_ID)

        # 4. Forward pass; pull logits at the last s-token position and
        #    apply the live mask before argmax.
        with torch.no_grad():
            s = torch.from_numpy(states_w).unsqueeze(0).to(self._device)
            a = torch.from_numpy(actions_w).unsqueeze(0).to(self._device)
            r = torch.from_numpy(rtgs_w).unsqueeze(0).to(self._device)
            t = torch.from_numpy(ts_w).unsqueeze(0).to(self._device)
            m_pad = torch.from_numpy(attn_w).unsqueeze(0).to(self._device)
            c = torch.tensor([cfg_id], dtype=torch.long, device=self._device)
            logits = self._model(s, a, r, t, m_pad, c)            # (1, K, NUM_ACTIONS)
            last_logits = logits[0, -1]                           # (NUM_ACTIONS,)
            mask_t = torch.from_numpy(mask).to(self._device)
            masked = last_logits + (1.0 - mask_t) * -1e9
            action = int(masked.argmax().item())

        # 5. Replace the placeholder so the next window holds the real a_t.
        self._actions[-1] = action
        self._t += 1

        # Defensive fallback: if the live mask is empty (no valid action),
        # the runner is about to terminate the episode anyway. DRAW (0)
        # is universally legal at game start, so it's the safest default.
        if mask.sum() == 0:
            return 0
        return action

    def on_step_result(
        self, action: int, reward: float, terminated: bool, info: dict
    ) -> None:
        # Decrement the remaining target by the realised reward so the
        # next step's RTG conditioning reflects what's *still* needed.
        # Standard DT inference recipe (Chen et al., 2021, §3.2).
        self._remaining_return -= float(reward)
