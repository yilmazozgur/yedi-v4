"""
Yedi VLM Environment — extends YediEnv with screenshot + text observations
for Vision-Language Model agents (Claude, GPT-4V, etc.).
"""

import numpy as np
from typing import Optional
from .yedi_env import YediEnv, SLOT_NAMES, NUM_ACTIONS


class YediVLMEnv(YediEnv):
    """Extended Gymnasium environment for VLM (Vision-Language Model) agents.

    Adds:
    - Screenshot capture at each step
    - Natural language game state description
    - Formatted valid actions text
    """

    def __init__(
        self,
        screenshot_resolution: tuple = (960, 540),
        **kwargs,
    ):
        kwargs.setdefault("render_mode", "rgb_array")
        super().__init__(**kwargs)
        self.screenshot_resolution = screenshot_resolution
        self._last_screenshot = None

    def step(self, action: int):
        obs, reward, terminated, truncated, info = super().step(action)

        # Capture screenshot after the action
        self._last_screenshot = self.render()
        info["screenshot"] = self._last_screenshot
        info["text_description"] = self.get_text_description()
        info["valid_actions_text"] = self.get_valid_actions_text()

        return obs, reward, terminated, truncated, info

    def reset(self, seed=None, options=None):
        obs, info = super().reset(seed=seed, options=options)

        self._last_screenshot = self.render()
        info["screenshot"] = self._last_screenshot
        info["text_description"] = self.get_text_description()
        info["valid_actions_text"] = self.get_valid_actions_text()

        return obs, info

    def get_vlm_observation(self) -> dict:
        """Get the full VLM observation bundle."""
        return {
            "screenshot": self._last_screenshot,
            "text": self.get_text_description(),
            "valid_actions": self.get_valid_actions_text(),
            "raw_state": self._state,
        }

    def get_text_description(self) -> str:
        """Generate natural language description of the current game state."""
        if not self._state:
            return "Game not started."

        s = self._state
        lines = []

        # Header
        mana = s.get("mana", 0)
        mana_max = s.get("mana_max", 0)
        timer = s.get("timer_remaining", 0)
        lines.append(f"YEDI Game State")
        lines.append(f"Mana: {mana:.0f} | Max Mana: {mana_max:.0f} | Timer: {timer:.1f}s remaining")

        # Active modes
        modes = []
        for dim, key in [("Math", "mode_number"), ("Visual", "mode_color"),
                         ("Spatial", "mode_shape"), ("Verbal", "mode_word"),
                         ("Music", "mode_beat"), ("Memory", "mode_memory"),
                         ("Motor", "mode_motor")]:
            mode = s.get(key, "")
            if mode:
                modes.append(f"{dim}={mode}")
        if modes:
            lines.append(f"Active modes: {', '.join(modes)}")

        lines.append("")
        lines.append("BOARD:")

        # Slots
        slots = s.get("slots", [])
        slot_labels = ["SlotNew", "Slot1", "Slot2", "Slot3", "Slot4", "Slot5", "SlotSell"]
        for i, slot in enumerate(slots):
            label = slot_labels[i] if i < len(slot_labels) else f"Slot{i}"
            if not slot.get("occupied", False):
                lines.append(f"  {label}: Empty")
                continue

            parts = []

            # Number
            num = slot.get("number_value", -9999)
            if num != -9999:
                parts.append(f"Num={num:.1f}")

            # Color
            cr, cg, cb = slot.get("color_r", 0), slot.get("color_g", 0), slot.get("color_b", 0)
            if cr > 0 or cg > 0 or cb > 0:
                color_name = self._color_name(cr, cg, cb)
                parts.append(f"Color={color_name}")

            # Shape
            shape = slot.get("shape_index", -1)
            if shape >= 0:
                parts.append(f"Shape={shape}")

            # Word
            word = slot.get("word_value", "")
            if word:
                parts.append(f"Word={word}")

            # Hidden
            hidden = " [HIDDEN]" if slot.get("memory_hidden", False) else ""

            card_mana = slot.get("card_mana", 0)
            merges = slot.get("merges_done", 0)

            lines.append(f"  {label}: {', '.join(parts)} | Mana={card_mana:.0f} | Merges={merges}{hidden}")

        # Beat info
        if s.get("beat_active", False):
            phase = s.get("beat_phase", 0)
            period = s.get("beat_period", 1.8)
            next_beat = (1.0 - phase) * period if phase < 1 else 0
            timing_hint = ""
            if phase > 0.97 or phase < 0.03:
                timing_hint = " -> PERFECT timing NOW!"
            elif phase > 0.88 or phase < 0.12:
                timing_hint = " -> Good timing window"
            elif phase > 0.75 and phase < 0.88:
                timing_hint = " -> Wait..."
            elif phase > 0.25 and phase < 0.75:
                timing_hint = " -> Bad timing, wait for beat"
            lines.append(f"\nBeat: phase={phase:.3f}, period={period:.2f}s{timing_hint}")

        # Game over
        if s.get("game_over", False):
            lines.append(f"\nGAME OVER — Final max mana: {mana_max:.0f}")

        return "\n".join(lines)

    def get_valid_actions_text(self) -> str:
        """Format valid actions as numbered text for VLM prompting."""
        if not self._state:
            return "No actions available."

        valid = self._state.get("valid_actions", [])
        if not valid:
            return "No valid actions."

        lines = ["VALID ACTIONS (choose a number):"]
        for a in sorted(valid):
            desc = self._describe_action(a)
            lines.append(f"  {a}: {desc}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _describe_action(action: int) -> str:
        if action == 0:
            return "Draw a new card"
        elif action == 37:
            return "Wait (do nothing)"
        elif 1 <= action <= 30:
            idx = action - 1
            src_idx = idx // 5
            dst_num = (idx % 5) + 1
            src_name = SLOT_NAMES[src_idx]
            return f"Move card from {src_name} to slot {dst_num}"
        elif 31 <= action <= 36:
            src_idx = action - 31
            src_name = SLOT_NAMES[src_idx]
            return f"Sell card from {src_name}"
        return f"Unknown action {action}"

    @staticmethod
    def _color_name(r: float, g: float, b: float) -> str:
        if r > 0.9 and g < 0.1 and b < 0.1:
            return "Red"
        elif r < 0.1 and g > 0.9 and b < 0.1:
            return "Green"
        elif r < 0.1 and g < 0.1 and b > 0.9:
            return "Blue"
        elif r < 0.1 and g > 0.9 and b > 0.9:
            return "Cyan"
        elif r > 0.9 and g < 0.1 and b > 0.9:
            return "Magenta"
        elif r > 0.9 and g > 0.9 and b < 0.1:
            return "Yellow"
        elif r < 0.1 and g < 0.1 and b < 0.1:
            return "Black"
        else:
            return f"RGB({r:.1f},{g:.1f},{b:.1f})"
