"""
LLM Agent — uses Claude (or compatible API) to play Yedi via metadata and/or screenshots.

Supports four evaluation modes:
  - metadata + stateless  (Mode A): one API call per step, text-only, no history
  - metadata + conversational (Mode B): rolling conversation within an episode, text-only
  - screenshot + stateless  (Mode A): one API call per step, screenshot + text
  - screenshot + conversational (Mode B): rolling conversation, screenshot + text

Usage:
    # Metadata-only, stateless
    python -m yedi_benchmark.benchmark_runner --agent claude-meta-a --configs EASY --episodes 3
    # Metadata-only, conversational
    python -m yedi_benchmark.benchmark_runner --agent claude-meta-b --configs EASY --episodes 3
    # Screenshot, stateless
    python -m yedi_benchmark.benchmark_runner --agent claude-vision-a --configs EASY --episodes 3
    # Screenshot, conversational
    python -m yedi_benchmark.benchmark_runner --agent claude-vision-b --configs EASY --episodes 3
"""

import base64
import io
import logging
import os
import re
from pathlib import Path

import numpy as np
from .base_agent import BaseAgent

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
You are playing YEDI, a brain training card game.

OBJECTIVE
  Maximise your mana score.  The game tracks your peak mana ("max mana") as the score.

BOARD
  - 5 numbered slots (1-5) plus a "new" draw slot.
  - Each card has a mana value and attributes in one or more dimensions.

ACTIONS (you will pick a number)
  0  = Draw a new card (costs mana, card appears in "new" slot)
  1-30 = Move/Merge a card from one slot to another
  31-36 = Sell a card (its card_mana is added to your total mana)
  37 = Wait (do nothing)

MERGE MECHANICS
  Moving a card onto an occupied slot MERGES them.
  Each active dimension is scored independently:
    +3  perfect merge (both at identity value)
    +2  great merge
    +1  good merge
     0  neutral
    -1  bad merge (penalises card mana)
  The merged card stays in the target slot with updated dimension values.
  A card with many merges accumulates high mana — sell it to cash in.

GAME FLOW
  Draw → build cards via merges → sell high-value cards → repeat.
  Mana drains each step.  Game ends when step limit is reached.

STRATEGY PRINCIPLES
  - Each merge should be positive in ALL active dimensions if possible.
  - Build up a card with several good merges, then sell it for a big mana boost.
  - Don't hoard cards.  If a card can't merge well, sell it early.
  - An empty slot has value — it lets you place cards without forced bad merges.
  - When the "new" slot has a card, you must deal with it before drawing again.\
"""

# Per-dimension merge rules, keyed by (dimension_field, mode_value)
DIMENSION_RULES = {
    ("number", "add"): """\
MATH — Add mode
  Cards have integer values (e.g. -3, 0, 2, 5).
  Merge: values ADD together (result = slot_value + incoming_value).
  Scoring:
    Both 0 → +3 (perfect).  Sum = 0 → +2 (great: e.g. 3 + -3).
    |sum| ≤ 3 → +1.  |sum| > 3 → -1.
  Identity value: 0.  Merge towards zero.\
""",
    ("number", "multiply"): """\
MATH — Multiply mode
  Cards have fractional values.
  Merge: values MULTIPLY (result = slot_value × incoming_value).
  Scoring:
    Both 1 → +3.  Product = 1 → +2 (reciprocals: e.g. 2 × 0.5).
    Product close to 1 → +1.  Far from 1 → -1.
  Identity value: 1.  Merge towards one.\
""",
    ("number", "gcd"): """\
MATH — GCD mode
  Cards have positive integers.
  Merge: the GCD of the two numbers is evaluated.
  Scoring:
    Both 1 → +3.  GCD = 1 (coprime) → +2.  GCD > 1 (share factors) → -1.
  Strategy: merge numbers that share NO common factors.\
""",
    ("number", "vector"): """\
MATH — Vector mode
  Cards have integers 1-8 representing 2D direction vectors.
  Merge: pair scoring is based on vector orthogonality / alignment.
  Scoring:
    Both 0 → +3.  Perpendicular pairs → +2.  Adjacent → +1/0.  Parallel → -1.
  Strategy: merge vectors that are perpendicular (e.g. 1↔4, 2↔5, 3↔6).\
