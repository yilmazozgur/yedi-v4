"""
LLM Agent — provider-agnostic agent that plays Yedi via metadata and/or screenshots.

The agent talks to the LLM through an injected `LLMProvider` (LiteLLM-backed
in production), so the same class works for Anthropic, OpenAI, Google, or any
other backend the provider layer can dispatch to.

Supports four evaluation modes (per AgentMode in registries.models):
  - metadata + stateless  (Mode A): one API call per step, text-only, no history
  - metadata + conversational (Mode B): rolling conversation within an episode, text-only
  - screenshot + stateless  (Mode A): one API call per step, screenshot + text
  - screenshot + conversational (Mode B): rolling conversation, screenshot + text

The system prompt is assembled from a `Prompt` object (registry-driven) when
provided, otherwise from the legacy module-level CORE_RULES + DIMENSION_RULES
constants. The legacy constants stay in this file because the prompt registry
seeds the default "v1" prompt by importing them.
"""

import base64
import io
import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import numpy as np
from .base_agent import BaseAgent

if TYPE_CHECKING:
    from ..providers.base import LLMProvider
    from ..registries.models import Prompt

# Load .env from the benchmark directory
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

logger = logging.getLogger("llm_agent")

# Maximum conversation turns to keep (per direction) to bound context size.
# Each "turn" = 1 user + 1 assistant message.  100 steps ≈ 60-80K tokens.
MAX_HISTORY_TURNS = 80


# =====================================================================
# Prompt building
# =====================================================================

CORE_RULES = """\
You are playing YEDI, a brain-training card game. You buy cards, merge them
into HIGH-VALUE cards, then SELL the merged cards to convert their accumulated
card_mana back into your total mana bank. Your SCORE is the PEAK total mana
("Best" / max mana) you ever reached. Maximise it.

The game has TWO scarce resources you must respect at all times:
  - LIMITED MANA: your bank starts low (200). Every draw costs mana up front.
    Bad merges destroy mana. You only profit when sells return more than you spent.
  - LIMITED MOVES: every action — draw, move, merge, sell, wait — consumes one
    of a fixed number of moves per game (typically 100). When the moves run out
    the game ends. Wasted moves are wasted score. NEVER move just to "see what
    happens"; every action must have a concrete reason.

============ THE BOARD ============

  [ NEW ]    [ 1 ]  [ 2 ]  [ 3 ]  [ 4 ]  [ 5 ]    (sell action)
   draw         <----- 5 build slots ----->          destroys
   target                                            a card

  - "new"  : where freshly drawn cards land. Must be cleared before drawing again.
  - 1..5   : your build slots — cards grow here through merges.
  - "sell" : NOT a slot you place into. The "sell <slot>" actions destroy the
             card in that slot and ADD its current card_mana to your total mana.

============ ACTION INDEX (the integer you must output) ============

You select a move by outputting a single integer 0..37. The mapping is FIXED:

   0          DRAW a new card into "new"
   1..30      MOVE src → dst (merge if dst occupied, place if dst empty)
                Source slots: 0=new, 1..5=build slots
                Destination slots: 1..5 (you cannot move INTO new)
                Formula:  action = 1 + (src_index * 5) + (dst_index - 1)
                Examples: new→1 = 1     new→2 = 2     new→5 = 5
                          1→2  = 7      1→3  = 8      1→5  = 10
                          3→4  = 19     5→1  = 26     5→4  = 29
   31..36     SELL the card in the given source slot
                31=sell new, 32=sell slot1, 33=slot2, 34=slot3, 35=slot4, 36=slot5
   37         WAIT (no-op for one step)

You will see a "Valid actions:" list in each turn's user message — that list
already enumerates the legal action numbers for your current state, with a
short text label. ALWAYS pick from that list. If you compute a number that
isn't on the list it will be rejected and a fallback will run instead.

============ MANA ECONOMY ============

You start with ~200 total mana. Mana drains slowly each step. Your score = the
highest total mana you ever reached during the game.

DRAW (action 0):
  - Costs ~10 mana × (number of active dimensions). Single-dim ≈ 10, 4-dim ≈ 40.
  - Spawns a card in "new" with card_mana = round(cost × 0.9), e.g. 9 for a
    1-dim card, 36 for a 4-dim card.
  - INVALID if "new" is occupied. Always clear "new" before drawing.
  - Selling a freshly drawn card returns LESS than the draw cost (~10% loss).
    Drawing is only profitable if you turn the card into something larger first.

SELL (actions 31-36, one per slot):
  - Removes the card from its slot and ADDS its current card_mana to your total mana.
  - Selling is the ONLY way card_mana becomes score. A card sitting in a slot is
    POTENTIAL score, not realised score. You MUST sell to actually score.
  - Selling is meant for cards you have BUILT UP through good merges.

WAIT (action 37): no-op for one step. Burns a move with no benefit. Almost never useful.

============ NEUTRAL CARDS — THE KEY CONCEPT ============

Each dimension has a special "NEUTRAL CARD" — the card that represents the
dimension's resolved/identity state:

  - Math/Add        → the card with value 0       (neutral = "0")
  - Math/Multiply   → the card with value 1       (neutral = "×1")
  - Math/GCD        → the card with value 1       (neutral = "1")
  - Visual/Add      → White                       (R+G+B all on)
  - Visual/Subtract → Black                       (no ink)
  - Visual/Gray     → White
  - Shape/*         → the BLANK shape card        (Shape=8 or Shape=16)
  - Word/* etc.     → see each dimension's section below

A neutral card by itself is just a card. The MAGIC happens when you merge a
neutral card with ANOTHER neutral card — that scores the maximum 2.5x multiplier
in that dimension. This is the highest possible single-merge gain in the game.

NEUTRAL CARDS ARE RARE. They almost never spawn from a vanilla draw — they
come either from a "super" draw (low probability) or, much more reliably, from
a GREAT merge that RESOLVES TO neutral (e.g. math:add 3+(-3)=0, visual:add
Yellow+Cyan=White). DO NOT sit and wait for a neutral to be drawn. The
intended path is: draw ordinary cards → merge them into neutral state → THEN
pair neutrals together for the ×2.5 jackpot.

GOAL: build up to neutral cards via ×2.0 "resolve-to-neutral" merges, then
chain neutral+neutral merges for ×2.5 each. Each link in the chain multiplies
card_mana by 2.5×, so the value grows EXPONENTIALLY.

============ MERGES — HOW CARDS GROW ============

Moving a card onto an OCCUPIED slot MERGES them. The two cards fuse into one,
which stays in the target slot. The target's card_mana is multiplied by a
coefficient based on how good the merge is in EACH active dimension:

   2.5x  PERFECT  (both cards are the dimension's NEUTRAL card)
   2.0x  GREAT    (the merge RESOLVES TO neutral — e.g. math:add 3+(-3)=0,
                   visual:add Yellow+Cyan=White, shape Triangle-up + Triangle-down)
   1.5x  GOOD     (the merge moves toward neutral — e.g. Red+Green=Yellow)
   ~1.1x OK       (small positive)
   1.0x  NEUTRAL  (no change to mana)
   0.9x  BAD      (DEGRADES card_mana — you LOSE mana!)
   0.7x  TERRIBLE

============ MULTI-DIMENSION MERGES ARE EXPONENTIAL ============

When MULTIPLE dimensions are active (e.g. math + visual + memory), each
dimension's multiplier is applied to card_mana SEQUENTIALLY. The same merge
hits the card with N multipliers stacked on top of each other:

   1 dim, perfect:        9 × 2.5             = 22
   2 dims, both perfect:  9 × 2.5 × 2.5       = 56
   3 dims, all great:     9 × 2.0 × 2.0 × 2.0 = 72
   3 dims, all perfect:   9 × 2.5 × 2.5 × 2.5 = 141
   4 dims, all perfect:   36 × 2.5 × 2.5 × 2.5 × 2.5 = 1406  ← jackpot

This is why a merge that is great in EVERY dimension is exponentially better
than one that is great in just one. Conversely:

   3 dims, 2 great 1 bad: 9 × 2.0 × 2.0 × 0.9 = 32
   3 dims, all bad:       9 × 0.9 × 0.9 × 0.9 =  7  (LOST 2 mana from this card!)

A merge that is BAD or NEUTRAL in ANY dimension is rarely worth it — one bad
factor washes out gains in the other dims. Aim for GOOD-or-better in EVERY
active dim. The BEST move is the one that scores high in all dimensions
simultaneously.

DECISION RULE — evaluate each candidate merge ONE DIMENSION AT A TIME, do not
average them in your head:

  for each candidate merge (this new card → some build slot):
      for each ACTIVE dimension:
          look up the multiplier for THIS specific pair under that dim's rules
      if the MIN multiplier across all dims is < 1.0  → this merge is a LOSS, skip
      if the MIN multiplier is >= 1.5                 → this merge is a KEEPER
      otherwise it is mediocre — only do it if no better option exists

Pick the candidate with the HIGHEST minimum (not the highest average) — the
worst-dimension factor is what bounds the actual gain. A merge that is 2.5×
in math but 0.9× in colour is a 0.9-bounded merge, not a "mostly great" one.

============ HARD LIMIT: 3 MERGES PER CARD ============

Each card refuses further merges after 3 merges. After that, the card is DONE —
no further growth. Holding a 3-merge card just wastes a slot while mana drains.

RULE: as soon as a card hits 3 merges, SELL IT next turn. Free the slot.

============ THE CORE LOOP ============

  1. DRAW    → spawns in "new"
  2. PLACE   → move into the BEST matching build slot OR an empty build slot
  3. BUILD   → keep 4-5 cards growing in parallel across slots 1-5; chain to neutral
  4. SELL    → when a slot card hits 3 merges (or stops merging well), sell it
  5. REPEAT

A card that survives 3 perfect (2.5x) merges goes from 9 → 23 → 56 → 141 mana.
Selling adds +141 to your total. Doing this 3-4 times during a game can push
max mana well above 500. Bad play stays around the starting 200.

============ CRITICAL: USE MULTIPLE SLOTS IN PARALLEL ============

THE #1 FAILURE MODE is dumping every new card into the SAME slot. This kills
your score:

  - Slot 1 hits 3 merges quickly and stops growing.
  - You're forced to push BAD merges into slot 1 (no other choice), DEGRADING it.
  - Slots 2-5 stay empty all game. You waste 80% of your strategy space.
  - Final result: max mana barely changes from the starting 200.

CORRECT play: spread cards across all 5 build slots. The strategic reason is
that NEUTRAL+NEUTRAL chains require you to have neutral cards LYING AROUND in
multiple slots at the same time — if you only ever build one slot, you can
never pair two neutrals.

When the "new" card appears, look at EVERY build slot and ask:

  - "Which build slot, paired with this new card, gives the highest multiplier
     across ALL active dimensions?"
  - If at least one yields ≥1.5x in every active dim → merge with the BEST one.
  - If best available merge is ≤1.0x in some dim → place the new card into an
     EMPTY build slot instead (preserves the card_mana for future merges).
  - If all 5 build slots are full AND no merge ≥1.5x is available →
     SELL the new card (action sell-new) rather than ruin a built slot.
  - If a build slot has hit 3 merges → SELL it next turn.

============ PRESERVE POTENTIAL — DOING NOTHING IS A REAL OPTION ============

A common mistake is feeling that every turn must "make progress" by merging.
That is wrong. Forcing a bad merge actively DESTROYS card_mana (×0.9 or ×0.7),
whereas placing the new card into an empty slot keeps its full card_mana intact
and gives you another candidate for a future ×2.0 or ×2.5 merge.

The hierarchy of options when the "new" slot is occupied, BEST to WORST:

   1. MERGE INTO A SLOT WHERE EVERY ACTIVE DIM SCORES ≥1.5×    (compounding gain)
   2. PLACE INTO AN EMPTY BUILD SLOT                            (preserves mana, keeps options)
   3. SELL THE NEW CARD                                         (recovers ~90% of draw cost)
   4. FORCE A BAD MERGE INTO A BUILT SLOT                       (NEVER do this)

Option 4 looks like "doing something" but it both wastes the new card AND
damages a slot you spent earlier turns building up. It is strictly worse than
selling the new card, even though selling feels like "wasting" it. Selling
recovers most of the mana; a bad merge recovers nothing and degrades a slot.

============ TURN-BY-TURN DECISION CHECKLIST ============

Before deciding anything, READ THE SLOT SUMMARY at the top of the user message.
Every turn the message lists each slot with its current attributes (Num, Color,
Shape, …), card_mana, and merge count. You CANNOT make a good move without
that information — never decide from memory of an earlier turn, the state has
changed. Also read the "Valid actions:" list to confirm your chosen action ID
is legal RIGHT NOW.

Then, in order:

  1. Is any build slot at 3 merges? → SELL it (action 32-36).
  2. Is the "new" slot occupied?
       a. For each occupied build slot N, mentally compute the merge multiplier
          across ALL active dimensions (read the dimension rules below). Use
          the per-dim DECISION RULE — pick the candidate with the highest
          MINIMUM multiplier across dims.
       b. If any merge ≥ 1.5x in every dim → MOVE new → that slot.
       c. Else if there is an empty build slot → MOVE new → empty slot
          (preserves card_mana, lets you merge later).
       d. Else → SELL new (action 31), don't pollute a built slot.
  3. Is "new" empty AND no slot needs selling? → DRAW (action 0).

Every action above costs ONE move from your fixed budget. Skipping step 1
(failing to sell a 3-merge card) wastes mana drain. Defaulting to draw without
a placement plan wastes both mana and a move. Think before each action.

============ COMMON MISTAKES TO AVOID ============

  1. Single-slot fixation: always merging into slot 1. You'll cap out fast and
     start degrading the slot with bad merges. Spread across slots 2-5.
  2. Forgetting to sell: card_mana is potential, not score. CARDS MUST BE SOLD
     to convert into mana. If you never sell, your score never grows.
  3. Bad-merge spam: 0.9x and 0.7x DEGRADE card_mana. Avoid them — place into
     an empty slot or sell instead.
  4. Drawing without a plan: every draw costs mana AND a move. If you can't
     place or sell efficiently afterwards, you're losing mana net.
  5. Blocking yourself: leaving "new" occupied PREVENTS drawing. Always clear
     "new" before issuing another draw.
  6. Ignoring multi-dim trade-offs: a merge can be perfect in one dim and
     terrible in another. Multipliers compound — one bad dim ruins the merge.
  7. Wasting moves: WAIT, redundant moves between empty slots, or moving a
     card just to move it all burn the move budget. Only act with intent.
  8. OSCILLATING BETWEEN BUILD SLOTS: moving a card from one build slot
     (1..5) to another WITHOUT triggering a merge is strictly worse than
     doing nothing. Every such unproductive slot→slot move:
       - costs a move from your fixed move budget,
       - wastes the drain tick on the total-mana bank, AND
       - DEDUCTS A FLAT 5 MANA PENALTY from your total mana bank directly.
         Yes — your bank drops by 5 the moment you issue a board-to-board
         move that does not reduce the occupied-slot count. This is real
         score you are losing, it is visible in the next state's mana
         value, and it permanently lowers the ceiling for your max_mana.
     A "move slot→slot" action (action IDs 6..30) only makes sense if the
     destination is OCCUPIED and the pair produces a merge that is ≥1.5x
     in every active dimension. If the destination is empty, or the
     resulting merge would be neutral/bad, do NOT issue the move — you
     will pay 5 mana for nothing. Prefer: place NEW into an empty slot,
     sell a capped slot, or draw.\
"""

