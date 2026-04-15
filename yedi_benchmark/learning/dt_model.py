"""Decision Transformer over Yedi (R, s, a) sequences.

Architecture — standard DT (Chen et al., 2021):

    tokens = [R_0, s_0, a_0, R_1, s_1, a_1, ..., R_{K-1}, s_{K-1}, a_{K-1}]

Three separate linear embeddings project return-to-go, state and the
one-hot action into ``d_model``. A shared timestep embedding is added
to all three tokens of the same step. A standard GPT-style causal
transformer stack (pre-LN) runs over the length-``3K`` sequence; the
output at each ``s_t`` token position projects to a 37-way action
logit. Loss is soft cross-entropy over the expert's action-equivalence
set, averaged across non-pad positions.

Why pre-LN + dropout 0.2: our dataset is small (≈2k rows); post-LN
transformers are notoriously unstable on small batches, and light
dropout on the embedding/attention/MLP output is the standard
regularization in this regime.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import torch
import torch.nn as nn
import torch.nn.functional as F

from .dataset import OBS_DIM
from .featurizer import NUM_ACTIONS


@dataclass
class DTModelConfig:
    obs_dim: int = OBS_DIM
    num_actions: int = NUM_ACTIONS
    context_length: int = 20        # K
    d_model: int = 128
    n_heads: int = 4
    n_layers: int = 2
    dropout: float = 0.2
    # Episode step index can be large; we clamp to this range so a new
    # step outside the range still embeds (saturation on the last
    # learned position). Most episodes cap at ~100 steps anyway.
    max_episode_length: int = 1024
    # 0 disables the config embedding entirely; matches BCModelConfig.
    config_vocab_size: int = 0
    config_emb_dim: int = 8


class _CausalBlock(nn.Module):
    """Pre-LN transformer block with multi-head self-attention + MLP."""

    def __init__(self, d_model: int, n_heads: int, dropout: float):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = nn.MultiheadAttention(
            d_model, n_heads, dropout=dropout, batch_first=True,
        )
        self.ln2 = nn.LayerNorm(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, 4 * d_model),
            nn.GELU(),
            nn.Linear(4 * d_model, d_model),
            nn.Dropout(dropout),
        )

    def forward(
        self,
        x: torch.Tensor,
        *,
        attn_mask: torch.Tensor,
    ) -> torch.Tensor:
        h = self.ln1(x)
        attended, _ = self.attn(
            h, h, h,
            attn_mask=attn_mask,
            need_weights=False,
        )
        x = x + attended
        x = x + self.mlp(self.ln2(x))
        return x


class DecisionTransformer(nn.Module):
    def __init__(self, config: DTModelConfig | None = None):
        super().__init__()
        cfg = config or DTModelConfig()
        self.config = cfg

        # Raw state features span orders of magnitude (mana_max in the
        # thousands alongside 0/1 hashes). BC uses BatchNorm because it
        # only ever sees real rows; DT batches contain pad states (all
        # zeros), which would skew BN's running stats and inject
        # extreme values at eval time. LayerNorm is per-token and
        # unaffected by pad contamination.
        self.state_norm = nn.LayerNorm(cfg.obs_dim)
        self.state_proj = nn.Linear(cfg.obs_dim, cfg.d_model)
        self.rtg_proj = nn.Linear(1, cfg.d_model)
        self.action_emb = nn.Embedding(cfg.num_actions, cfg.d_model)
        self.timestep_emb = nn.Embedding(cfg.max_episode_length, cfg.d_model)
        self.emb_ln = nn.LayerNorm(cfg.d_model)
        self.emb_dropout = nn.Dropout(cfg.dropout)

        self.config_embed = (
            nn.Embedding(cfg.config_vocab_size, cfg.config_emb_dim)
            if cfg.config_vocab_size > 0 and cfg.config_emb_dim > 0
            else None
        )
        if self.config_embed is not None:
            self.config_proj = nn.Linear(cfg.config_emb_dim, cfg.d_model)

        self.blocks = nn.ModuleList([
            _CausalBlock(cfg.d_model, cfg.n_heads, cfg.dropout)
            for _ in range(cfg.n_layers)
        ])
        self.ln_f = nn.LayerNorm(cfg.d_model)
        self.action_head = nn.Linear(cfg.d_model, cfg.num_actions)

        # Cache a [3K, 3K] causal mask — construction is trivial but
        # moving to the right device + dtype every forward is wasteful.
        mask = torch.triu(torch.ones(3 * cfg.context_length, 3 * cfg.context_length), diagonal=1).bool()
        self.register_buffer("_causal_mask", mask, persistent=False)

    def forward(
        self,
        states: torch.Tensor,        # (B, K, OBS_DIM)
        actions: torch.Tensor,       # (B, K) int64
        rewards_to_go: torch.Tensor, # (B, K) float32
        timesteps: torch.Tensor,     # (B, K) int64
        attn_mask: torch.Tensor,     # (B, K) 0/1 float — 1 real, 0 pad
        config_id: torch.Tensor | None = None,  # (B,) int64
    ) -> torch.Tensor:
        """Return action logits at the s-token positions: (B, K, num_actions).

        Positions where ``attn_mask[b, t] == 0`` carry meaningless
        logits — the caller must mask them before computing loss or
        picking an action.
        """
        B, K, _ = states.shape
        cfg = self.config

        # Clamp timesteps to the learned range. Values beyond
        # max_episode_length saturate to the final position embedding
        # rather than raising, which matters mid-episode when the
        # runtime context grows past training-time episodes.
        timesteps = timesteps.clamp(max=cfg.max_episode_length - 1)

        # LayerNorm is per-token, so no need to flatten batch×time first.
        s_tok = self.state_proj(self.state_norm(states))
        r_tok = self.rtg_proj(rewards_to_go.unsqueeze(-1))
        a_tok = self.action_emb(actions)

        time_emb = self.timestep_emb(timesteps)
        s_tok = s_tok + time_emb
        r_tok = r_tok + time_emb
        a_tok = a_tok + time_emb

        if self.config_embed is not None:
            if config_id is None:
                raise ValueError("model built with config_vocab_size>0 requires config_id")
            cfg_tok = self.config_proj(self.config_embed(config_id))  # (B, d_model)
            # Broadcast onto every token (acts like a per-sequence bias).
            cfg_tok = cfg_tok.unsqueeze(1).expand(B, K, cfg.d_model)
            r_tok = r_tok + cfg_tok
            s_tok = s_tok + cfg_tok
            a_tok = a_tok + cfg_tok

        # Interleave along the time axis: [R_0, s_0, a_0, R_1, ...].
        # stacking then reshape is equivalent to a manual interleave
        # but avoids a Python loop.
        stacked = torch.stack([r_tok, s_tok, a_tok], dim=2)  # (B, K, 3, d)
        seq = stacked.reshape(B, 3 * K, cfg.d_model)
        seq = self.emb_dropout(self.emb_ln(seq))

        # Causal mask is upper-triangular of True — attend only to earlier.
        # We deliberately skip key_padding_mask: combining it with a
        # causal mask leaves pad queries at the head of a sequence with
        # no attendable keys, producing NaN from softmax(all -inf). Pad
        # state inputs are all-zero, their embeddings are bounded, and
        # the loss/metric pad-masks their outputs downstream — so their
        # contribution is negligible and numerically safe.
        causal = self._causal_mask[: 3 * K, : 3 * K]

        for block in self.blocks:
            seq = block(seq, attn_mask=causal)
        seq = self.ln_f(seq)

        # Take the s-token positions — at offset 1 within each step's
        # triple. These are the positions at which the model should
        # have emitted a_t.
        s_positions = seq[:, 1::3, :]                    # (B, K, d_model)
        return self.action_head(s_positions)             # (B, K, num_actions)


def dt_soft_cross_entropy(
    logits: torch.Tensor,       # (B, K, num_actions)
    equiv_sets: torch.Tensor,   # (B, K, num_actions) 0/1
    attn_mask: torch.Tensor,    # (B, K) 0/1
) -> torch.Tensor:
    """Soft CE over action-equivalence sets, averaged over valid positions.

    Mirrors ``bc_soft_cross_entropy`` but reduces over real positions
    only. Pad positions contribute zero to both numerator and
    denominator so short episodes aren't under-weighted.
    """
    log_probs = F.log_softmax(logits, dim=-1)
    masked = log_probs.masked_fill(equiv_sets < 0.5, float("-inf"))
    log_mass = torch.logsumexp(masked, dim=-1)            # (B, K)

    valid = attn_mask > 0.5
    if not valid.any():
        return torch.zeros((), device=logits.device, dtype=logits.dtype)
    loss = -log_mass[valid].mean()
    return loss


def dt_accuracy(
    logits: torch.Tensor,       # (B, K, num_actions)
    equiv_sets: torch.Tensor,   # (B, K, num_actions)
    attn_mask: torch.Tensor,    # (B, K)
) -> tuple[int, int]:
    """Count (correct, total) over real positions. Argmax in the
    equivalence set is credited as correct (matches BC's metric)."""
    preds = logits.argmax(dim=-1)
    # Gather the equivalence-mask entry at each predicted index.
    B, K = preds.shape
    flat_pred = preds.reshape(-1)
    flat_equiv = equiv_sets.reshape(B * K, -1)
    flat_correct = flat_equiv[torch.arange(B * K, device=preds.device), flat_pred]
    correct = flat_correct.reshape(B, K)
    valid = attn_mask > 0.5
    return int(correct[valid].sum().item()), int(valid.sum().item())
