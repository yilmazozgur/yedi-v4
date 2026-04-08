"""
Yedi Gymnasium Environment.

Connects to the Yedi game running in a browser via WebSocket through gym_server.py.
Supports both metadata-only (RL) and visual (VLM) observation modes.

Action Space (Discrete(38)):
    0:      DRAW_CARD
    1-30:   MOVE(src, dst) — src in {new,1-5}, dst in {1-5}
            action = 1 + src_idx * 5 + (dst_idx - 1)
    31-36:  SELL(src) — src in {new,1-5}
            action = 31 + src_idx
    37:     WAIT (no-op, relevant for beat timing)

Observation Space (Dict):
    mana, mana_max, timer_remaining, beat_phase: Box scalars
    slots: Box(7, 11) — per-slot card features
    valid_actions: MultiBinary(38) — action mask
"""

import asyncio
import json
import logging
import time
from typing import Optional

import gymnasium as gym
import numpy as np

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    websockets = None
    ConnectionClosed = Exception  # type: ignore[assignment,misc]

logger = logging.getLogger("yedi_env")


class BridgeDisconnectedError(RuntimeError):
    """Raised when the WebSocket bridge to the browser game has died.

    Distinct from generic Exception so the runner can mark the run FAILED
    with a clear, actionable message instead of cryptic websockets internals
    like 'no close frame received or sent'.
    """

# Action space constants
NUM_ACTIONS = 38
ACTION_DRAW = 0
ACTION_MOVE_BASE = 1  # 1..30
ACTION_SELL_BASE = 31  # 31..36
ACTION_WAIT = 37

# Slot names for indexing
SLOT_NAMES = ["new", "1", "2", "3", "4", "5"]


def action_to_command(action: int) -> dict:
    """Convert a discrete action index to a game command dict."""
    if action == ACTION_DRAW:
        return {"type": "draw_card"}
    elif action == ACTION_WAIT:
        return {"type": "get_state"}  # WAIT = just get state, no action
    elif ACTION_MOVE_BASE <= action <= 30:
        idx = action - ACTION_MOVE_BASE
        src_idx = idx // 5
        dst_num = (idx % 5) + 1
        return {
            "type": "move_card",
            "source": SLOT_NAMES[src_idx],
            "target": str(dst_num),
        }
    elif ACTION_SELL_BASE <= action <= 36:
        src_idx = action - ACTION_SELL_BASE
        return {
            "type": "sell_card",
            "source": SLOT_NAMES[src_idx],
        }
    else:
        raise ValueError(f"Invalid action: {action}")


def command_to_action(cmd: dict) -> int:
    """Convert a game command dict to a discrete action index."""
    t = cmd["type"]
    if t == "draw_card":
        return ACTION_DRAW
    elif t == "move_card":
        src = cmd["source"]
        dst = int(cmd["target"])
        src_idx = SLOT_NAMES.index(src)
        return ACTION_MOVE_BASE + src_idx * 5 + (dst - 1)
    elif t == "sell_card":
        src = cmd["source"]
        src_idx = SLOT_NAMES.index(src)
        return ACTION_SELL_BASE + src_idx
    elif t == "get_state":
        return ACTION_WAIT
    else:
        raise ValueError(f"Unknown command type: {t}")