# Per-dimension merge rules, keyed by (dimension_field, mode_value).
# Each rule includes: mechanics, exact scoring (verified against C# source),
# worked examples, and strategy guidance.
DIMENSION_RULES = {
    # =================================================================
    # MATH (number)
    # =================================================================
    ("number", "add"): """\
==== MATH — ADD MODE ====
Each card has an integer value shown in metadata as "Num=N" (e.g. -5, -2, 0, 3, 7).
A merge ADDS the new card's value to the slot's value: result = slot_value + new_value.

NEUTRAL CARD = the "0" card. Merging neutral+neutral is the maximum 2.5x.

EXACT SCORING (multiplier applied to the slot's card_mana after the merge):
  slot=0  AND new=0       → 2.5x  PERFECT (both NEUTRAL)
  sum becomes 0           → 2.0x  GREAT   (resolves to neutral — e.g. 3+(-3), -2+2)
  |sum|=1                 → 1.1x
  |sum|=2                 → 1.0x  neutral mult
  |sum|=3                 → 0.9x  BAD
  |sum|=4                 → 0.8x  BAD
  |sum|≥5                 → 0.7x  TERRIBLE (capped here)

  SPECIAL: slot=0, new≠0  → 0.9x  BAD — wasted the neutral, slot becomes new value
  SPECIAL: slot≠0, new=0  → no multiplier; slot's value is RESET to 0 (use this
                            to "fix" a bad slot for free, then merge other things in)

WORKED EXAMPLES:
  Slot 1: Num=3, mana=9.   Merge new=Num=-3 → sum=0, ×2.0 → mana=18, value=0 (now neutral)
  Slot 1: Num=0, mana=18.  Merge new=Num=0  → both neutral, ×2.5 → mana=45, value=0
  Slot 1: Num=2, mana=9.   Merge new=Num=4  → sum=6,  ×0.7 → mana=6,  value=6 (LOST!)
  Slot 1: Num=-2, mana=15. Merge new=Num=0  → resets slot, mana unchanged at 15

STRATEGY:
  - Scan all build slots for (slot_value + new_value) closest to 0.
  - sum=0 (×2.0) is the workhorse merge — easy to find with mixed positive/negative cards.
  - HOLD value=0 (neutral) cards as merge targets for the 2.5x perfect; do NOT merge
    a non-zero card INTO a neutral slot (×0.9, wastes the neutral).
  - The strategic chain is: build several slots up to value=0 (neutral), then pair
    two neutral slots together for the ×2.5 jackpot.
  - Cards with extreme values (±5, ±7) are dangerous — pair them with their
    opposite, or sell them rather than ruin a slot.\
""",
    ("number", "multiply"): """\
==== MATH — MULTIPLY MODE ====
Each card has a fractional or integer value (e.g. 0.5, 1, 2, 3, 1/3, 1/4).
A merge MULTIPLIES: result = slot_value × new_value. Identity = 1.

EXACT SCORING:
  slot≈1  AND new≈1       → 2.5x  PERFECT
  product=1               → 2.0x  GREAT (reciprocals: 2×0.5, 3×1/3, 4×0.25)
  product close to 1      → 1.0-1.15x (smooth gaussian falloff)
  product far from 1      → 0.7x  (capped)

  SPECIAL: slot=1, new≠1  → 0.9x  BAD — wasted the 1 identity
  SPECIAL: slot≠1, new=1  → resets slot to 1, no multiplier (use to fix bad slots)

WORKED EXAMPLES:
  Slot 1: 2,   mana=9.  Merge new=0.5 → product=1, ×2.0  → mana=18, value=1
  Slot 1: 1,   mana=18. Merge new=1   → both 1,    ×2.5  → mana=45, value=1
  Slot 1: 3,   mana=9.  Merge new=4   → product=12, ×0.7 → mana=6,  value=12 (LOST!)
  Slot 1: 1/3, mana=9.  Merge new=3   → product=1, ×2.0  → mana=18, value=1

STRATEGY:
  - Look for RECIPROCAL pairs: 2×0.5, 3×1/3, 4×0.25, 5×0.2.
  - Hold value=1 cards as neutral targets.
  - Avoid merges that take you far from 1 in either direction.
  - Once a slot reaches 1, try to find another reciprocal pair to chain ×2.0 again.\
""",
    ("number", "gcd"): """\
==== MATH — GCD MODE ====
Each card has a positive integer (typically 1-12). A merge computes GCD of
(slot_value, new_value). Identity = 1.

EXACT SCORING:
  slot=1  AND new=1       → 2.5x  PERFECT
  GCD(slot,new) = 1       → 2.0x  GREAT, slot becomes 1 (coprime pair)
  GCD(slot,new) > 1       → 0.9x  BAD,  slot becomes the GCD value

  SPECIAL: slot=1, new≠1  → 0.9x  BAD — wasted the 1 identity
  SPECIAL: slot≠1, new=1  → resets slot to 1, no multiplier (use to fix bad slots)

WORKED EXAMPLES:
  Slot 1: 6, mana=9.  Merge new=5 → GCD=1, ×2.0 → mana=18, value=1 (great)
  Slot 1: 6, mana=9.  Merge new=4 → GCD=2, ×0.9 → mana=8,  value=2 (LOSS)
  Slot 1: 1, mana=18. Merge new=1 → both 1, ×2.5 → mana=45, value=1
  Slot 1: 8, mana=9.  Merge new=9 → GCD=1, ×2.0 → mana=18, value=1
  Slot 1: 4, mana=9.  Merge new=8 → GCD=4, ×0.9 → mana=8,  value=4 (LOSS)

STRATEGY:
  - Merge COPRIME pairs (no shared factors). Easy wins:
      5+anything-not-multiple-of-5, 7+anything (7 prime), 11+anything (11 prime)
      Adjacent integers (3+4, 5+6, 8+9) are always coprime.
  - AVOID pairs sharing factors: 4+6, 6+9, 8+12, 4+8, 9+12.
  - Once a slot reaches 1 (after a coprime merge), keep merging coprimes for
    a chain of ×2.0 → ×2.0 → ×2.0.
  - Primes (2,3,5,7,11) are coprime with everything except their own multiples.\
""",
    ("number", "trigon"): """\
==== MATH — TRIGON MODE ====
Each card has an angle value (typically multiples of 15° or 30°).
A merge combines the angles trigonometrically. Hardest math mode.

GENERAL PRINCIPLE: COMPLEMENTARY pairs (sum to 90°) and SUPPLEMENTARY pairs
(sum to 180°) are the high-multiplier merges.

ROUGH SCORING:
  Both at 0°                  → 2.5x  PERFECT
  Sum to 90° or 180°          → 2.0x  GREAT
  Acute pairs (sum < 90°)     → ~1.0-1.5x
  Obtuse / extreme pairs      → 0.7-0.9x
  Two of the same angle       → 0.9x  BAD

STRATEGY:
  - Look for sum=90° pairs (30+60, 45+45, 0+90).
  - Or sum=180° pairs (60+120, 90+90 — careful not same! — 30+150).
  - Avoid merging two equal angles.
  - When in doubt, keep building toward the identity 0° card.\
""",
    ("number", "vector"): """\
==== MATH — VECTOR MODE ====
Cards have integers 1-8 representing 2D direction vectors:
  1=(0,1)↑  2=(1,1)↗  3=(1,0)→  4=(1,-1)↘
  5=(0,-1)↓ 6=(-1,-1)↙ 7=(-1,0)← 8=(-1,1)↖
Identity = 0 (zero vector).

EXACT SCORING:
  Both 0                      → 2.5x  PERFECT
  Vector sum becomes 0        → 2.0x  GREAT (opposite directions: 1+5, 3+7, 2+6, 4+8)
  Perpendicular pairs         → 1.5-2.0x
  Adjacent vectors            → 0.9-1.0x
  Same vector                 → 0.7x

  SPECIAL: slot=0, new≠0      → 0.9x  BAD
  SPECIAL: slot≠0, new=0      → resets slot to 0

STRATEGY:
  - Merge OPPOSITE vector pairs: 1+5, 3+7, 2+6, 4+8 → ×2.0.
  - Or perpendicular: 1+3, 1+7, 3+5, 5+7 → ×1.5+.\
""",
    ("number", "interval"): """\
==== MATH — INTERVAL MODE ====
Cards have integers 1-9 representing musical intervals (semitones).
Merge scoring is based on consonance/dissonance.

ROUGH SCORING:
  Both 0                              → 2.5x  PERFECT
  Consonant intervals (octave, 5th)   → 2.0x  GREAT
  Mildly consonant (3rd, 6th)         → 1.0-1.5x
  Dissonant (close numbers, 2nd, 7th) → 0.7-0.9x

STRATEGY:
  - Merge numbers that differ by 7 (perfect 5th) or 12 (octave).
  - Avoid adjacent numbers (1+2, 2+3) — these are dissonant.\
""",
    ("number", "sort"): """\
==== MATH — SORT MODE ====
Cards have numbers that should be arranged in order across the build slots.
Merging is generally NOT the goal — placement is.

STRATEGY:
  - Place cards so that values increase monotonically left-to-right (slot 1 < slot 2 < ... < slot 5).
  - Sell out-of-order cards.\
""",
    # =================================================================
    # VISUAL (color)
    # =================================================================
    ("color", "add"): """\
==== VISUAL — ADD MODE (additive RGB colour mixing) ====
Each card is one of 7 colours, shown in metadata as "Color=Red" etc:
  PRIMARIES: Red, Green, Blue
  MIXES:     Yellow (R+G), Cyan (G+B), Magenta (R+B)
  IDENTITY:  White (R+G+B)

MENTAL MODEL: a primary "contains" itself; a mix "contains" the two primaries
that built it. Yellow contains Red and Green. Each primary's COMPLEMENT is the
mix that does NOT contain it: Red ↔ Cyan, Green ↔ Magenta, Blue ↔ Yellow.

EXACT SCORING:
  Both White                                          → 2.5x  PERFECT
  Two DIFFERENT mixes (Y+C, Y+M, C+M)                 → 2.0x  GREAT (→ slot becomes White)
  Primary + its COMPLEMENT mix (R+Cyan, G+Magenta,
                                B+Yellow)             → 2.0x  GREAT (→ slot becomes White)
  Two DIFFERENT primaries (R+G, R+B, G+B)             → 1.5x  GOOD  (→ slot becomes the mix)
  Same colour                                         → 0.9x  BAD
  White + non-White                                   → 0.9x  BAD (wasted identity)
  Primary + mix CONTAINING that primary (R+Y, R+M,
                          G+Y, G+C, B+M, B+C)         → 0.9x  BAD

  SPECIAL: non-White slot + White new → resets slot to White, no multiplier
           (use this to "fix" a bad slot for free)

WORKED EXAMPLES:
  Slot 1: Yellow,  mana=9.  Merge new=Cyan    → Y+C, ×2.0 → mana=18, slot=White
  Slot 1: Red,     mana=9.  Merge new=Cyan    → R+complement, ×2.0 → mana=18, slot=White
  Slot 1: White,   mana=18. Merge new=White   → both White, ×2.5 → mana=45
  Slot 1: Red,     mana=9.  Merge new=Yellow  → R contained in Y, ×0.9 → mana=8 (LOSS)
  Slot 1: Red,     mana=9.  Merge new=Green   → R+G, ×1.5 → mana=14, slot=Yellow

STRATEGY:
  - BEST merges: two-different-mixes, OR primary+complement-mix. Both score ×2.0
    AND turn the slot White, setting up a future ×2.5 with another White card.
  - GOOD merges: two-different-primaries (×1.5). Builds toward a mix.
  - MEMORISE the complements: Red↔Cyan, Green↔Magenta, Blue↔Yellow.
  - HOLD White cards. They're worth ×2.5 perfects with other Whites.
  - NEVER merge a primary into a mix that contains it (×0.9 — pure loss).\
""",
    ("color", "subtract"): """\
==== VISUAL — SUBTRACT MODE (subtractive CMY colour mixing) ====
Same structure as Add mode but with the roles SWAPPED:
  PRIMARIES: Cyan, Magenta, Yellow
  MIXES:     Blue (C+M), Red (M+Y), Green (C+Y)
  IDENTITY:  Black

COMPLEMENTS: Cyan↔Red, Magenta↔Green, Yellow↔Blue.

SCORING (same multiplier table as Add mode):
  Both Black                                  → 2.5x  PERFECT
  Two different mixes (R+G, R+B, G+B)         → 2.0x  GREAT (→ Black)
  Primary + complement mix
    (C+Red, M+Green, Y+Blue)                  → 2.0x  GREAT (→ Black)
  Two different primaries (C+M, C+Y, M+Y)     → 1.5x  GOOD  (→ the mix)
  Same colour                                 → 0.9x  BAD
  Black + non-Black                           → 0.9x  BAD
  Primary + mix containing it
    (C+Blue, C+Green, M+Blue, M+Red,
     Y+Red, Y+Green)                          → 0.9x  BAD

STRATEGY: identical to Add mode — use the swapped colour identities.\
""",
    ("color", "gray"): """\
==== VISUAL — GRAY MODE ====
Each card has a gray-level index 1-9 (1=darkest, 9=lightest), shown in metadata
as "Gray=N". Plus White (the identity).

EXACT SCORING:
  Both White                                  → 2.5x  PERFECT
  Same gray index                             → 0.9x  BAD
  White + non-White                           → 0.9x  BAD (wasted identity)

  Slot LIGHTER than incoming (slot_idx > new_idx):
    sum > 9   → 2.0x GREAT, slot becomes White
    sum ≤ 9   → 1.5x GOOD,  slot becomes index=sum (still gray, but lighter)

  Slot DARKER or EQUAL to incoming             → 0.9x  BAD
  Non-White slot + White new                   → resets slot to White (no multiplier)

WORKED EXAMPLES:
  Slot 1: Gray=5, mana=9.  Merge new=Gray=6  → slot darker, ×0.9 → mana=8 (LOSS)
  Slot 1: Gray=8, mana=9.  Merge new=Gray=4  → slot lighter, sum=12>9, ×2.0 → mana=18, slot=White
  Slot 1: Gray=8, mana=9.  Merge new=Gray=1  → slot lighter, sum=9≤9, ×1.5 → mana=14, slot=Gray9
  Slot 1: White,  mana=18. Merge new=White   → both White, ×2.5 → mana=45

STRATEGY:
  - Always merge DARKER cards INTO LIGHTER slots (slot index must be > new index).
  - Aim for sum > 9 → ×2.0 AND sets up future White merges.
  - Hold the highest-index gray (Gray=9) as a powerful merge target — almost
    anything merged INTO it is "lighter slot" and will trigger sum>9 easily.
  - NEVER merge two cards of equal gray (×0.9).\
""",
    ("color", "text"): """\
==== VISUAL — TEXT MODE (Stroop effect) ====
Each card shows a colour NAME written in a DIFFERENT INK colour. The merge
logic uses the INK colour, not the printed word — exactly like Add mode.

In metadata you see RGB values (the ink colour). Use the ADD mode scoring table.

  Two different mixes      → 2.0x
  Primary + complement     → 2.0x
  Two different primaries  → 1.5x
  Same colour              → 0.9x
  Primary + containing mix → 0.9x
  Both White               → 2.5x

This mode is hardest in screenshot mode (Stroop conflict). In metadata mode
it's identical to Add — just read the ink colour and apply Add rules.\
""",
    # =================================================================
    # SPATIAL (shape)
    # =================================================================
    ("shape", "triangle"): """\
==== SPATIAL — TRIANGLE MODE ====
Cards show triangles in 8 orientations (index 0-7, rotating in 45° steps).
Index 8 = blank/identity. Shown in metadata as "Shape=N".

ROUGH SCORING:
  Both 8 (blank)                          → 2.5x  PERFECT
  Opposite orientations (idx differ by 4) → 2.0x  GREAT
       (e.g. 0+4, 1+5, 2+6, 3+7)
  Perpendicular (idx differ by 2 or 6)    → 1.5x  GOOD
  Adjacent orientations                   → 0.9-1.0x
  Same orientation                        → 0.7-0.9x

  SPECIAL: blank slot + non-blank → 0.9x (wasted identity)
  SPECIAL: non-blank slot + blank → resets slot to blank

STRATEGY:
  - Merge OPPOSITE triangles (4 apart): 0↔4, 1↔5, 2↔6, 3↔7.
  - Hold blank cards (Shape=8) as identity targets for ×2.5.\
""",
    ("shape", "rectangle"): """\
==== SPATIAL — RECTANGLE MODE ====
Cards show rectangles in 8 orientations (index 0-7). Index 8 = blank/identity.

Same merge structure as Triangle mode:
  Both blank (8)                           → 2.5x  PERFECT
  Opposite orientations (4 apart)          → 2.0x  GREAT
  Perpendicular                            → 1.5x  GOOD
  Adjacent / same                          → 0.7-1.0x

STRATEGY: same as Triangle — pair orientations 4 apart.\
""",
    ("shape", "kanizsa"): """\
==== SPATIAL — KANIZSA MODE ====
Cards show Kanizsa illusory contour patterns (index 0-7). Index 8 = blank.
This mode is a key VLM test — the illusory contours must be PERCEIVED, not
just counted from the visible parts.

Same merge structure as Triangle mode (orientations, not actual content):
  Both blank (8)                           → 2.5x  PERFECT
  Opposite orientations (4 apart)          → 2.0x  GREAT
  Perpendicular                            → 1.5x
  Same / adjacent                          → 0.7-0.9x

In metadata mode you see Shape=N — treat it like Triangle.\
""",
    ("shape", "hanoi"): """\
==== SPATIAL — HANOI MODE ====
Cards represent Tower of Hanoi disc configurations (index 0-15). Index 16 = blank.
ONE OF THE HARDEST modes — requires multi-step planning.

Each index encodes a specific (peg, disc) state. A merge represents a Hanoi
move. VALID Hanoi moves score well; invalid ones don't.

ROUGH STRATEGY:
  - Treat each card index as a state in a Hanoi puzzle.
  - Aim to chain merges along the optimal solution path.
  - When uncertain, prefer the BLANK card (index 16) as identity (×2.5 with itself).
  - This mode is genuinely hard — focus on simple wins (blank+blank) and
    sell low-quality cards.\
""",
    ("shape", "triple"): """\
==== SPATIAL — TRIPLE MODE ====
Cards show three overlapping shapes. Merge logic is based on which triple
patterns combine into recognised figures.

STRATEGY: hold blank cards for safe ×2.5 merges; sell unclear ones early.\
""",
    ("shape", "sphere"): """\
==== SPATIAL — SPHERE MODE ====
Cards show 3D sphere positions. Merging combines the spatial positions —
opposing or symmetric positions score better than adjacent ones.

STRATEGY: merge spheres on opposite sides of the sphere; hold blanks for ×2.5.\
""",
    # =================================================================
    # VERBAL (word)
    # =================================================================
    ("word", "verbs"): """\
==== VERBAL — VERBS MODE ====
Each card has one or more VERBS (e.g. "run", "walk", "throw"), shown in metadata
as "Word=[verb]". Merging compares the words against a built-in PAIRED-WORDS
list of related verb pairs (e.g. "run"↔"sprint", "throw"↔"catch").

ROUGH SCORING:
  All words are PAIR matches             → 2.0-2.5x  GREAT (related verbs)
  Some pair matches                      → 1.0-1.5x
  No relationship                        → 1.0x  neutral
  IDENTICAL words                        → 0.9x  BAD (penalty for duplicates)

STRATEGY:
  - Merge cards whose verbs are RELATED but NOT identical.
  - Examples of probable pairs: "run"+"sprint", "walk"+"stroll", "eat"+"chew",
    "throw"+"catch", "give"+"take", "buy"+"sell".
  - AVOID merging two cards with the same word.
  - You won't always know the pairings in advance — observe what scored well
    and remember those pairs.\
""",
    ("word", "nouns"): """\
==== VERBAL — NOUNS MODE ====
Same as Verbs mode but with nouns (e.g. "dog", "bone", "table", "chair").

STRATEGY:
  - Merge RELATED nouns: "dog"+"bone", "table"+"chair", "key"+"lock",
    "cup"+"saucer", "bread"+"butter".
  - Avoid identical nouns.\
""",
    ("word", "adjectives"): """\
==== VERBAL — ADJECTIVES MODE ====
Same as Verbs mode but with adjectives.

STRATEGY:
  - Merge RELATED adjective pairs (often opposites): "hot"+"cold", "big"+"small",
    "fast"+"slow", "happy"+"sad".
  - Avoid identical adjectives.\
""",
    ("word", "synVerbs"): """\
==== VERBAL — SYNONYM VERBS MODE ====
Cards have verbs; matching is based on SYNONYMS (same meaning) rather than
related-pair lists.

ROUGH SCORING:
  Synonym pair                  → 2.0-2.5x  GREAT
  Unrelated                     → 1.0x  neutral
  Identical word                → 0.9x  BAD (must be DIFFERENT but same meaning)

STRATEGY:
  - Merge verbs that mean the SAME thing in DIFFERENT words:
    "run"+"sprint", "walk"+"stroll", "eat"+"consume", "build"+"construct",
    "begin"+"start", "finish"+"complete".
  - "Same meaning, different word" is the gold standard.\
""",
    ("word", "synAdjectives"): """\
==== VERBAL — SYNONYM ADJECTIVES MODE ====
Same as synVerbs but with adjectives.

STRATEGY:
  - Merge synonymous adjectives: "big"+"large", "fast"+"quick", "happy"+"glad",
    "smart"+"clever", "tired"+"exhausted".\
""",
    ("word", "grammar"): """\
==== VERBAL — GRAMMAR MODE ====
Cards contain grammar elements / sentence fragments. Merging combines them
into longer fragments. Grammatically VALID combinations score well.

ROUGH SCORING:
  Forms a valid grammatical phrase       → 2.0-2.5x
  Partially valid                        → 1.0-1.5x
  Invalid combination                    → 0.9x

STRATEGY:
  - Think of each card as a sentence chunk (subject, verb, object, modifier).
  - Merge in an order that builds a sensible sentence.
  - Subject + verb, verb + object, adjective + noun are usually good.\
""",
    ("word", "questions"): """\
==== VERBAL — QUESTIONS MODE ====
Cards have question words/phrases. Merging tries to form valid Q&A pairs.

STRATEGY:
  - Merge question + matching answer pattern.\
""",
    ("word", "scrabble"): """\
==== VERBAL — SCRABBLE MODE ====
Each card has a single LETTER (a single character), shown in metadata as
"Word=[A]". Merging CONCATENATES the letters. If the result spells a real
English word, score increases with the word length.

ROUGH SCORING:
  Length 4+ valid word        → 2.5x  PERFECT
  Length 3 valid word         → 2.0x  GREAT
  Length 2 valid word         → 1.5x  GOOD
  Not a valid word            → 1.0x  neutral (NOT negative)

NOTE on order: when merging new → slot, the new letter is PREPENDED to the
slot's existing string. So if slot has "AT" and you merge new "C", the slot
becomes "CAT" (a real word, ×2.0). Plan letter ORDER carefully.

WORKED EXAMPLES:
  Slot 1: "T", mana=9.  Merge new="A" → slot becomes "AT" (valid 2-letter), ×1.5 → mana=14
  Slot 1: "AT", mana=14. Merge new="C" → slot becomes "CAT", ×2.0 → mana=28
  Slot 1: "CAT", mana=28. Merge new="S" → slot becomes "SCAT", ×2.5 → mana=70

STRATEGY:
  - Plan SHORT WORDS first: build "CAT", "DOG", "RUN" before going for longer.
  - Common 2-letter words: AT, IT, IS, ON, IN, OR, AS, TO, OF, BE, GO, NO, SO.
  - Common 3-letter: CAT, DOG, RUN, SUN, RED, BIG, EAT, EYE, BOY, GIRL.
  - The new letter PREPENDS — visualise (new + slot) when planning.
  - Vowels are precious — hold them; consonants are more flexible.
  - This is a reasoning-heavy mode: think two letters ahead.\
""",
    # =================================================================
    # MEMORY
    # =================================================================
    ("memory", "every action"): """\
==== MEMORY — EVERY ACTION MODE ====
After EVERY action you take, all card values are HIDDEN in the metadata.
You see that a slot is occupied and its mana, but NOT its dimension values.
Hidden slots show "[HIDDEN]" in the state description.

The MERGE LOGIC of other dimensions still applies — you just can't see the
values. You must REMEMBER each card's values from when they were last visible
(typically when freshly drawn).

STRATEGY:
  - When a card is drawn, NOTE its values in your reasoning. The "new" slot
    is briefly visible.
  - Track each slot's contents in your head (or in the conversation history).
  - Plan merges that you can VERIFY mentally without re-reading the slots.
  - When uncertain, draw a fresh card so you can see at least one value, then
    pair it with a slot whose values you remember.
  - In conversational mode (Mode B), use earlier turns as your "memory log".
  - Conservative play: merge fewer times but more confidently.\
""",
    ("memory", "show all"): """\
==== MEMORY — SHOW ALL MODE ====
Cards are periodically REVEALED (all at once) for a brief moment, then hidden.
Easier than "every action" — you get periodic refreshes of full state.

STRATEGY:
  - When all cards are visible, take maximum actions to lock in your plan.
  - Between refreshes, rely on what you saw last.
  - Conservative play during hidden phases; aggressive during reveals.\
""",
    ("memory", "show one"): """\
==== MEMORY — SHOW ONE MODE ====
Only ONE card is revealed at a time, rotating through slots. You must build a
mental model of all cards from partial glimpses.

STRATEGY:
  - Keep a running mental list of (slot → values) updated each time a slot reveals.
  - Use conversational history as your notepad.
  - Be cautious with merges — you might be acting on stale info.\
""",
}

