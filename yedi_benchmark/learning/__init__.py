"""Yedi learning pipeline — featurize replay logs and export BC datasets.

The replay logger writes one ``events.jsonl`` per episode, regardless of
which agent produced it (human, greedy, random, LLM). This package turns
those JSONL files into fixed-shape numeric rows suitable for behavior
cloning or offline RL:

  * ``featurizer``   — pure functions that convert a single step record
                       into a feature dict, with deterministic hash-bucket
                       word encoding.
  * ``export_dataset`` — CLI that walks a logs directory and writes a
                         single Parquet file with an ``agent_source``
                         column so trainers can mix or filter by provider.
"""

from .featurizer import (
    DIMENSIONS,
    DIMENSIONS_DIM,
    SLOT_FEATURE_DIM,
    NUM_SLOTS,
    WORD_HASH_DIM,
    OBS_SCALAR_FIELDS,
    classify_agent_source,
    featurize_episode,
    featurize_step,
    hash_word,
    parse_active_dimensions,
)

__all__ = [
    "DIMENSIONS",
    "DIMENSIONS_DIM",
    "SLOT_FEATURE_DIM",
    "NUM_SLOTS",
    "WORD_HASH_DIM",
    "OBS_SCALAR_FIELDS",
    "classify_agent_source",
    "featurize_episode",
    "featurize_step",
    "hash_word",
    "parse_active_dimensions",
]
