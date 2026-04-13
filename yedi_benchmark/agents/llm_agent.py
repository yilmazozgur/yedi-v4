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
# Each "turn" = 1 user + 1 assistant message.  Compact trail entries average
# ~120 chars each, so 30 entries ≈ 3.6K chars of history — keeps the total
# prompt under ~10K tokens even for smaller models (e.g. 20B on Together).
# The original 80-turn cap allowed context to grow to ~8K+ chars of trail,
# contributing to server-side timeouts on cost-sensitive inference endpoints.
MAX_HISTORY_TURNS = 30


# =====================================================================
# Prompt building
# =====================================================================

CORE_RULES = """\
You are playing YEDI, a brain-training card game. You DRAW cards, MERGE them
to grow their card_mana, then SELL merged cards to add that card_mana to your
total mana bank. Your SCORE is the PEAK total mana ("Best" / max mana) you
reach during the game. Maximise it.

Two scarce resources bound every decision:
  MANA BANK — starts ~200, drains slowly each step. Reaching 0 ends the game.
  MOVES     — fixed budget (typically 100). Every action spends one.
Wasted moves and bad merges BOTH cost score. Every action must have a reason.

============ BOARD & ACTIONS ============

Slots: [new] [1] [2] [3] [4] [5]  — "new" is the draw landing spot, 1..5 are
build slots. "new" must be EMPTY before you can draw again. The "sell" action
destroys a card and returns its card_mana to your bank (it is not a slot).

You output ONE integer 0..36 per turn:
   0         DRAW a new card into "new"  (cost ~10 × active_dims mana)
   1..30     MOVE src → dst — formula: 1 + src_idx*5 + (dst_idx - 1)
               src_idx: 0=new, 1..5=build slots ;  dst_idx: 1..5
               If dst is OCCUPIED → it MERGES. If dst is EMPTY → it just places.
               Examples: new→1=1, new→5=5, 1→2=7, 3→4=19, 5→1=26
   31..36    SELL — 31=sell new, 32..36=sell slots 1..5

Each turn's user message includes a "Valid actions:" list. Pick ONLY from that
list — the action mask rejects anything else.

============ MANA & SCORING ============

- DRAW costs ~10 mana per active dimension. It spawns a card in "new" with
  card_mana ≈ 0.9 × cost (9 for 1-dim, 36 for 4-dim). Selling a fresh card
  refunds ~90% of the draw cost.
- Your total mana bank drains slowly every step — holding cards costs mana.
- SELL is the ONLY way card_mana becomes score: it adds the card's current
  card_mana to your bank. If the new bank exceeds Best, Best goes up.
- Score = peak Best across the whole episode. You do NOT need to END with
  high mana; you need to PEAK high at some point.

============ MERGES — HOW CARDS GROW ============

When you move a card onto an OCCUPIED slot, they MERGE. For EACH active
dimension, the target's card_mana is multiplied by a tier coefficient:

   2.5×  PERFECT  — both cards are the dimension's NEUTRAL (identity) card
   2.0×  GREAT    — the merge RESOLVES TO neutral (e.g. 3+(-3)=0, Y+C=White)
   1.5×  GOOD     — a positive step toward neutral (e.g. Red+Green=Yellow)
   1.0×  neutral  — no change
   0.9×  BAD      — DEGRADES card_mana (you lose mana)

Multi-dim merges STACK: each active dim's multiplier hits sequentially.

   1 dim PERFECT:          9 × 2.5                   =   22
   3 dims ALL GREAT:       9 × 2.0 × 2.0 × 2.0       =   72
   3 dims ALL PERFECT:     9 × 2.5 × 2.5 × 2.5       =  141
   4 dims ALL PERFECT:    36 × 2.5 × 2.5 × 2.5 × 2.5 = 1406   ← jackpot
   3 dims 2 GREAT + 1 BAD: 9 × 2.0 × 2.0 × 0.9       =   32

ONE BAD dim wrecks a multi-dim merge. Evaluate every candidate by its MIN
multiplier across active dims — never the average. Pick the candidate with
the highest minimum. A merge that is 2.5× in math but 0.9× in colour is a
0.9-bounded merge, not a "mostly great" one.

HARD LIMIT: each card refuses further merges after 3. A 3-merge card is
done — no more growth — and should be SOLD next turn to free the slot.

============ NEUTRAL CARDS ============

Every dimension has a NEUTRAL identity card:

   math:add      → value 0           color:add/gray → White
   math:multiply → value 1           color:subtract → Black
   math:gcd      → value 1           color:text     → White (ink)

   shape:triangle/rectangle/kanizsa/triple → index 7 (empty-set symbol)
   shape:hanoi   → index 9 (solved state)
   shape:sphere  → index 0 (neutral angle)

   word:* (except scrabble) → "nihil" (all word-pairs cancelled)

NOTE: shape identity ≠ blank/reset. Index 8 (or 10/16) is the BLANK that
resets a slot for free (1.0×). Index 7 (or 0/9) is the TRUE IDENTITY that
gives 2.5× PERFECT when paired with another identity.

Neutral cards rarely spawn from a vanilla draw. The usual path to one is a
GREAT merge that RESOLVES to neutral (3+(-3)=0, Yellow+Cyan=White,
appear+vanish→nihil, opposite shapes→identity). Once you
hold two neutrals AT THE SAME TIME in DIFFERENT slots, pairing them gives
the 2.5× PERFECT jackpot. This is why you must build multiple slots in
parallel — you cannot pair two neutrals if you only use slot 1.

Strategy: drive slots up to neutral via GREAT merges, then chain
neutral+neutral pairs for PERFECT merges. Each PERFECT multiplies card_mana
by 2.5×, so value grows exponentially.

============ DECISION PRIORITY (when "new" is occupied) ============

Ranked best-to-worst:
   A. MERGE "new" into a slot where EVERY active dim scores ≥1.5×
      (this is the only merge that actually compounds score)
   B. PLACE "new" into an EMPTY build slot
      (preserves card_mana and keeps future merge options open)
   C. SELL "new"
      (recovers ~90% of draw cost — strictly better than option D)
   D. FORCE a bad merge into a built slot
      (NEVER — destroys both the new card AND the slot you built up)

Option D looks like "making progress" but is strictly worse than C. Selling
the new card loses the 10% draw overhead; a bad merge loses the full card
AND degrades a slot.

Never move a card slot→slot (actions 6..30) unless it triggers a ≥1.5× merge
on every active dim. Unproductive board shuffles incur a FLAT 5-mana penalty
on your bank in addition to burning a move and the drain tick.

============ TURN CHECKLIST ============

Read the SLOT SUMMARY and "Valid actions:" list every turn — state changes
every step, memory of prior turns is unreliable. Then:

  1. Any build slot at 3 merges? → SELL it (actions 32..36). Do this FIRST.
  2. Is "new" occupied?
       a. Compute the MIN multiplier across active dims for each candidate
          new→{1..5} merge. Pick the candidate with the highest minimum.
       b. If that minimum ≥ 1.5× → MOVE new → that slot.
       c. Else if an empty build slot exists → MOVE new → empty slot.
       d. Else → SELL new (action 31).
  3. "new" empty and no 3-merge slot to sell? → DRAW (action 0).

============ COMMON MISTAKES ============

  1. Single-slot fixation: merging everything into slot 1 caps it at 3 merges
     and wastes slots 2..5. Spread builds across all five slots.
  2. Forcing bad merges: 0.9× degrades card_mana. Strictly worse than placing
     into an empty slot or selling the new card.
  3. Hoarding finished cards: a 3-merge card sitting in a slot just drains
     your bank. Sell it and free the slot.
  4. Drawing without a plan: each draw costs mana AND a move. Only draw when
     "new" is empty and you have a placement strategy ready.
  5. Averaging multi-dim multipliers: the WORST dim bounds the outcome. One
     BAD dim kills a multi-dim merge, no matter how good the others are.
  6. Slot-to-slot shuffles: moving between build slots without triggering a
     merge burns a move AND costs a flat 5-mana bank penalty.\
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
Cards show integers (e.g. -5, -2, 0, 3, 7), shown as "Num=N" in metadata.
A merge ADDS: result = slot_value + new_value. NEUTRAL = 0.

SCORING (preview tiers, as they appear in merge_previews):
  slot=0 AND new=0        → 2.5x PERFECT (both neutral)
  sum=0 (opposite signs)  → 2.0x GREAT   (slot becomes neutral)
  |sum|=1                 → 1.5x GOOD
  |sum|=2                 → 1.0x neutral
  |sum|≥3                 → 0.9x BAD
  slot=0, new≠0           → 0.9x BAD — wasted the neutral
  slot≠0, new=0           → no mult; slot is RESET to 0 (free slot fix)

STRATEGY:
  - Aim for sum=0 (opposite-sign pairing) — the workhorse ×2.0.
  - HOLD 0-cards as targets for ×2.5 pairings with other 0-cards.
  - Never merge a non-zero card INTO a 0 slot (×0.9).
  - Use the "new=0 resets slot" rule to rescue a bad slot for free.\
""",
    ("number", "multiply"): """\
==== MATH — MULTIPLY MODE ====
Cards show integers or fractions (e.g. 1/4, 1/3, 0.5, 1, 2, 3, 4).
A merge MULTIPLIES: result = slot × new. IDENTITY = 1.

SCORING:
  slot=1 AND new=1        → 2.5x PERFECT
  product=1 (reciprocals) → 2.0x GREAT (2×0.5, 3×1/3, 4×0.25)
  product close to 1      → 1.5x GOOD
  product a bit off 1     → 1.0x neutral
  product far from 1      → 0.9x BAD
  slot=1, new≠1           → 0.9x BAD — wasted the identity
  slot≠1, new=1           → resets slot to 1 (free slot fix)

STRATEGY:
  - Hunt RECIPROCAL pairs for ×2.0: 2×0.5, 3×1/3, 4×0.25, 5×0.2.
  - HOLD 1-cards as targets for ×2.5 pairings.
  - Avoid merges that push the product far from 1.\
""",
    ("number", "gcd"): """\
==== MATH — GCD MODE ====
Cards show positive integers (1-12). Merge = GCD(slot, new). IDENTITY = 1.

SCORING:
  slot=1 AND new=1        → 2.5x PERFECT
  GCD = 1 (coprime)       → 2.0x GREAT, slot → 1
  GCD > 1 (shared factor) → 0.9x BAD,   slot → the GCD
  slot=1, new≠1           → 0.9x BAD — wasted identity
  slot≠1, new=1           → resets slot to 1 (free slot fix)

STRATEGY:
  - Merge COPRIME pairs (no shared factor). Easy wins: primes (2,3,5,7,11)
    pair with anything not a multiple; adjacent integers (3+4, 5+6, 8+9)
    are always coprime.
  - AVOID shared-factor pairs: 4+6, 6+9, 8+12, 4+8, 9+12.
  - Once a slot reaches 1, keep chaining coprimes for repeated ×2.0.\
""",
    ("number", "trigon"): """\
==== MATH — TRIGON MODE ====
Cards show angles (multiples of 15° or 30°). IDENTITY = 0°.
Complementary pairs (sum to 90°) and supplementary pairs (sum to 180°)
are the high-multiplier merges.

SCORING (approximate — rely on merge_previews):
  Both 0°                          → 2.5x PERFECT
  Sum to 90° or 180°               → 2.0x GREAT
  Near-complementary / acute       → 1.5x GOOD
  Same angle / extreme pairs       → 0.9x BAD

STRATEGY: hunt sum=90° (30+60, 45+45, 0+90) or sum=180° (60+120, 30+150).\
""",
    ("number", "vector"): """\
==== MATH — VECTOR MODE ====
Cards are integers 1-8 encoding 2D direction vectors (45° steps):
  1=↑ 2=↗ 3=→ 4=↘ 5=↓ 6=↙ 7=← 8=↖    IDENTITY = 0.

SCORING:
  Both 0                  → 2.5x PERFECT
  Opposite (sum vector=0) → 2.0x GREAT — pairs 1+5, 2+6, 3+7, 4+8
  Perpendicular           → 1.5x GOOD  — e.g. 1+3, 3+5, 5+7, 7+1
  Adjacent directions     → 1.0x neutral
  Same direction          → 0.9x BAD
  slot=0, new≠0           → 0.9x BAD
  slot≠0, new=0           → resets slot to 0

STRATEGY: pair opposites (1+5, 2+6, 3+7, 4+8) for ×2.0.\
""",
    ("number", "interval"): """\
==== MATH — INTERVAL MODE ====
Cards are integers 1-9 (semitone intervals). Scoring = consonance.

SCORING (approximate):
  Both 0                         → 2.5x PERFECT
  Consonant (octave, perfect 5)  → 2.0x GREAT — differ by 7 or 12
  3rd, 6th                       → 1.5x GOOD
  Dissonant (adjacent, 2nd/7th)  → 0.9x BAD — e.g. 1+2, 2+3

STRATEGY: pair numbers differing by 7 (perfect 5th) or 12 (octave).\
""",
    ("number", "sort"): """\
==== MATH — SORT MODE ====
Place cards so values increase left-to-right across slots 1..5.
Merging is NOT the goal here — PLACEMENT is. Sell out-of-order cards.\
""",
    # =================================================================
    # VISUAL (color)
    # =================================================================
    ("color", "add"): """\
==== VISUAL — ADD MODE (additive RGB) ====
Cards are one of 7 colours, shown as "Color=Red" etc:
  PRIMARIES: Red, Green, Blue
  MIXES:     Yellow=R+G, Cyan=G+B, Magenta=R+B
  IDENTITY:  White (R+G+B)

A mix "contains" its two primaries. Each primary's COMPLEMENT is the mix
that does NOT contain it:  Red↔Cyan, Green↔Magenta, Blue↔Yellow.

SCORING:
  Both White                                → 2.5x PERFECT
  Two different mixes (Y+C, Y+M, C+M)       → 2.0x GREAT (→ slot White)
  Primary + its complement mix
    (R+Cyan, G+Magenta, B+Yellow)           → 2.0x GREAT (→ slot White)
  Two different primaries (R+G, R+B, G+B)   → 1.5x GOOD  (→ slot is the mix)
  Same colour                               → 0.9x BAD
  White + non-White                         → 0.9x BAD (wasted identity)
  Primary + mix containing it
    (R+Y, R+M, G+Y, G+C, B+M, B+C)          → 0.9x BAD
  non-White slot + White new                → resets slot to White (free fix)

STRATEGY:
  - MEMORISE complements: Red↔Cyan, Green↔Magenta, Blue↔Yellow.
  - Best merges (×2.0) also turn the slot White — perfect ×2.5 setup.
  - HOLD White cards for ×2.5 White+White.
  - Never merge a primary into a mix containing it (×0.9).\
""",
    ("color", "subtract"): """\
==== VISUAL — SUBTRACT MODE (subtractive CMY) ====
Same structure as Add mode with SWAPPED roles:
  PRIMARIES: Cyan, Magenta, Yellow
  MIXES:     Blue=C+M, Red=M+Y, Green=C+Y
  IDENTITY:  Black
  COMPLEMENTS: Cyan↔Red, Magenta↔Green, Yellow↔Blue

Scoring table is IDENTICAL to Add mode — just apply it with the swapped
identities. Two different mixes (R+G, R+B, G+B) or primary+complement
(C+Red, M+Green, Y+Blue) hit ×2.0 and turn the slot Black.\
""",
    ("color", "gray"): """\
==== VISUAL — GRAY MODE ====
Cards have a gray index 1-9 (1=darkest, 9=lightest), shown as "Gray=N".
IDENTITY = White.

SCORING:
  Both White                                   → 2.5x PERFECT
  Slot lighter than new (slot_idx > new_idx):
    sum > 9                                    → 2.0x GREAT (→ slot White)
    sum ≤ 9                                    → 1.5x GOOD  (→ slot idx=sum)
  Slot darker or equal to new                  → 0.9x BAD
  Same gray index                              → 0.9x BAD
  White + non-White                            → 0.9x BAD (wasted identity)
  non-White slot + White new                   → resets slot to White (free fix)

STRATEGY:
  - Always merge DARKER cards INTO LIGHTER slots (slot_idx > new_idx).
  - HOLD the lightest grays (Gray=8/9) as targets — nearly anything merged
    in satisfies "slot lighter" AND tips sum past 9 for ×2.0.
  - Never merge equal-gray cards (×0.9).\
""",
    ("color", "text"): """\
==== VISUAL — TEXT MODE (Stroop effect) ====
Cards show a colour NAME printed in a DIFFERENT ink colour. Merge logic uses
the INK colour — IGNORE the printed word.

In METADATA mode you see RGB values (the ink). Apply the Add-mode scoring
table unchanged. In SCREENSHOT mode, read the ink, resist the word — this
is the classic Stroop conflict.\
""",
    # =================================================================
    # SPATIAL (shape)
    # =================================================================
    ("shape", "triangle"): """\
==== SPATIAL — TRIANGLE MODE ====
Cards show triangles in 8 orientations (index 0-7, rotating 45° per step).
Two special indices: 7 = identity (empty-set symbol), 8 = blank/reset.
Shown as "Shape=N".

SCORING:
  Both identity (7)                      → 2.5x PERFECT
  Opposite (idx differ by 4)             → 2.0x GREAT — 0+4, 1+5, 2+6, 3+7
                                           (slot becomes identity 7 after merge)
  Perpendicular (idx differ by 2 or 6)   → 1.5x GOOD
  Adjacent orientations                  → 1.0x neutral
  Same orientation                       → 0.9x BAD
  Identity(7) slot + non-identity        → 0.9x BAD (wasted identity)
  Non-identity slot + blank(8)           → resets slot to blank (1.0x, free fix)

Identity 7 never spawns from a draw. The path to it: merge OPPOSITES (4
apart) for ×2.0 GREAT — the slot becomes identity 7. Then pair two
identity-7 cards for ×2.5 PERFECT.

STRATEGY: pair OPPOSITES (4 apart) for ×2.0 → creates identity 7 →
hold identity-7 cards for ×2.5 PERFECT pairings.\
""",
    ("shape", "rectangle"): """\
==== SPATIAL — RECTANGLE MODE ====
Rectangles in 8 orientations (0-7). Identity = index 7 (empty-set symbol),
blank/reset = index 8. Same scoring as Triangle mode — pair orientations
4 apart for ×2.0 GREAT (slot becomes identity 7), then pair identity-7
cards for ×2.5 PERFECT.\
""",
    ("shape", "kanizsa"): """\
==== SPATIAL — KANIZSA MODE ====
Cards show Kanizsa illusory-contour patterns in 8 orientations (0-7).
Identity = index 7 (empty-set symbol), blank/reset = index 8. Key VLM
test: the contour must be PERCEIVED from the pacman-cutout inducers.

Merge scoring identical to Triangle mode — pair orientations 4 apart
for ×2.0 GREAT (slot → identity 7), then pair identity-7 cards for
×2.5 PERFECT. In metadata mode you see Shape=N directly.\
""",
    ("shape", "hanoi"): """\
==== SPATIAL — HANOI MODE ====
Cards represent Tower of Hanoi disc states (index 0-15). Identity = index 9
(solved state), blank/reset = index 16. One of the hardest modes — merges
represent Hanoi moves. Valid moves score well, invalid ones don't.

SCORING:
  Both identity (9)                      → 2.5x PERFECT
  Valid Hanoi move                       → 2.0x GREAT (slot → identity 9)
  Identity(9) slot + non-identity        → 0.9x BAD (wasted identity)
  Non-identity slot + blank(16)          → resets slot (1.0x, free fix)

STRATEGY: pair valid Hanoi moves for ×2.0 → creates identity 9 → then
pair identity-9 cards for ×2.5 PERFECT. Sell unclear cards rather than
gamble a bad merge.\
""",
    ("shape", "triple"): """\
==== SPATIAL — TRIPLE MODE ====
Cards show three overlapping shapes in 8 orientations (0-7). Identity =
index 7 (empty-set symbol), blank/reset = index 8. Merges combine
patterns — opposite orientations (4 apart) give ×2.0 GREAT and produce
identity 7. Same scoring as Triangle mode.

STRATEGY: pair opposites (4 apart) for ×2.0 → identity 7 → pair
identity-7 cards for ×2.5 PERFECT. Sell unclear cards early.\
""",
    ("shape", "sphere"): """\
==== SPATIAL — SPHERE MODE ====
Cards show 3D sphere angle positions. Identity = index 0 (neutral angle),
blank/reset = index 10. Opposing/symmetric positions merge best.

SCORING:
  Both identity (0)                      → 2.5x PERFECT
  Opposing position                      → 2.0x GREAT (slot → identity 0)
  Identity(0) slot + non-identity        → 0.9x BAD (wasted identity)
  Non-identity slot + blank(10)          → resets slot (1.0x, free fix)

STRATEGY: pair opposing positions for ×2.0 → identity 0 → pair
identity-0 cards for ×2.5 PERFECT.\
""",
    # =================================================================
    # VERBAL (word)
    # =================================================================
    ("word", "verbs"): """\
==== VERBAL — VERBS MODE ====
Cards show 1-2 verbs from a FIXED list of 7 ANTONYM pairs, as "Word=[verb]".
IDENTITY = "nihil" (shown when all words have been cancelled).

THE 7 PAIRS (memorise these — they are the ONLY words in the game):
  appear↔vanish, contract↔expand, fail↔succeed, help↔hinder,
  separate↔join, build↔destroy, conceal↔reveal

HOW WORD CARDS WORK:
  - Each card holds a LIST of 1-2 words (shown stacked on the card).
  - Merging checks each incoming word against the target card's list:
      • ANTONYM PAIR found → the matched word is REMOVED from the target,
        ×2.0 GREAT per pair removed.
      • IDENTICAL word → ×0.9 BAD (duplicate penalty).
      • NO MATCH → incoming word is ADDED to the target's list (max 2).
  - When ALL words are removed from a card → "nihil" is added (identity).

SCORING:
  nihil + nihil                      → 2.5x PERFECT
  1 antonym pair matched             → 2.0x GREAT (matched word removed)
  2 antonym pairs matched            → 2.5x+ PERFECT (2.0×2.0)
  No match (word added to list)      → 1.0x neutral
  Identical word                     → 0.9x BAD
  nihil slot + non-nihil new         → 0.9x BAD (wasted identity)
  non-nihil slot + nihil new         → slot becomes nihil (1.0x, free fix)

STRATEGY:
  - Merge ANTONYM pairs to cancel words: appear→vanish, fail→succeed, etc.
  - The goal is to reach "nihil" (all words cancelled), then pair nihils
    for ×2.5 PERFECT — same pattern as reaching 0 in math:add.
  - HOLD nihil cards for ×2.5 pairings. Never merge non-nihil into nihil.
  - If no antonym match exists, PLACE into an empty slot or SELL.\
""",
    ("word", "nouns"): """\
==== VERBAL — NOUNS MODE ====
Same mechanics as verbs mode (1-2 word cards, pair removal, nihil identity).
7 ANTONYM NOUN PAIRS:
  despair↔hope, past↔present, poverty↔wealth, success↔failure,
  virtue↔vice, war↔peace, bless↔curse

Merge antonym pairs to cancel words → reach nihil → pair nihils for ×2.5.\
""",
    ("word", "adjectives"): """\
==== VERBAL — ADJECTIVES MODE ====
Same mechanics as verbs mode (1-2 word cards, pair removal, nihil identity).
7 ANTONYM ADJECTIVE PAIRS:
  empty↔full, messy↔neat, boring↔fun, young↔old,
  private↔public, quiet↔loud, sweet↔sour

Merge antonym pairs to cancel words → reach nihil → pair nihils for ×2.5.\
""",
    ("word", "synVerbs"): """\
==== VERBAL — SYNONYM VERBS MODE ====
Same mechanics as verbs mode (1-2 word cards, pair removal, nihil identity),
but pairs are SYNONYMS instead of antonyms.
7 SYNONYM VERB PAIRS:
  choose↔select, close↔shut, refuse↔reject, collect↔gather,
  defend↔protect, forbid↔ban, begin↔start

Merge synonym pairs to cancel words → reach nihil → pair nihils for ×2.5.\
""",
    ("word", "synAdjectives"): """\
==== VERBAL — SYNONYM ADJECTIVES MODE ====
Same mechanics as verbs mode (1-2 word cards, pair removal, nihil identity),
but pairs are SYNONYMS.
7 SYNONYM ADJECTIVE PAIRS:
  happy↔amused, little↔tiny, good↔terrific, bad↔awful,
  pretty↔handsome, angry↔annoyed, mad↔crazy

Merge synonym pairs to cancel words → reach nihil → pair nihils for ×2.5.\
""",
    ("word", "grammar"): """\
==== VERBAL — GRAMMAR MODE ====
Same mechanics as verbs mode (1-2 word cards, pair removal, nihil identity),
but pairs are GRAMMATICAL CONSTRUCTIONS that belong together.
7 GRAMMAR PAIRS:
  I↔am, you↔are, she↔is, to↔be,
  either↔or, neither↔nor, not only↔but also

Merge paired grammar words to cancel them → reach nihil → pair nihils
for ×2.5. Note: "not only" and "but also" are multi-word tokens.\
""",
    ("word", "questions"): """\
==== VERBAL — QUESTIONS MODE ====
Same mechanics as verbs mode (1-2 word cards, pair removal, nihil identity),
but pairs are QUESTION WORDS matched with their ANSWER WORDS.
7 QUESTION-ANSWER PAIRS:
  what↔this, where↔here, when↔now, why↔because,
  who↔she, whom↔her, how often↔rarely

Merge question↔answer pairs to cancel them → reach nihil → pair nihils
for ×2.5. Note: "how often" is a multi-word token.\
""",
    ("word", "scrabble"): """\
==== VERBAL — SCRABBLE MODE ====
Each card has a single LETTER, shown as "Word=[A]". Merging CONCATENATES.
A real English word scores by length.

SCORING:
  4+ letter valid word        → 2.5x PERFECT
  3-letter valid word         → 2.0x GREAT
  2-letter valid word         → 1.5x GOOD
  Not a valid word            → 1.0x neutral (not negative)

ORDER: the new letter is PREPENDED to the slot's string.
  slot "AT" + new "C" → slot becomes "CAT" → ×2.0.
  slot "CAT" + new "S" → slot becomes "SCAT" → ×2.5.

STRATEGY:
  - Build SHORT valid words first (CAT, DOG, RUN) before chasing length.
  - Common 2-letter: AT, IT, IS, ON, IN, OR, AS, TO, OF, BE, GO, NO, SO.
  - Common 3-letter: CAT, DOG, RUN, SUN, RED, BIG, EAT, BOY, EYE.
  - Vowels are precious — hold them. Plan TWO letters ahead.\
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
    show_merge_previews: bool = False,
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

    `show_merge_previews` adds instructions about the merge preview block
    that appears in each turn's state dump when the ablation is enabled.
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

    if show_merge_previews:
        parts.append(_MERGE_PREVIEW_INSTRUCTIONS)

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

    # Which dimensions are actually active this episode. Gates per-slot
    # attribute rendering below so we never leak e.g. Shape=8 or Color=Clear
    # into a pure Number episode — small models took those ghost fields at
    # face value and wasted reasoning on dimensions the game wasn't scoring.
    mode_active = {
        dim: bool(raw_state.get(key))
        for dim, key in _MODE_FIELD_MAP.items()
    }

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
        if mode_active["number"]:
            num_val = slot.get("number_value", 0)
            attrs.append(f"Num={num_val:.1f}")

        # Color
        if mode_active["color"]:
            cr = slot.get("color_r", 0)
            cg = slot.get("color_g", 0)
            cb = slot.get("color_b", 0)
            gray_idx = slot.get("color_index_gray", 0)
            if cr > 0 or cg > 0 or cb > 0:
                attrs.append(f"Color={_color_name(cr, cg, cb)}")
            if gray_idx > 0:
                attrs.append(f"Gray={gray_idx}")

        # Shape
        if mode_active["shape"]:
            shape_idx = slot.get("shape_index", -1)
            if shape_idx >= 0:
                attrs.append(f"Shape={shape_idx}")

        # Word — filter empty-string ghosts that can appear due to a
        # WebGL initialisation race (serialised as leading/trailing commas).
        if mode_active["word"]:
            raw_word = slot.get("word_value", "")
            word_val = ",".join(w for w in raw_word.split(",") if w)
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


def _compact_slot(
    slot: dict,
    hide_perceptual_attrs: bool = False,
    active_dims: Optional[set] = None,
) -> str:
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
        # Dimensions the episode isn't scoring stay out of the trail so
        # small models don't waste tokens reasoning about ghost attrs.
        # When `active_dims` is None we fall back to the old value-gated
        # rendering for backward compat with callers that don't know the
        # mode set (tests, ad-hoc debugging).
        legacy = active_dims is None
        # Number
        if legacy or "number" in active_dims:
            num_val = slot.get("number_value", 0.0)
            if legacy and not (slot.get("number_active", False) or abs(num_val) > 0.01):
                pass
            else:
                if abs(num_val - round(num_val)) < 0.01:
                    parts.append(f"{int(round(num_val)):+d}")
                else:
                    parts.append(f"{num_val:+.1f}")
        # Color (single letter)
        if legacy or "color" in active_dims:
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
        if legacy or "shape" in active_dims:
            shape_idx = slot.get("shape_index", -1)
            if shape_idx >= 0:
                parts.append(f"s{shape_idx}")
        # Word (bracketed) — filter empty-string ghosts
        if legacy or "word" in active_dims:
            raw_word = slot.get("word_value", "")
            word_val = ",".join(w for w in raw_word.split(",") if w)
            if word_val:
                parts.append(f"[{word_val}]")

    parts.append(f"m{slot.get('card_mana', 0):.0f}")
    parts.append(f"x{slot.get('merges_done', 0)}")
    return ",".join(parts)


def _compact_slots_row(
    slots: list,
    hide_perceptual_attrs: bool = False,
    active_dims: Optional[set] = None,
) -> str:
    """Render the row [new|s1|s2|s3|s4|s5] for one step.

    The first 6 entries of `slots` correspond to [new, 1, 2, 3, 4, 5]; any
    extra trailing entry (e.g. the "sell" pseudo-slot the bridge sometimes
    appends) is ignored.
    """
    if not slots:
        return "|".join(["."] * 6)
    cells = [
        _compact_slot(
            slots[i],
            hide_perceptual_attrs=hide_perceptual_attrs,
            active_dims=active_dims,
        )
        if i < len(slots) else "."
        for i in range(6)
    ]
    return "|".join(cells)


def _annotate_action(action: int) -> str:
    """Short, parseable annotation: 'a7:new>s1', 'a0:draw', 'a32:sell(s1)'."""
    slot_short = ["new", "s1", "s2", "s3", "s4", "s5"]
    if action == 0:
        return "a0:draw"
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
    active_dims: Optional[set] = None,
) -> str:
    """One trail line for the compact history block.

    Layout:
        tN [new|s1|s2|s3|s4|s5] aA:annotation -> mAFTER(±DELTA)

    ``hide_perceptual_attrs`` strips per-dimension tokens inside each cell
    (vision-mode trail). See :func:`_compact_slot` for the cell format.
    ``active_dims`` gates per-dimension tokens to the dims the episode is
    actually scoring; None keeps the legacy value-based gating for tests.
    """
    row = _compact_slots_row(
        slots_before,
        hide_perceptual_attrs=hide_perceptual_attrs,
        active_dims=active_dims,
    )
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

Use the trail as your action-and-mana scratchpad; use the CURRENT STATE
screenshot as the authoritative source for what each slot actually holds
right now.\
"""