# Map dimension fields to human-readable names used in raw_state mode keys
_MODE_FIELD_MAP = {
    "number": "mode_number",
    "color": "mode_color",
    "shape": "mode_shape",
    "word": "mode_word",
    "beat": "mode_beat",
    "memory": "mode_memory",
    "motor": "mode_motor",
}

_COLOR_NAMES = {
    (1, 0, 0): "Red", (0, 1, 0): "Green", (0, 0, 1): "Blue",
    (1, 1, 0): "Yellow", (0, 1, 1): "Cyan", (1, 0, 1): "Magenta",
    (1, 1, 1): "White", (0, 0, 0): "Black",
}

# Merge gain tier → (label, multiplier) mapping used by describe_state when
# rendering the merge_previews block. Bridge-side ComputeMerge*Gain returns
# integer tiers in the set {-1, 0, 1, 2, 3}; the multipliers come from
# ManaDisplay.cs at difficulty=0 (the only difficulty the benchmark runs):
# manaReductionMultiplier=0.9, manaIncreaseMultiplier1=1.5,
# manaIncreaseMultiplier2=2.0, manaIncreaseMultiplier3=2.5.
#
# Format note: emitting tier WORDS plus the multiplier (instead of the bare
# integer the old format used) avoids the "Num=+2 reads as a resulting card
# value" confusion. The slot dump uses "Num=-2.0" for actual numeric card
# values, and small models repeatedly mistook the preview's "Num=+2" tier
# code for a card value.
_MERGE_TIER = {
    -1: ("BAD",       "0.9"),
     0: ("neutral",   "1.0"),
     1: ("GOOD",      "1.5"),
     2: ("GREAT",     "2.0"),
     3: ("PERFECT",   "2.5"),
}