""",
    ("number", "interval"): """\
MATH — Interval mode
  Cards have integers 1-9 representing musical intervals.
  Merge: pair scoring based on consonance/dissonance.
  Scoring:
    Both 0 → +3.  Consonant intervals (e.g. octave, fifth) → +2.
    Mildly consonant → +1.  Dissonant (close numbers) → -1.
  Strategy: merge numbers that are far apart (large intervals).\
""",
    ("number", "trigon"): """\
MATH — Trigon mode
  Cards have angle values.
  Merge: trigonometric relationship between angles is scored.
  Scoring follows complementary angle logic.
  Strategy: look for complementary or supplementary angle pairs.\
""",
    ("number", "sort"): """\
MATH — Sort mode
  Cards have numbers that must be arranged in order.
  Strategy: place cards so numbers increase left-to-right across slots.\
""",
    ("color", "add"): """\
VISUAL — Add mode (RGB additive colour mixing)
  Cards have one of 6 colours:  Red, Green, Blue (primaries)
                                 Yellow, Cyan, Magenta (mixes)
  Plus White (identity/null colour).
  Merge rules:
    Both White → +3.  Same colour → -1.
    Two DIFFERENT mixes (Y+C, Y+M, C+M) → +2.
    Primary + its COMPLEMENT → +2 (Red+Cyan, Green+Magenta, Blue+Yellow).
    Two different primaries (R+G, R+B, G+B) → +1.
    Primary + mix that CONTAINS it → -1 (e.g. Red+Yellow, Red+Magenta).
  Strategy: merge different mixes together, or primary with its complement.\
""",
    ("color", "subtract"): """\
VISUAL — Subtract mode (CMY subtractive colour mixing)
  Cards have: Cyan, Magenta, Yellow (primaries), Red, Green, Blue (mixes).
  Plus Black (identity/null colour).
  Same pairing logic as Add mode but with swapped primary/mix roles.
  Strategy: merge different mixes, or primary with complement.\
""",
    ("color", "gray"): """\
VISUAL — Gray mode
  Cards have a gray level index 1-9 (1=darkest, 9=lightest).
  Plus White (identity).
  Merge rules:
    Both White → +3.  Same shade → -1.
    Darker card merged ONTO lighter card (target > source): +1 (or +2 if sum > 9).
    Lighter onto darker: -1.
  Strategy: merge dark cards onto light cards.  card_index reported as color_index_gray.\
""",
    ("color", "text"): """\
VISUAL — Text mode (Stroop effect)
  Cards show a colour NAME written in a DIFFERENT ink colour.
  Merge logic identical to Add mode (uses the ink colour, not the word).
  The visual conflict makes this harder for screenshot-based agents.
  In metadata: you see the RGB values (the ink colour).  Use Add mode rules.\
""",
    ("shape", "triangle"): """\
SPATIAL — Triangle mode
  Cards show triangles in one of 8 orientations (index 0-7).  Index 8 = blank.
  Merge: matching orientations scores well.
  Scoring: based on how the two triangle orientations combine geometrically.
    Complementary orientations → +2.  Same orientation → varies.
  Strategy: merge triangles that are mirror/complement pairs.\
""",
    ("shape", "rectangle"): """\
SPATIAL — Rectangle mode
  Cards show rectangles in orientations (index 0-7).  Index 8 = blank.
  Same merge logic as Triangle mode but with rectangle geometry.\
""",
    ("shape", "triple"): """\
SPATIAL — Triple mode
  Cards show three overlapping shapes.
  Merge logic based on geometric compatibility of the triple patterns.\
""",
    ("shape", "kanizsa"): """\
SPATIAL — Kanizsa mode
  Cards show Kanizsa illusory contour patterns (index 0-7).  Index 8 = blank.
  Same merge structure as Triangle mode.
  Strategy: merge complementary Kanizsa patterns.\
""",
    ("shape", "sphere"): """\
SPATIAL — Sphere mode
  Cards show 3D sphere positions.
  Merge logic based on spatial position compatibility.\
""",
    ("shape", "hanoi"): """\