_MERGE_PREVIEW_INSTRUCTIONS = """\
============ MERGE PREVIEWS — PRE-COMPUTED, AUTHORITATIVE ============

Each turn's state dump includes a "Merge previews" block listing EVERY legal
merge candidate with its exact tier and multiplier PER ACTIVE DIMENSION. These
are computed by the game engine — they are ALWAYS CORRECT.

Format:
  a<ACTION>  <src>→<dst>: <Dim> <TIER> ×<mult>[, <Dim2> <TIER2> ×<mult2>, ...]

Example:
  a1   new→1: Number GREAT ×2.0
  a2   new→2: Number BAD ×0.9

CRITICAL: DO NOT try to compute merge quality yourself from the card values.
The merge previews are the ground truth — trust them. When previews are shown,
your decision process is:

  1. Read the "Merge previews" block.
  2. Find the candidate with the HIGHEST MINIMUM multiplier across all dims.
  3. If that minimum is ≥1.5× → take that merge.
  4. If no merge is ≥1.5× → place into an empty slot or sell.

The previews already account for all dimension rules, special cases, and
edge conditions. Using them saves you from arithmetic errors and is strictly
more reliable than mental computation.\
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
            show_merge_previews=show_merge_previews,
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
            show_merge_previews=self.show_merge_previews,
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
                    "active_dims": {
                        dim for dim, key in _MODE_FIELD_MAP.items()
                        if raw_state.get(key)
                    },
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
                    "active_dims": {
                        dim for dim, key in _MODE_FIELD_MAP.items()
                        if raw_state.get(key)
                    },
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
                active_dims=pending.get("active_dims"),
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
        return 0  # DRAW

    @staticmethod
    def _fallback_action(observation: dict) -> int:
        # When the LLM errors or returns nonsense, fall back to the first
        # valid action from the mask (usually DRAW). DRAW is almost always
        # valid and is the least destructive default.
        mask = observation.get("action_mask", None)
        if mask is not None:
            valid = np.where(np.array(mask) > 0)[0]
            if len(valid) > 0:
                return int(valid[0])
        return 0  # DRAW

    @staticmethod
    def _encode_screenshot(screenshot: np.ndarray) -> str:
        from PIL import Image
        img = Image.fromarray(screenshot)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