# Short, unambiguous dimension labels for the preview rows. The slot dump
# uses Num/Color/Shape/Word; we mirror those exactly so the model can map
# "Number GREAT" in a preview to the "Num=..." it sees in the slot lines.
_DIM_NAME = {
    "number": "Number",
    "color":  "Color",
    "shape":  "Shape",
    "word":   "Word",
}

# Hardcoded merge cap matches the game's per-card limit (maxNumberOfMerges
# in CardFrame.cs / NumberCard.cs). The slot serializer doesn't expose this
# value, and the greedy_agent.py heuristic hardcodes the same constant — see
# greedy_agent.py:142. If the game ever changes this value, both call sites
# need to update together.
_MERGE_CAP = 3


def _build_sell_hint(slots: list, mana: float, mana_max: float) -> str:
    """Single-line sell-candidate hint for the prompt.

    Walks the build slots, picks the highest-mana occupied one, and reports
    what selling it RIGHT NOW would do to the bank — specifically, whether
    the resulting `mana + card_mana` would exceed the current `Best`.

    Why this exists: small models repeatedly fail this comparison. Trace
    analysis on Qwen3-VL 4B's EASY runs showed it routinely sells mana=9
    cards "because selling looks safe", which cannot raise the score, then
    never lets a slot accumulate enough merges to compound. Lifting the
    arithmetic out of the model and into the state dump removes the
    cognitive cost of that comparison.

    Returns "" when no build slot is occupied (nothing to hint about).
    """
    # slots indexes from SerializeGameState: 0 = new, 1..5 = build, 6 = sell.
    # Only build slots are meaningful sell candidates — selling new is just
    # rebating the draw cost, and the sell slot itself isn't an action target.
    candidates = []
    for idx in range(1, 6):
        if idx >= len(slots):
            break
        slot = slots[idx]
        if not slot.get("occupied", False):
            continue
        try:
            card_mana = float(slot.get("card_mana", 0) or 0)
        except (TypeError, ValueError):
            card_mana = 0.0
        try:
            merges = int(slot.get("merges_done", 0) or 0)
        except (TypeError, ValueError):
            merges = 0
        candidates.append((idx, card_mana, merges))

    if not candidates:
        return ""

    # Pick highest card_mana; tie-break on merges_done (closer to MAXED
    # implies the card is "done" and the right thing to liquidate). Ties
    # after that fall back to lowest slot index for determinism, which the
    # reverse-sort below preserves naturally because Python's sort is stable.
    candidates.sort(key=lambda t: (t[1], t[2]), reverse=True)
    idx, card_mana, merges = candidates[0]

    maxed = merges >= _MERGE_CAP
    merge_str = f"{merges}/{_MERGE_CAP} merges"
    if maxed:
        merge_str += ", MAXED — cannot grow further"

    sell_action = 31 + idx  # action ID for "Sell slot {idx}" — see _describe_action
    bank_after = float(mana or 0) + card_mana

    try:
        best = float(mana_max or 0)
    except (TypeError, ValueError):
        best = 0.0

    head = (
        f"Sell hint: best candidate is slot {idx} "
        f"(+{card_mana:.0f} mana, {merge_str}, action {sell_action})."
    )

    if best <= 0:
        return f"{head} Bank would become {bank_after:.0f}."

    if bank_after > best:
        return (
            f"{head} Selling now would raise Best from "
            f"{best:.0f} → {bank_after:.0f}."
        )

    deficit = best - bank_after
    return (
        f"{head} Best is {best:.0f}; selling now only reaches "
        f"{bank_after:.0f} (short by {deficit:.0f}) — keep merging unless MAXED."
    )