class YediEnv(gym.Env):
    """Gymnasium environment for the Yedi brain training game."""

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}

    def __init__(
        self,
        server_url: str = "ws://localhost:8000/ws/agent",
        game_config: Optional[dict] = None,
        render_mode: Optional[str] = None,
        seed: Optional[int] = None,
        max_steps: int = 100,
    ):
        super().__init__()

        if websockets is None:
            raise ImportError("websockets package required: pip install websockets")

        self.server_url = server_url
        self.game_config = game_config or {}
        self.render_mode = render_mode
        self._seed = seed
        self.max_steps = max_steps

        # Action space
        self.action_space = gym.spaces.Discrete(NUM_ACTIONS)

        # Observation space
        self.observation_space = gym.spaces.Dict({
            "mana": gym.spaces.Box(0, 10000, shape=(1,), dtype=np.float32),
            "mana_max": gym.spaces.Box(0, 10000, shape=(1,), dtype=np.float32),
            "timer_remaining": gym.spaces.Box(0, 300, shape=(1,), dtype=np.float32),
            "beat_phase": gym.spaces.Box(0, 1, shape=(1,), dtype=np.float32),
            "slots": gym.spaces.Box(-100, 100, shape=(7, 11), dtype=np.float32),
            "action_mask": gym.spaces.MultiBinary(NUM_ACTIONS),
        })

        self._ws = None
        self._loop = None
        self._state = None
        self._prev_mana = 0
        self._step_count = 0

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _ensure_connected(self):
        if self._ws is not None:
            return
        self._loop = asyncio.new_event_loop()
        self._ws = self._loop.run_until_complete(
            websockets.connect(self.server_url, max_size=10 * 1024 * 1024)
        )
        logger.info(f"Connected to {self.server_url}")

    def _send_command(self, command: dict, timeout: float = 30.0) -> dict:
        """Send a command and wait for the response.

        Raises:
            BridgeDisconnectedError: when the WebSocket bridge dies (browser
                tab closed, ASGI socket already shut down, etc.) or when the
                server forwards a bridge-level error response.
        """
        self._ensure_connected()

        async def _do():
            await self._ws.send(json.dumps(command))
            raw = await asyncio.wait_for(self._ws.recv(), timeout)
            return json.loads(raw)

        try:
            response = self._loop.run_until_complete(_do())
        except ConnectionClosed as e:
            # Drop the dead socket so the next call doesn't try to reuse it.
            self._ws = None
            raise BridgeDisconnectedError(
                f"WebSocket bridge to game closed: {e}"
            ) from e
        except asyncio.TimeoutError as e:
            raise BridgeDisconnectedError(
                f"timed out waiting for {command.get('type')} response after {timeout}s"
            ) from e

        # Server-side bridge errors come back as {"error": "...", "seq": ...}.
        # The "ok" path always carries a state field (mana, type, etc.) instead.
        if isinstance(response, dict) and "error" in response and "mana" not in response:
            raise BridgeDisconnectedError(
                f"bridge error for {command.get('type')}: {response.get('error')}"
            )

        return response

    # ------------------------------------------------------------------
    # Gymnasium interface
    # ------------------------------------------------------------------

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._ensure_connected()

        # Build start_game command with modes
        # This sets HeptagonController static fields and loads the gameplay scene
        start_cmd = {"type": "start_game"}

        if seed is not None:
            start_cmd["seed"] = seed
        elif self._seed is not None:
            start_cmd["seed"] = self._seed

        if "player_name" in self.game_config:
            start_cmd["player_name"] = self.game_config["player_name"]

        # Map mode config to command fields
        modes = self.game_config.get("modes", {})
        mode_field_map = {
            "number": "mode_number",
            "color": "mode_color",
            "shape": "mode_shape",
            "word": "mode_word",
            "beat": "mode_beat",
            "memory": "mode_memory",
            "motor": "mode_motor",
        }
        for key, field in mode_field_map.items():
            if key in modes:
                start_cmd[field] = modes[key]

        # Step-based game limit — Unity disables the timer and counts actions
        if self.max_steps > 0:
            start_cmd["max_steps"] = self.max_steps

        # Per-run ablation: when game_config asks for perfect_memory, tell the
        # bridge to stop masking hidden card values + previews. Off by default
        # so the canonical Memory dimension behaviour is preserved.
        if self.game_config.get("perfect_memory"):
            start_cmd["perfect_memory"] = True

        self._send_command(start_cmd)

        # Wait for scene to load, then get initial state
        time.sleep(3.0)  # Scene reload takes ~2-3s
        response = self._send_command({"type": "get_state"})
        self._state = response
        self._prev_mana = self._state.get("mana", 200)
        self._step_count = 0

        obs = self._state_to_obs(self._state)
        info = {"raw_state": self._state}
        return obs, info

    def step(self, action: int):
        command = action_to_command(action)
        response = self._send_command(command)

        # The response includes updated state
        if "mana" in response:
            self._state = response
        else:
            # Some responses (ack, error) don't include state — fetch it
            state_resp = self._send_command({"type": "get_state"})
            self._state = state_resp

        self._step_count += 1

        # Compute reward
        reward = self._compute_reward()
        self._prev_mana = self._state.get("mana", 0)

        # Termination
        terminated = self._state.get("game_over", False)
        truncated = False  # Timer expiry is a normal end, not truncation

        obs = self._state_to_obs(self._state)
        info = {
            "raw_state": self._state,
            "max_mana": self._state.get("mana_max", 0),
            "step": self._step_count,
        }

        return obs, reward, terminated, truncated, info

    def render(self):
        if self.render_mode == "rgb_array":
            response = self._send_command({"type": "get_screenshot"})
            if "data" in response and response["data"]:
                return self._decode_screenshot(response["data"])
            return np.zeros((540, 960, 3), dtype=np.uint8)
        return None

    def close(self):
        if self._ws:
            self._loop.run_until_complete(self._ws.close())
            self._ws = None
        if self._loop:
            self._loop.close()
            self._loop = None

    # ------------------------------------------------------------------
    # Action mask
    # ------------------------------------------------------------------

    def get_action_mask(self) -> np.ndarray:
        """Return boolean mask of valid actions."""
        mask = np.zeros(NUM_ACTIONS, dtype=np.int8)
        if self._state and "valid_actions" in self._state:
            for a in self._state["valid_actions"]:
                if 0 <= a < NUM_ACTIONS:
                    mask[a] = 1
        else:
            mask[ACTION_WAIT] = 1  # WAIT is always valid
        return mask

    # ------------------------------------------------------------------
    # State conversion
    # ------------------------------------------------------------------

    def _state_to_obs(self, state: dict) -> dict:
        """Convert raw game state to Gymnasium observation dict."""
        obs = {
            "mana": np.array([state.get("mana", 0)], dtype=np.float32),
            "mana_max": np.array([state.get("mana_max", 0)], dtype=np.float32),
            "timer_remaining": np.array([state.get("timer_remaining", 0)], dtype=np.float32),
            "beat_phase": np.array([state.get("beat_phase", 0)], dtype=np.float32),
            "slots": self._serialize_slots(state),
            "action_mask": self.get_action_mask(),
        }
        return obs

    def _serialize_slots(self, state: dict) -> np.ndarray:
        """Serialize slot data to (7, 11) array.

        Per slot: [occupied, mana, merges_done, is_super,
                   number_val, color_r, color_g, color_b,
                   shape_idx, memory_hidden, beat_phase]
        """
        slots_array = np.zeros((7, 11), dtype=np.float32)
        slots_data = state.get("slots", [])
        if not slots_data:
            return slots_array

        for i, slot in enumerate(slots_data):
            if i >= 7:
                break
            if not slot.get("occupied", False):
                continue
            slots_array[i, 0] = 1.0  # occupied
            slots_array[i, 1] = slot.get("card_mana", 0)
            slots_array[i, 2] = slot.get("merges_done", 0)
            slots_array[i, 3] = 0  # is_super (TODO)
            slots_array[i, 4] = slot.get("number_value", 0)
            slots_array[i, 5] = slot.get("color_r", 0)
            slots_array[i, 6] = slot.get("color_g", 0)
            slots_array[i, 7] = slot.get("color_b", 0)
            slots_array[i, 8] = slot.get("shape_index", 0)
            slots_array[i, 9] = 1.0 if slot.get("memory_hidden", False) else 0.0
            slots_array[i, 10] = state.get("beat_phase", 0)

        return slots_array

    # ------------------------------------------------------------------
    # Reward
    # ------------------------------------------------------------------

    def _compute_reward(self) -> float:
        mana = self._state.get("mana", 0)
        delta = mana - self._prev_mana
        reward = delta / 100.0

        # Bonus for new max
        mana_max = self._state.get("mana_max", 0)
        if mana_max > self._prev_mana:
            reward += 0.1

        # Penalty for game over (mana hit 0)
        if self._state.get("game_over", False):
            reward -= 1.0

        return reward

    # ------------------------------------------------------------------
    # Screenshot decoding
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_screenshot(base64_data: str) -> np.ndarray:
        """Decode base64 PNG to numpy array."""
        import base64
        import io
        from PIL import Image

        img_bytes = base64.b64decode(base64_data)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        return np.array(img, dtype=np.uint8)

    # ------------------------------------------------------------------
    # Time control (for beat timing)
    # ------------------------------------------------------------------

    def advance_time(self, delta_seconds: float):
        """Advance game time by delta_seconds (turn-based mode)."""
        response = self._send_command({
            "type": "step_time",
            "delta": delta_seconds,
        })
        if "mana" in response:
            self._state = response
        else:
            state_resp = self._send_command({"type": "get_state"})
            self._state = state_resp

    # ------------------------------------------------------------------
    # Merge preview (greedy agent baseline)
    # ------------------------------------------------------------------

    def preview_merge(self, source: str, target: str) -> dict:
        """Score a candidate merge WITHOUT committing it.

        Calls the bridge's preview_merge command, which delegates to the same
        ComputeMerge*Gain functions that the real merge code uses, so the
        preview is guaranteed to match the actual scoring.

        Args:
            source: name of the slot holding the moving card ("new" or "1".."5")
            target: name of the slot the card would land on ("1".."5"). Must
                    be currently occupied (a place-into-empty has no merge to
                    score).

        Returns:
            dict with per-dimension gain tiers (number/color/shape/word_gain),
            each in {-1, 0, 1, 2, 3} where -1=bad, 0=neutral or inactive,
            1=ok, 2=great, 3=perfect. Plus target_can_accept_merge (False if
            the target card has already hit its 3-merge cap).

        Raises:
            BridgeDisconnectedError: on the same conditions as _send_command.
        """
        return self._send_command({
            "type": "preview_merge",
            "source": source,
            "target": target,
        })
