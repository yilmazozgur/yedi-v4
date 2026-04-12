"""
VLM Agent — uses Claude or other Vision-Language Models to play Yedi.

The agent receives a screenshot + text description of the game state
and valid actions, then asks the VLM to choose an action.
"""

import base64
import io
import logging
import re

import numpy as np
from .base_agent import BaseAgent

logger = logging.getLogger("vlm_agent")


class ClaudeAgent(BaseAgent):
    """Agent that uses Anthropic's Claude to play Yedi.

    Requires: pip install anthropic
    Set ANTHROPIC_API_KEY environment variable.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 256,
        system_prompt: str = None,
    ):
        super().__init__(name=f"claude-{model}")
        self.model = model
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or self._default_system_prompt()
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    @staticmethod
    def _default_system_prompt() -> str:
        return """You are playing YEDI, a brain training card game. Your goal is to maximize your mana score.

Game rules:
- You have 5 slots and a draw slot. Cards have values in multiple dimensions (number, color, shape, word).
- DRAW a card (costs mana), then MOVE it to a slot or MERGE it with another card.
- Merging: if the merge produces a good result in any dimension, the card's mana increases. Bad merges decrease it.
- When a card is sold/destroyed, its mana is added to your total.
- Mana drains over time. Game ends when mana hits 0 or timer expires.
- Higher max mana = better score.

Strategy tips:
- Draw cards and merge them to increase their mana value before they're destroyed.
- Look for merges where dimension values complement each other (e.g., numbers that sum to 0 for 'add' mode).
- Don't let too many cards pile up — sell low-value cards to free slots.
- If Music mode is active, time your actions to the beat phase.

Respond with ONLY the action number. Nothing else."""

    def act(self, observation: dict, info: dict = None) -> int:
        if info is None:
            info = {}

        # Build the message content
        content = []

        # Add screenshot if available
        screenshot = info.get("screenshot")
        if screenshot is not None and isinstance(screenshot, np.ndarray) and screenshot.size > 0:
            img_b64 = self._encode_screenshot(screenshot)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64,
                },
            })

        # Add text description
        text_desc = info.get("text_description", "")
        valid_actions = info.get("valid_actions_text", "")

        text_content = f"{text_desc}\n\n{valid_actions}\n\nChoose an action number:"
        content.append({"type": "text", "text": text_content})

        # Call Claude
        try:
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                messages=[{"role": "user", "content": content}],
            )

            # Parse the action number from response
            response_text = response.content[0].text.strip()
            action = self._parse_action(response_text, observation)
            logger.info(f"Claude chose action {action}: {response_text}")
            return action

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            # Fallback to DRAW
            return 0

    def _parse_action(self, text: str, observation: dict) -> int:
        """Extract action number from Claude's response."""
        # Try to find a number in the response
        numbers = re.findall(r'\d+', text)
        if numbers:
            action = int(numbers[0])
            # Validate against action mask
            mask = observation.get("action_mask", None)
            if mask is not None and 0 <= action < len(mask) and mask[action] > 0:
                return action

        # If parsing failed, pick the first valid action
        mask = observation.get("action_mask", None)
        if mask is not None:
            valid = np.where(np.array(mask) > 0)[0]
            if len(valid) > 0:
                return int(valid[0])
        return 0  # DRAW

    @staticmethod
    def _encode_screenshot(screenshot: np.ndarray) -> str:
        """Encode numpy array to base64 PNG."""
        from PIL import Image
        img = Image.fromarray(screenshot)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