def _color_name(r: float, g: float, b: float) -> str:
    key = (round(r), round(g), round(b))
    return _COLOR_NAMES.get(key, f"RGB({r:.2f},{g:.2f},{b:.2f})")


def build_system_prompt(
    modes: dict,
    prompt: "Optional[Prompt]" = None,
    *,
    include_history_legend: bool = False,
    vision_legend: bool = False,
) -> str:
    """Build a game-specific system prompt from active modes.

    If `prompt` is provided, its `core_rules` and `dimension_rules` are used as
    the source of truth (the registry-driven path used by the web UI). Otherwise
    the module-level CORE_RULES + DIMENSION_RULES constants are used (legacy
    path, kept so the old benchmark_runner CLI still works).

    `prompt.dimension_rules` is keyed by flat strings of the form "field:mode"
    (e.g. "number:add"), while the legacy DIMENSION_RULES dict is keyed by
    tuples (field, mode). Both shapes are handled here.

    `include_history_legend` injects the compact-history format legend used by
    Mode C agents (metadata-c / vision-c). `vision_legend` switches to the
    vision-mode variant of that legend (attribute-stripped cells, screenshot
    as source of perceptual truth).
    """
    if prompt is not None:
        core = prompt.core_rules
        dim_rules = prompt.dimension_rules

        def lookup(field: str, mode_val: str):
            return dim_rules.get(f"{field}:{mode_val}")
    else:
        core = CORE_RULES

        def lookup(field: str, mode_val: str):
            return DIMENSION_RULES.get((field, mode_val))

    parts = [core, ""]

    # Add rules for each active dimension
    has_rules = False
    for field, mode_val in modes.items():
        if not mode_val:
            continue
        rule = lookup(field, mode_val)
        if rule:
            parts.append(rule)
            has_rules = True

    if not has_rules:
        parts.append("No specific dimension rules available — use general merge strategy.")

    if include_history_legend:
        parts.append(_COMPACT_HISTORY_LEGEND_VISION if vision_legend else _COMPACT_HISTORY_LEGEND)

    parts.append("")
    parts.append("RESPONSE FORMAT")
    parts.append(
        "You may write a SHORT line of reasoning (one or two sentences max) "
        "describing the candidate merges you considered and why you picked one. "
        "Then output your final choice on a NEW line in the exact form:\n"
        "    ACTION: <integer>\n"
        "where <integer> is one of the action IDs from the 'Valid actions:' list "
        "in the user message. The parser looks for the ACTION: marker first; if "
        "it's missing, it falls back to scanning the last line for an integer. "
        "Examples of valid replies:\n"
        "    ACTION: 0\n"
        "    Slot 3 has Num=2, new is Num=-2 → sum 0, ×2.0. Best option.\n"
        "    ACTION: 19\n"
        "Do NOT wrap the action ID in code fences or quotes. Do NOT output more "
        "than one ACTION: line. Keep the reasoning brief — long explanations "
        "burn tokens and slow the run."
    )

    return "\n\n".join(parts)


