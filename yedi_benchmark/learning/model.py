"""BC policy — MLP over the flat Yedi feature vector.

Design notes
------------
* The action space is tiny (37 discrete), so an MLP over the featurizer's
  529-d vector is enough for v1. Conv over the 7-slot axis is a natural
  upgrade but not needed to beat random/greedy.
* **Masking is applied at inference, not training**. The bridge's
  ``valid_actions`` is sometimes stale in logs (notably human frames),
  which would corrupt masked cross-entropy with -1e9 logits on the
  expert's label. Instead we train pure cross-entropy over all 37
  classes — the expert only picks legal actions, so the model learns
  legal-action distributions naturally — and apply the action mask in
  ``BehaviorCloningAgent.act`` using the real-time mask from the live
  env.
* Checkpoint metadata stores ``OBS_DIM`` and ``NUM_ACTIONS`` so a future
  featurizer change surfaces as an explicit load-time error instead of
  silent corruption.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

from .dataset import OBS_DIM
from .featurizer import NUM_ACTIONS


LOGIT_MASK_NEG_INF: float = -1e9
"""Additive term for masked-out logits at inference time. ``-inf`` would
be correct but can destabilize downstream softmax/entropy calculations;
a large negative constant produces ~zero probability while staying
numerically well-behaved."""


@dataclass
class BCModelConfig:
    obs_dim: int = OBS_DIM
    num_actions: int = NUM_ACTIONS
    hidden_sizes: tuple[int, ...] = (256, 256)
    dropout: float = 0.1
    # 0 disables the config embedding path entirely (single-config runs
    # or checkpoints predating the embedding). The trainer sets this to
    # ``len(vocab) + 1`` — the +1 being the reserved UNK slot at id 0.
    config_vocab_size: int = 0
    config_emb_dim: int = 8


class BCPolicy(nn.Module):
    def __init__(self, config: BCModelConfig | None = None):
        super().__init__()
        cfg = config or BCModelConfig()
        self.config = cfg

        # The raw features are wildly mis-scaled (``mana_max`` reaches
        # ~1300 while ``beat_phase`` is in [0,1] and slot word-hash
        # one-hots are 0/1). Without input normalization, the first
        # Linear sees pre-activations in the thousands and loss
        # explodes. BatchNorm1d tracks running stats so inference
        # picks up the same mean/var without a separate calibration
        # pass.
        self.bn = nn.BatchNorm1d(cfg.obs_dim)
        # The config embedding deliberately bypasses BN: BN would
        # destandardize each embedding across a batch (different configs
        # → different running means) and fight the embedding's job of
        # holding a stable per-config vector. Concat it after BN instead.
        self.config_embed = (
            nn.Embedding(cfg.config_vocab_size, cfg.config_emb_dim)
            if cfg.config_vocab_size > 0 and cfg.config_emb_dim > 0
            else None
        )
        mlp_in = cfg.obs_dim + (cfg.config_emb_dim if self.config_embed is not None else 0)

        layers: list[nn.Module] = []
        prev = mlp_in
        for h in cfg.hidden_sizes:
            layers += [nn.Linear(prev, h), nn.ReLU(), nn.Dropout(cfg.dropout)]
            prev = h
        layers.append(nn.Linear(prev, cfg.num_actions))
        self.mlp = nn.Sequential(*layers)

    def forward(
        self,
        features: torch.Tensor,
        mask: torch.Tensor | None = None,
        config_id: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Return unmasked logits (train) or masked logits (inference).

        ``config_id`` is required iff the model was built with a non-zero
        ``config_vocab_size``; otherwise it's silently ignored so legacy
        checkpoints keep working through the same forward signature.
        """
        x = self.bn(features)
        if self.config_embed is not None:
            if config_id is None:
                raise ValueError("model built with config_vocab_size>0 requires config_id")
            x = torch.cat([x, self.config_embed(config_id)], dim=-1)
        logits = self.mlp(x)
        if mask is not None:
            logits = logits + (1.0 - mask) * LOGIT_MASK_NEG_INF
        return logits


def bc_cross_entropy(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Plain softmax cross-entropy over all 37 action classes.

    Expert demonstrations only contain legal actions, so there's no
    mass to clean up at train time — the distribution over illegal
    actions naturally goes to zero as training progresses.
    """
    return F.cross_entropy(logits, target)


def bc_soft_cross_entropy(
    logits: torch.Tensor,
    target_set: torch.Tensor,
) -> torch.Tensor:
    """Cross-entropy over an equivalence class of expert actions.

    Several Yedi moves are semantically identical from the same state —
    e.g. parking a new card in empty slot 3 vs empty slot 5 when both
    are empty and no merge is possible. Penalizing the model for picking
    slot 5 when the human happened to pick slot 3 is label noise. This
    loss instead maximizes the *total* probability mass the model puts
    on any action in the equivalence set, so any of them is treated as
    fully correct.

    ``target_set`` is a (B, NUM_ACTIONS) {0,1} mask with ≥1 ones per row.
    Reduces to plain cross-entropy when the set is a singleton.
    """
    log_probs = F.log_softmax(logits, dim=-1)
    # log(sum_i T_i · p_i) = logsumexp over the active indices.
    masked = log_probs.masked_fill(target_set < 0.5, float("-inf"))
    log_mass = torch.logsumexp(masked, dim=-1)
    return -log_mass.mean()