SPATIAL — Hanoi mode
  Cards represent Tower of Hanoi disc configurations (index 0-15).  Index 16 = blank.
  Merge: based on valid Hanoi move sequences.
  This is one of the hardest spatial modes — requires multi-step reasoning.\
""",
    ("word", "verbs"): """\
VERBAL — Verbs mode
  Cards have a list of verbs (e.g. ["run"], ["walk"]).
  Merge: words are compared pairwise.  Matching PAIRS (defined in the game's word list) → bonus.
    Identical words → penalty.  No relationship → neutral.
  Scoring: total multiplier across all pairs → +3/+2/+1/-1.
  Strategy: merge cards whose verbs are PAIRED in the game's word list (related but not identical).\
""",
    ("word", "adjectives"): """\
VERBAL — Adjectives mode
  Same as Verbs mode but with adjective pairs.
  Strategy: merge cards with related (but not identical) adjectives.\
""",
    ("word", "nouns"): """\
VERBAL — Nouns mode
  Same as Verbs mode but with noun pairs.
  Strategy: merge cards with related (but not identical) nouns.\
""",
    ("word", "synVerbs"): """\
VERBAL — Synonym Verbs mode
  Cards have verbs; matching is based on SYNONYMS.
  Merge synonym pairs for bonus.  Same word → penalty.
  Strategy: merge verbs that mean the same thing (e.g. "run" + "sprint").\
""",
    ("word", "synAdjectives"): """\
VERBAL — Synonym Adjectives mode
  Cards have adjectives; matching is based on synonyms.
  Strategy: merge adjectives that mean the same thing.\
""",
    ("word", "grammar"): """\
VERBAL — Grammar mode
  Cards have grammar elements (sentence fragments).
  Merge: grammatically compatible fragments score well.
  Strategy: merge fragments that form valid grammatical structures.\
""",
    ("word", "questions"): """\
VERBAL — Questions mode
  Cards have question words/phrases.
  Merge: matching question-answer pairs score well.\
""",
    ("word", "scrabble"): """\
VERBAL — Scrabble mode
  Cards have single LETTERS (characters).
  Merge: letters concatenate.  If the result is a valid English word → bonus.
    Word length 2 → +1.  Length 3 → +2.  Length 4+ → +3.
    Not a word → 0 (neutral, not negative).
  Strategy: build real English words by merging letters in the right order.
  NOTE: merge order matters — the new card's letter is PREPENDED to the slot's.\
""",
    ("memory", "every action"): """\
MEMORY — Every Action mode
  After EVERY action you take, all card values are HIDDEN.
  You see that a slot is occupied and its mana, but NOT its dimension values.
  You must REMEMBER what each card's values are from when you last saw them.
  Tip: pay attention when cards are first drawn — that's when you see their values.\
""",
    ("memory", "show all"): """\
MEMORY — Show All mode
  Cards are periodically revealed (all at once), then hidden again.
  You can see values briefly, then must rely on memory.
  Easier than "every action" — you get periodic refreshes.\
""",
    ("memory", "show one"): """\
MEMORY — Show One mode
  Only ONE card is revealed at a time (rotating).
  You must build a mental model of all cards from partial glimpses.\
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


def _color_name(r: float, g: float, b: float) -> str:
    key = (round(r), round(g), round(b))
    return _COLOR_NAMES.get(key, f"RGB({r:.2f},{g:.2f},{b:.2f})")


def build_system_prompt(modes: dict) -> str:
    """Build a game-specific system prompt from active modes."""
    parts = [CORE_RULES, ""]

    # Add rules for each active dimension
    has_rules = False
    for field, mode_val in modes.items():
        if not mode_val:
            continue
        key = (field, mode_val)
        rule = DIMENSION_RULES.get(key)
        if rule:
            parts.append(rule)
            has_rules = True

    if not has_rules:
        parts.append("No specific dimension rules available — use general merge strategy.")

    parts.append("")
    parts.append("RESPONSE FORMAT")
    parts.append("Reply with ONLY the action number.  No explanation, no text — just the integer.")

    return "\n\n".join(parts)


def describe_state(raw_state: dict) -> str:
    """Convert raw game state dict to a concise text description for the LLM."""
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
# Agent
# =====================================================================

class LLMAgent(BaseAgent):
    """LLM-based agent supporting stateless/conversational × metadata/screenshot modes.

    Args:
        model: Anthropic model ID.
        mode: "stateless" (A) or "conversational" (B).
        use_screenshot: If True, include screenshots in prompts (requires VLM env).
        game_modes: Dict of active game dimensions, used to build the system prompt.
        max_tokens: Max response tokens per API call.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        mode: str = "conversational",
        use_screenshot: bool = False,
        game_modes: dict = None,
        max_tokens: int = 512,
    ):
        label = "vision" if use_screenshot else "meta"
        mode_label = "a" if mode == "stateless" else "b"
        super().__init__(name=f"claude-{label}-{mode_label}-{model}")

        self.model = model
        self.mode = mode
        self.use_screenshot = use_screenshot
        self.max_tokens = max_tokens
        self._client = None

        # System prompt is built once per config (set via set_game_modes or constructor)
        self._game_modes = game_modes or {}
        self._system_prompt = build_system_prompt(self._game_modes)

        # Conversation history (Mode B only)
        self._messages: list[dict] = []

    def set_game_modes(self, modes: dict):
        """Update game modes and rebuild the system prompt."""
        self._game_modes = modes
        self._system_prompt = build_system_prompt(modes)

    def reset(self):
        self._messages = []

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    def act(self, observation: dict, info: dict = None) -> int:
        info = info or {}
        raw_state = info.get("raw_state", {})

        # Build user message content blocks
        content = []

        # Screenshot (if enabled and available)
        if self.use_screenshot:
            screenshot = info.get("screenshot")
            if screenshot is not None and isinstance(screenshot, np.ndarray) and screenshot.size > 0:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": self._encode_screenshot(screenshot),
                    },
                })

        # Text state description (always included)
        state_text = describe_state(raw_state)
        content.append({"type": "text", "text": state_text})

        # Build messages for the API call
        if self.mode == "stateless":
            messages = [{"role": "user", "content": content}]
        else:
            # Conversational: append to history
            self._messages.append({"role": "user", "content": content})
            # Trim if too long
            if len(self._messages) > MAX_HISTORY_TURNS * 2:
                # Keep system context fresh: drop oldest turns but keep the first exchange
                self._messages = self._messages[:2] + self._messages[-(MAX_HISTORY_TURNS * 2 - 2):]
            messages = list(self._messages)

        # API call
        try:
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self._system_prompt,
                messages=messages,
            )
            response_text = response.content[0].text.strip()

            # In conversational mode, record the assistant reply
            if self.mode == "conversational":
                self._messages.append({"role": "assistant", "content": response_text})

            action = self._parse_action(response_text, observation)
            logger.info(f"LLM chose action {action} (raw: {response_text!r})")
            return action

        except Exception as e:
            logger.error(f"LLM API error: {e}", exc_info=True)
            # Fallback: first valid action
            return self._fallback_action(observation)

    def on_step_result(self, action: int, reward: float, terminated: bool, info: dict):
        """In conversational mode, inject a brief result note so the model tracks outcomes."""
        if self.mode != "conversational":
            return
        if not self._messages:
            return

        raw_state = info.get("raw_state", {})
        mana = raw_state.get("mana", 0)
        mana_max = raw_state.get("mana_max", 0)

        note = f"[Result: action={action}, reward={reward:+.2f}, mana={mana:.0f}, best={mana_max:.0f}]"

        # Append as a user message so the model sees the feedback
        # (it follows the assistant's action choice)
        if self._messages and self._messages[-1]["role"] == "assistant":
            self._messages.append({"role": "user", "content": note})

    # -----------------------------------------------------------------
    # Parsing
    # -----------------------------------------------------------------

    @staticmethod
    def _parse_action(text: str, observation: dict) -> int:
        """Extract an action number from the LLM response, validating against the mask."""
        mask = observation.get("action_mask", None)

        # Try to find numbers in the response
        numbers = re.findall(r'\d+', text)
        for num_str in numbers:
            action = int(num_str)
            if mask is not None and 0 <= action < len(mask) and mask[action] > 0:
                return action

        # Fallback: first valid action from mask
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