def describe_state(
    raw_state: dict,
    show_merge_previews: bool = False,
    hide_perceptual_attrs: bool = False,
) -> str:
    """Convert raw game state dict to a concise text description for the LLM.

    Args:
        raw_state: AgentBridge.SerializeGameState output dict.
        show_merge_previews: when True, render the bridge's pre-computed
            merge_previews block (per-dim gain tier for every legal merge
            candidate this turn). Default False — the canonical benchmark
            withholds these so the model has to estimate gains itself; flip
            this on for an "assisted-mode" run.
        hide_perceptual_attrs: when True, strip per-slot card attributes
            (Num, Color, Gray, Shape, Word) from the output and emit only
            occupancy + mana + merges. Used by vision agents so the screen-
            shot is the only source of perceptual information — otherwise
            the text dump would hand the model a free answer key for the
            visual perception test. HUD-style fields (header mana, active
            modes, valid-actions list, HIDDEN flag) are kept regardless,
            since the model could read them from pixels anyway.
    """
    if not raw_state:
        return "Game not started."

    lines = []
    mana = raw_state.get("mana", 0)
    mana_max = raw_state.get("mana_max", 0)
    action_count = raw_state.get("action_count", "?")
    max_steps = raw_state.get("max_steps", "?")
    lines.append(f"Mana: {mana:.0f} | Best: {mana_max:.0f} | Step: {action_count}/{max_steps}")

    # Active modes (for conversational context — the model may forget)
    mode_strs = []
    for dim_field, state_key in _MODE_FIELD_MAP.items():
        mode_val = raw_state.get(state_key, "")
        if mode_val:
            mode_strs.append(f"{dim_field}:{mode_val}")
    if mode_strs:
        lines.append(f"Modes: {', '.join(mode_strs)}")

    lines.append("")

    # Slots
    slots = raw_state.get("slots", [])
    slot_labels = ["new", "1", "2", "3", "4", "5", "sell"]
    for i, slot in enumerate(slots):
        label = slot_labels[i] if i < len(slot_labels) else f"s{i}"
        if not slot.get("occupied", False):
            lines.append(f"  [{label}] Empty")
            continue

        hidden = slot.get("memory_hidden", False)
        card_mana = slot.get("card_mana", 0)
        merges = slot.get("merges_done", 0)

        if hidden:
            lines.append(f"  [{label}] HIDDEN | Mana={card_mana:.0f} | Merges={merges}")
            continue

        # Vision mode: strip perceptual attributes. The screenshot is the
        # only place the model should learn Num/Color/Shape/Word from.
        if hide_perceptual_attrs:
            lines.append(
                f"  [{label}] Occupied (see screenshot) "
                f"| Mana={card_mana:.0f} | Merges={merges}"
            )
            continue

        attrs = []

        # Number
        num_val = slot.get("number_value", 0)
        if slot.get("number_active", False) or abs(num_val) > 0.01:
            attrs.append(f"Num={num_val:.1f}")

        # Color
        cr = slot.get("color_r", 0)
        cg = slot.get("color_g", 0)
        cb = slot.get("color_b", 0)
        gray_idx = slot.get("color_index_gray", 0)
        if cr > 0 or cg > 0 or cb > 0:
            attrs.append(f"Color={_color_name(cr, cg, cb)}")
        if gray_idx > 0:
            attrs.append(f"Gray={gray_idx}")

        # Shape
        shape_idx = slot.get("shape_index", -1)
        if shape_idx >= 0:
            attrs.append(f"Shape={shape_idx}")

        # Word
        word_val = slot.get("word_value", "")
        if word_val:
            attrs.append(f"Word=[{word_val}]")

        attr_str = ", ".join(attrs) if attrs else "no-attrs"
        lines.append(f"  [{label}] {attr_str} | Mana={card_mana:.0f} | Merges={merges}")

    # Merge previews — the bridge pre-computes the per-dim gain tier for every
    # legal merge candidate this turn. Only rendered when show_merge_previews
    # is on (assisted ablation): the canonical benchmark withholds them so the
    # model has to estimate gains from the slot dump itself.
    #
    # Format note: the previous version emitted "Num=+2" for "Number gain
    # tier = 2 (great)". This collided with the slot-dump format where
    # "Num=-2.0" means the actual numeric value of the card, and small
    # models (Qwen3-VL 4B, Llama-3.2 11B) consistently misread the preview
    # as the resulting card's value. The format below uses tier WORDS
    # (PERFECT/GREAT/GOOD/OK/neutral/BAD/TERRIBLE) inline with the multiplier
    # so there is no overlap with the slot-value notation, and the action
    # number leads each row to line up with the Valid actions block below.
    if show_merge_previews:
        previews = raw_state.get("merge_previews") or []
        active_dims = [
            dim for dim in ("number", "color", "shape", "word")
            if raw_state.get(f"mode_{dim}")
        ]
        if previews and active_dims:
            lines.append("")
            lines.append(
                "Merge previews (per-dimension tier × multiplier — multipliers "
                "compound across active dims):"
            )
            for p in previews:
                src = p.get("source", "?")
                tgt = p.get("target", "?")
                action = p.get("action")
                parts = []
                for dim in active_dims:
                    g = int(p.get(f"{dim}_gain", 0))
                    label, mult = _MERGE_TIER.get(g, (f"tier{g:+d}", "?"))
                    parts.append(f"{_DIM_NAME[dim]} {label} ×{mult}")
                action_str = f"a{action:<3}" if action is not None else "?   "
                lines.append(f"  {action_str} {src}→{tgt}: {', '.join(parts)}")

    # Sell-candidate hint — surfaces the highest-mana built slot and whether
    # selling it RIGHT NOW would actually raise the score (i.e. push the bank
    # past `Best`). This is the discipline check small models repeatedly
    # fail: they sell single-merge cards (mana=9, no-op for the score) and
    # never sit on a card long enough for it to compound. Lifting the
    # arithmetic out of the model and into the state dump removes the
    # cognitive cost of that comparison.
    sell_hint = _build_sell_hint(slots, mana, mana_max)
    if sell_hint:
        lines.append("")
        lines.append(sell_hint)

    # Valid actions
    valid = raw_state.get("valid_actions", [])
    if valid:
        lines.append("")
        lines.append("Valid actions:")
        for a in sorted(valid):
            lines.append(f"  {a}: {_describe_action(a)}")

    if raw_state.get("game_over", False):
        lines.append(f"\nGAME OVER — Final max mana: {mana_max:.0f}")

    return "\n".join(lines)


def _describe_action(action: int) -> str:
    slot_names = ["new", "1", "2", "3", "4", "5"]
    if action == 0:
        return "Draw card"
    elif action == 37:
        return "Wait"
    elif 1 <= action <= 30:
        idx = action - 1
        src_idx = idx // 5
        dst_num = (idx % 5) + 1
        return f"Move {slot_names[src_idx]} → slot {dst_num}"
    elif 31 <= action <= 36:
        src_idx = action - 31
        return f"Sell {slot_names[src_idx]}"
    return f"? ({action})"


# =====================================================================
# Compact-history encoding (Mode C: metadata-c / vision-c)
# =====================================================================
#
# In compact mode the model sees, before the current full state, a one-line
# log entry per past step. This compresses the trajectory ~10-20× compared to
# full-state conversational mode while still letting the model reason about
# what it just did. The format is documented in the system prompt — see
# `_compact_history_legend` below — so the model can decode each line.

# Single-letter color codes used in the compact slot encoding.
_COMPACT_COLOR = {
    (1, 0, 0): "R", (0, 1, 0): "G", (0, 0, 1): "B",
    (1, 1, 0): "Y", (0, 1, 1): "C", (1, 0, 1): "M",
    (1, 1, 1): "W", (0, 0, 0): "K",
}


def _compact_slot(slot: dict, hide_perceptual_attrs: bool = False) -> str:
    """Render a single slot as a comma-separated cell, e.g. '+2,R,m15,x1' or '.'.

    Empty slot → ".". Hidden card (Memory mode) → "?,m15,x1" — only mana and
    merges are visible. Otherwise we emit one short token per active dimension
    plus mana and merges-done.

    When ``hide_perceptual_attrs`` is True (vision-mode trail), the per-
    dimension tokens are stripped: an occupied visible card becomes
    ``X,m15,x1`` (occupancy + mana + merges only) so the screenshot remains
    the sole source of Num/Color/Shape/Word. Mana and merges are HUD text
    the model could read from pixels regardless, so we keep them in the
    trail to preserve the "what did this slot look like last turn"
    reasoning scratchpad the compact mode is built around.
    """
    if not slot.get("occupied", False):
        return "."

    parts: list[str] = []

    if slot.get("memory_hidden", False):
        parts.append("?")
    elif hide_perceptual_attrs:
        parts.append("X")
    else:
        # Number
        num_val = slot.get("number_value", 0.0)
        if slot.get("number_active", False) or abs(num_val) > 0.01:
            if abs(num_val - round(num_val)) < 0.01:
                parts.append(f"{int(round(num_val)):+d}")
            else:
                parts.append(f"{num_val:+.1f}")
        # Color (single letter)
        cr = slot.get("color_r", 0)
        cg = slot.get("color_g", 0)
        cb = slot.get("color_b", 0)
        if cr > 0 or cg > 0 or cb > 0:
            parts.append(_COMPACT_COLOR.get(
                (round(cr), round(cg), round(cb)),
                f"rgb{round(cr)}{round(cg)}{round(cb)}",
            ))
        gray_idx = slot.get("color_index_gray", 0)
        if gray_idx > 0:
            parts.append(f"g{gray_idx}")
        # Shape (single digit)
        shape_idx = slot.get("shape_index", -1)
        if shape_idx >= 0:
            parts.append(f"s{shape_idx}")
        # Word (bracketed)
        word_val = slot.get("word_value", "")
        if word_val:
            parts.append(f"[{word_val}]")

    parts.append(f"m{slot.get('card_mana', 0):.0f}")
    parts.append(f"x{slot.get('merges_done', 0)}")
    return ",".join(parts)


def _compact_slots_row(slots: list, hide_perceptual_attrs: bool = False) -> str:
    """Render the row [new|s1|s2|s3|s4|s5] for one step.

    The first 6 entries of `slots` correspond to [new, 1, 2, 3, 4, 5]; any
    extra trailing entry (e.g. the "sell" pseudo-slot the bridge sometimes
    appends) is ignored.
    """
    if not slots:
        return "|".join(["."] * 6)
    cells = [
        _compact_slot(slots[i], hide_perceptual_attrs=hide_perceptual_attrs)
        if i < len(slots) else "."
        for i in range(6)
    ]
    return "|".join(cells)


def _annotate_action(action: int) -> str:
    """Short, parseable annotation: 'a7:new>s1', 'a0:draw', 'a32:sell(s1)'."""
    slot_short = ["new", "s1", "s2", "s3", "s4", "s5"]
    if action == 0:
        return "a0:draw"
    if action == 37:
        return "a37:wait"
    if 1 <= action <= 30:
        idx = action - 1
        src = idx // 5
        dst = (idx % 5) + 1
        return f"a{action}:{slot_short[src]}>s{dst}"
    if 31 <= action <= 36:
        return f"a{action}:sell({slot_short[action - 31]})"
    return f"a{action}:?"


def format_trail_entry(
    step_idx: int,
    slots_before: list,
    action: int,
    mana_before: float,
    mana_after: float,
    hide_perceptual_attrs: bool = False,
) -> str:
    """One trail line for the compact history block.

    Layout:
        tN [new|s1|s2|s3|s4|s5] aA:annotation -> mAFTER(±DELTA)

    ``hide_perceptual_attrs`` strips per-dimension tokens inside each cell
    (vision-mode trail). See :func:`_compact_slot` for the cell format.
    """
    row = _compact_slots_row(slots_before, hide_perceptual_attrs=hide_perceptual_attrs)
    delta = mana_after - mana_before
    return (
        f"t{step_idx} [{row}] {_annotate_action(action)} "
        f"-> m{mana_after:.0f}({delta:+.0f})"
    )


_COMPACT_HISTORY_LEGEND = """\
============ HISTORY FORMAT (compact mode) ============

Before the CURRENT STATE block you will see a "PAST STEPS" log — one line
per step, oldest first, in this exact layout:

    tN [new|s1|s2|s3|s4|s5] aA:annotation -> mAFTER(±DELTA)

  tN          : step index inside this episode (t0 = first decision)
  [...]       : the six slots BEFORE the action, in order: new, slot 1..5
  aA:...      : the action you took, with a short annotation
  mAFTER      : your total mana right after the action resolved
  ±DELTA      : the mana change from this action (negative = lost mana)

Each slot cell is one of:
  .                       empty slot
  ?,mM,xK                 a hidden card (Memory mode) — value unknown,
                          you only see mana M and merges-done K
  TOKENS,mM,xK            a visible card; TOKENS depend on the active dims:
    +N or -N or +N.N      number value (sign always shown)
    R G B Y C M W K       color: Red Green Blue Yellow Cyan Magenta White blacK
    gN                    grayscale index (visual:add-gray modes)
    sN                    shape index 0-7 (visual:shape modes)
    [word]                word card (verbal modes)

Action annotations:
  a0:draw                 spawn a fresh card in "new"
  a1-a30:src>sD           move source slot onto build slot D (merges if D busy)
  a31-a36:sell(src)       destroy the card in `src` and add its mana to total
  a37:wait                no-op for one step

Use the trail as your scratchpad: it tells you exactly what happened on every
prior step. The CURRENT STATE block below it is the live, full-fidelity view
of the board you must act on right now.\
"""


# Vision-mode variant of the compact history legend. Card attributes
# (Num, Color, Shape, Word) are STRIPPED from both the current state
# dump and every historical trail cell — the screenshot is the sole
# source of perceptual information. Mana and merges-done are kept in
# each cell as HUD-readable metadata so the trail still functions as
# a per-slot "what happened" scratchpad.
_COMPACT_HISTORY_LEGEND_VISION = """\
============ HISTORY FORMAT (compact mode, vision) ============

Before the CURRENT STATE block you will see a "PAST STEPS" log — one line
per step, oldest first, in this exact layout:

    tN [new|s1|s2|s3|s4|s5] aA:annotation -> mAFTER(±DELTA)

  tN          : step index inside this episode (t0 = first decision)
  [...]       : the six slots BEFORE the action, in order: new, slot 1..5
  aA:...      : the action you took, with a short annotation
  mAFTER      : your total mana right after the action resolved
  ±DELTA      : the mana change from this action (negative = lost mana)

Because this is a VISION run, the per-slot card attributes (number,
colour, shape, word) are NOT included in either the current-state dump
or the trail — the screenshot is your only source for those. Each trail
cell is one of:

  .                       empty slot
  ?,mM,xK                 a hidden card (Memory mode) — neither text nor
                          screenshot reveals its attributes; you only see
                          mana M and merges-done K
  X,mM,xK                 an occupied visible card at that turn — look at
                          the screenshot (for the CURRENT state) or recall
                          from previous screenshots (for past turns) to
                          identify its number/colour/shape/word. The text
                          only tells you the slot was occupied with mana M
                          and merges-done K.

Action annotations:
  a0:draw                 spawn a fresh card in "new"
  a1-a30:src>sD           move source slot onto build slot D (merges if D busy)
  a31-a36:sell(src)       destroy the card in `src` and add its mana to total
  a37:wait                no-op for one step

Use the trail as your action-and-mana scratchpad; use the CURRENT STATE
screenshot as the authoritative source for what each slot actually holds
right now.\
"""


# =====================================================================
# Agent
# =====================================================================

class LLMAgent(BaseAgent):
    """LLM-based agent supporting stateless/conversational/compact × metadata/screenshot.

    The agent is provider-agnostic: it talks to the LLM through an injected
    `LLMProvider` (LiteLLMProvider in production), which dispatches to whatever
    backend the user configured (Anthropic, OpenAI, Google, custom).

    Args:
        provider: LLMProvider instance. If None, a default LiteLLMProvider is
            built from `model`/`max_tokens` for backwards-compatibility with the
            legacy CLI runner.
        prompt: Prompt object from the registry. If None, the module-level
            CORE_RULES + DIMENSION_RULES constants are used (legacy path).
        mode: "stateless" (Mode A), "conversational" (Mode B), or "compact" (Mode C).
        use_screenshot: If True, include screenshots in prompts (requires VLM env).
        game_modes: Dict of active game dimensions, used to build the system prompt.
        model: Legacy convenience — used only when `provider` is None.
        max_tokens: Legacy convenience — used only when `provider` is None.
        name: Optional override for the agent's display name.
    """

    def __init__(
        self,
        provider: "Optional[LLMProvider]" = None,
        prompt: "Optional[Prompt]" = None,
        mode: str = "conversational",
        use_screenshot: bool = False,
        game_modes: dict = None,
        model: str = "claude-sonnet-4-5",
        max_tokens: int = 512,
        name: Optional[str] = None,
        on_exchange: "Optional[callable]" = None,
        should_cancel: "Optional[callable]" = None,
        show_merge_previews: bool = False,
    ):
        if mode not in ("stateless", "conversational", "compact"):
            raise ValueError(
                f"mode must be one of stateless/conversational/compact, got {mode!r}"
            )

        # Build a default provider if the caller did not supply one. This keeps
        # the legacy `LLMAgent(model=...)` call shape working.
        if provider is None:
            from ..providers.litellm_provider import LiteLLMProvider
            provider = LiteLLMProvider(
                model=model,
                max_tokens=max_tokens,
                supports_vision=use_screenshot,
            )

        self.provider = provider
        self.prompt = prompt

        # Derive a stable display name if one was not given.
        if name is None:
            label = "vision" if use_screenshot else "meta"
            mode_label = {"stateless": "a", "conversational": "b", "compact": "c"}[mode]
            name = f"llm-{label}-{mode_label}-{provider.model}"
        super().__init__(name=name)

        self.model = provider.model
        self.mode = mode
        self.use_screenshot = use_screenshot
        self.max_tokens = provider.max_tokens

        # System prompt is built once per config (set via set_game_modes or constructor).
        # Compact mode prepends a legend section so the model can decode trail lines.
        self._game_modes = game_modes or {}
        self._system_prompt = build_system_prompt(
            self._game_modes,
            self.prompt,
            include_history_legend=(mode == "compact"),
            vision_legend=use_screenshot,
        )

        # Conversation history (Mode B only)
        self._messages: list[dict] = []

        # Compact-history trail (Mode C only). Each entry is a finalized
        # one-line trail string. `_pending_trail` carries the (slots, action,
        # mana_before) snapshot from the most recent act() call so we can
        # finalize it once on_step_result() tells us the resulting mana.
        self._compact_trail: list[str] = []
        self._pending_trail: Optional[dict] = None

        # Optional live-trace hook. The benchmark runner installs a callback
        # so the dashboard can stream LLM thinking on the Run page. Signature:
        #   on_exchange(user_text, response, action, latency_ms, error,
        #               step_in_episode)
        # The agent does NOT know which run/config/episode it's in — that
        # context is captured by the closure the runner provides.
        self.on_exchange = on_exchange
        self._exchange_step_counter = 0

        # Cooperative cancellation. The runner installs a callable here so the
        # provider can break out of long rate-limit backoff sleeps within ~1s
        # of a Cancel click in the dashboard.
        self.should_cancel = should_cancel

        # Per-run ablation flag — when True, describe_state renders the
        # bridge's pre-computed merge_previews block. The canonical benchmark
        # leaves this off so the LLM has to estimate gains itself.
        self.show_merge_previews = show_merge_previews

        # Set by act() to a human-readable reason string whenever the chosen
        # action came from _fallback_action() instead of a real model pick
        # (provider crashed, mid-backoff timeout, etc). Cleared at the top of
        # every act() call. The benchmark runner reads this after act() and
        # stamps it into events.jsonl so offline analysis can tell "real
        # decision" apart from "silent fallback" — which used to be invisible.
        self._last_action_fallback_reason: Optional[str] = None

    def set_game_modes(self, modes: dict):
        """Update game modes and rebuild the system prompt."""
        self._game_modes = modes
        self._system_prompt = build_system_prompt(
            modes,
            self.prompt,
            include_history_legend=(self.mode == "compact"),
            vision_legend=self.use_screenshot,
        )

    def reset(self):
        self._messages = []
        self._compact_trail = []
        self._pending_trail = None
        self._exchange_step_counter = 0

    def act(self, observation: dict, info: dict = None) -> int:
        import time as _time
        info = info or {}
        raw_state = info.get("raw_state", {})

        # Reset per-step so a successful call clears any previous fallback
        # marker. Set in the except branch below when we fall back.
        self._last_action_fallback_reason = None

        # Build user message content blocks. We use the OpenAI/LiteLLM content
        # block format, which the provider layer translates if needed.
        content: list[dict] = []

        # Screenshot (if enabled and available)
        if self.use_screenshot:
            screenshot = info.get("screenshot")
            if screenshot is not None and isinstance(screenshot, np.ndarray) and screenshot.size > 0:
                b64 = self._encode_screenshot(screenshot)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                })

        # Text state description (always included).
        # In compact mode the trail of past steps is prepended to the full
        # current-state dump as a single text block. The current state is
        # always full-fidelity — only history is compressed.
        state_text = describe_state(
            raw_state,
            show_merge_previews=self.show_merge_previews,
            hide_perceptual_attrs=self.use_screenshot,
        )
        if self.mode == "compact" and self._compact_trail:
            history_block = "PAST STEPS (compact trail, oldest first):\n" + "\n".join(
                self._compact_trail
            )
            text_block = history_block + "\n\nCURRENT STATE:\n" + state_text
        elif self.mode == "compact":
            text_block = "PAST STEPS (compact trail): (none yet)\n\nCURRENT STATE:\n" + state_text
        else:
            text_block = state_text
        content.append({"type": "text", "text": text_block})

        # Build messages for the API call
        if self.mode == "stateless" or self.mode == "compact":
            # Compact mode uses one-shot calls just like stateless: the trail
            # lives in the user message itself, not in the conversation log.
            messages = [{"role": "user", "content": content}]
        else:
            # Conversational: append to history
            self._messages.append({"role": "user", "content": content})
            # Trim if too long
            if len(self._messages) > MAX_HISTORY_TURNS * 2:
                # Keep system context fresh: drop oldest turns but keep the first exchange
                self._messages = self._messages[:2] + self._messages[-(MAX_HISTORY_TURNS * 2 - 2):]
            messages = list(self._messages)

        # Provider call
        step_in_ep = self._exchange_step_counter
        started = _time.monotonic()
        try:
            response_text = self.provider.complete(
                messages=messages,
                system=self._system_prompt,
                should_cancel=self.should_cancel,
            ).strip()
            latency_ms = (_time.monotonic() - started) * 1000.0

            # In conversational mode, record the assistant reply
            if self.mode == "conversational":
                self._messages.append({"role": "assistant", "content": response_text})

            action = self._parse_action(response_text, observation)
            logger.info(f"LLM chose action {action} (raw: {response_text!r})")

            # In compact mode, stash the (slots, action, mana_before) snapshot
            # so on_step_result() can finalize a trail entry once it sees the
            # post-action mana.
            if self.mode == "compact":
                self._pending_trail = {
                    "step_idx": step_in_ep,
                    "slots": list(raw_state.get("slots", [])),
                    "action": action,
                    "mana_before": float(raw_state.get("mana", 0)),
                }

            if self.on_exchange is not None:
                try:
                    self.on_exchange(
                        user_text=text_block,
                        response=response_text,
                        action=action,
                        latency_ms=latency_ms,
                        error=None,
                        step_in_episode=step_in_ep,
                    )
                except Exception:  # pragma: no cover — never let tracing break a run
                    logger.exception("on_exchange callback raised; ignoring")

            self._exchange_step_counter += 1
            return action

        except Exception as e:
            # If the runner asked us to cancel, propagate immediately —
            # don't swallow it as a transient API error and play a fallback
            # action. The runner relies on this to abort cleanly.
            from ..providers.base import ProviderCancelled
            if isinstance(e, ProviderCancelled):
                raise
            latency_ms = (_time.monotonic() - started) * 1000.0
            logger.error(f"LLM provider error: {e}", exc_info=True)
            fallback = self._fallback_action(observation)
            # Surface the fallback to the runner so it can mark this step in
            # events.jsonl. Without this, crashed LLM calls are silently
            # indistinguishable from real model picks in offline logs.
            self._last_action_fallback_reason = f"llm_error: {e}"
            # Record the fallback into the pending trail too — otherwise the
            # next step would see a gap in the log.
            if self.mode == "compact":
                self._pending_trail = {
                    "step_idx": step_in_ep,
                    "slots": list(raw_state.get("slots", [])),
                    "action": fallback,
                    "mana_before": float(raw_state.get("mana", 0)),
                }
            if self.on_exchange is not None:
                try:
                    self.on_exchange(
                        user_text=text_block,
                        response="",
                        action=fallback,
                        latency_ms=latency_ms,
                        error=str(e),
                        step_in_episode=step_in_ep,
                    )
                except Exception:  # pragma: no cover
                    logger.exception("on_exchange callback raised; ignoring")
            self._exchange_step_counter += 1
            return fallback

    def on_step_result(self, action: int, reward: float, terminated: bool, info: dict):
        """Inject post-action feedback so future prompts know what happened.

        - Conversational mode: append a brief result note as a user message.
        - Compact mode: finalize the pending trail entry with the post-action
          mana and append it to the per-episode trail buffer.
        """
        raw_state = info.get("raw_state", {})
        mana = float(raw_state.get("mana", 0))

        if self.mode == "conversational":
            if not self._messages:
                return
            mana_max = raw_state.get("mana_max", 0)
            note = (
                f"[Result: action={action}, reward={reward:+.2f}, "
                f"mana={mana:.0f}, best={mana_max:.0f}]"
            )
            if self._messages and self._messages[-1]["role"] == "assistant":
                self._messages.append({"role": "user", "content": note})
            return

        if self.mode == "compact":
            pending = self._pending_trail
            if pending is None:
                return
            entry = format_trail_entry(
                step_idx=pending["step_idx"],
                slots_before=pending["slots"],
                action=pending["action"],
                mana_before=pending["mana_before"],
                mana_after=mana,
                hide_perceptual_attrs=self.use_screenshot,
            )
            self._compact_trail.append(entry)
            # Bound the trail so a long episode can't blow up the prompt.
            if len(self._compact_trail) > MAX_HISTORY_TURNS:
                # Keep the very first entry (often the most informative — the
                # opening hand) plus the most recent N-1.
                self._compact_trail = (
                    self._compact_trail[:1]
                    + self._compact_trail[-(MAX_HISTORY_TURNS - 1):]
                )
            self._pending_trail = None

    # -----------------------------------------------------------------
    # Parsing
    # -----------------------------------------------------------------

    @staticmethod
    def _parse_action(text: str, observation: dict) -> int:
        """Extract an action number from the LLM response, validating against the mask.

        Resolution order:
          1. Look for an explicit ``ACTION: N`` (or ``Action: N``) marker. This
             is the format we instruct the model to use, and it lets the model
             include reasoning above the line without the parser grabbing a
             stray slot index out of the prose.
          2. Otherwise scan the LAST line of the response for the first valid
             integer. The last line is usually where short replies put the
             answer; this avoids picking "slot 3" out of an explanation above.
          3. Otherwise scan the entire response for the first valid integer
             (legacy behaviour, kept so old terse responses still parse).
          4. Fallback: first valid action from the mask.
        """
        mask = observation.get("action_mask", None)

        def _is_valid(a: int) -> bool:
            return mask is not None and 0 <= a < len(mask) and mask[a] > 0

        # 1. Explicit ACTION: N marker (case-insensitive)
        marker = re.search(r"action\s*[:=]\s*(\d+)", text, re.IGNORECASE)
        if marker:
            action = int(marker.group(1))
            if _is_valid(action):
                return action

        # 2. Last non-empty line — most short answers put the integer there
        for line in reversed(text.strip().splitlines()):
            line = line.strip()
            if not line:
                continue
            for num_str in re.findall(r"\d+", line):
                action = int(num_str)
                if _is_valid(action):
                    return action
            break  # only check the LAST non-empty line for this stage

        # 3. Whole-response scan (legacy behaviour)
        for num_str in re.findall(r"\d+", text):
            action = int(num_str)
            if _is_valid(action):
                return action

        # 4. Fallback: first valid action from mask
        if mask is not None:
            valid = np.where(np.array(mask) > 0)[0]
            if len(valid) > 0:
                return int(valid[0])
        return 37  # WAIT

    @staticmethod
    def _fallback_action(observation: dict) -> int:
        mask = observation.get("action_mask", None)
        if mask is not None:
            valid = np.where(np.array(mask) > 0)[0]
            if len(valid) > 0:
                return int(valid[0])
        return 37

    @staticmethod
    def _encode_screenshot(screenshot: np.ndarray) -> str:
        from PIL import Image
        img = Image.fromarray(screenshot)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
