"""
Yedi Gymnasium Environment.

Connects to the Yedi game running in a browser via WebSocket through gym_server.py.
Supports both metadata-only (RL) and visual (VLM) observation modes.

Action Space (Discrete(37)):
    0:      DRAW_CARD
    1-30:   MOVE(src, dst) — src in {new,1-5}, dst in {1-5}
            action = 1 + src_idx * 5 + (dst_idx - 1)
    31-36:  SELL(src) — src in {new,1-5}
            action = 31 + src_idx

Observation Space (Dict):
    mana, mana_max, timer_remaining, beat_phase: Box scalars
    slots: Box(7, 11) — per-slot card features
    valid_actions: MultiBinary(37) — action mask
"""

import asyncio
import json
import logging
import threading
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

# The game always starts with this mana balance.  Scores are more
# meaningful as *surplus* (mana earned above the initial grant) because
# the initial 200 is a sunk cost that doesn't reflect agent skill.
INITIAL_MANA = 200


class BridgeDisconnectedError(RuntimeError):
    """Raised when the WebSocket bridge to the browser game has died.

    Distinct from generic Exception so the runner can mark the run FAILED
    with a clear, actionable message instead of cryptic websockets internals
    like 'no close frame received or sent'.
    """

# Action space constants
NUM_ACTIONS = 37
ACTION_DRAW = 0
ACTION_MOVE_BASE = 1  # 1..30
ACTION_SELL_BASE = 31  # 31..36

# Slot names for indexing
SLOT_NAMES = ["new", "1", "2", "3", "4", "5"]


def action_to_command(action: int) -> dict:
    """Convert a discrete action index to a game command dict."""
    if action == ACTION_DRAW:
        return {"type": "draw_card"}
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
        command_timeout: float = 30.0,
    ):
        super().__init__()

        if websockets is None:
            raise ImportError("websockets package required: pip install websockets")

        self.server_url = server_url
        self.game_config = game_config or {}
        self.render_mode = render_mode
        self._seed = seed
        self.max_steps = max_steps
        self.command_timeout = command_timeout

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
        self._loop_thread: Optional[threading.Thread] = None
        self._state = None
        self._prev_mana = 0
        self._prev_mana_max = 0
        self._step_count = 0

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _ensure_connected(self):
        if self._ws is not None:
            return
        # Run the asyncio loop in a dedicated daemon thread. Without this,
        # the loop would only spin during run_until_complete() and the
        # websockets library could not respond to server keepalive pings
        # during the long waits between commands (LLM inference can easily
        # take 200-330s for slow models like Kimi-K2.5). Missed pongs trip
        # ws_ping_timeout on the server and the connection dies with 1011.
        self._loop = asyncio.new_event_loop()
        ready = threading.Event()

        def _loop_runner():
            asyncio.set_event_loop(self._loop)
            ready.set()
            self._loop.run_forever()

        self._loop_thread = threading.Thread(
            target=_loop_runner,
            name="yedi-env-loop",
            daemon=True,
        )
        self._loop_thread.start()
        ready.wait()

        # websockets.connect(...) returns a Connect awaitable (context
        # manager), not a plain coroutine, and run_coroutine_threadsafe
        # insists on an actual coroutine. Wrap it.
        async def _do_connect():
            return await websockets.connect(
                self.server_url,
                max_size=10 * 1024 * 1024,
                # Disable client-side pings. The server side still pings us
                # and our background loop keeps responding even while the
                # main thread is blocked in an LLM call.
                ping_interval=None,
            )

        self._ws = asyncio.run_coroutine_threadsafe(
            _do_connect(), self._loop,
        ).result()
        logger.info(f"Connected to {self.server_url}")

    def _send_command(self, command: dict, timeout: float = None) -> dict:
        """Send a command and wait for the response.

        Args:
            timeout: seconds to wait. Defaults to ``self.command_timeout``
                (30s by default, but parallel workers pass a higher value to
                tolerate background-tab throttling).

        Raises:
            BridgeDisconnectedError: when the WebSocket bridge dies (browser
                tab closed, ASGI socket already shut down, etc.) or when the
                server forwards a bridge-level error response.
        """
        if timeout is None:
            timeout = getattr(self, "command_timeout", 30.0)
        self._ensure_connected()

        async def _do():
            await self._ws.send(json.dumps(command))
            raw = await asyncio.wait_for(self._ws.recv(), timeout)
            return json.loads(raw)

        try:
            # Submit the coroutine to the background loop and block this
            # thread until it resolves. The inner asyncio.wait_for enforces
            # the command timeout; we pass no outer timeout here so the
            # concurrent.futures future does not fire a second one.
            response = asyncio.run_coroutine_threadsafe(
                _do(), self._loop,
            ).result()
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
    # Reset readiness probe
    # ------------------------------------------------------------------

    @staticmethod
    def _is_fresh_state(state: dict) -> bool:
        """True iff ``state`` looks like a freshly-reset game.

        Background: scene reloads exhibit a TOC/TOU race. The new
        HeptagonController scene initializes its action_count counter to 0
        the moment Unity begins booting the new gameplay scene, but the
        slot game objects spawn later and the ManaDisplay singleton may
        still be holding the previous episode's mana value during that
        window. A weaker check (mana>0, action_count==0, valid_actions
        present) accepted those mash-up frames in run_1ffefc335187 and
        produced 11/24 zero-score "ghost episodes" — slots populated with
        leftover cards from the prior episode, mana frozen at the prior
        leaving value, but step counter rolled back to 0.

        The four checks below, taken together, are unambiguous: every one
        of them is satisfied by a real fresh game and every one rejects
        the observed mash-up frame.

          - ``mana > 0``: must be present (post-game-over flame leaks 0)
          - non-empty ``valid_actions``: any active game has at least DRAW
          - ``action_count == 0``: explicit step=0 (not still showing the
            final step of the previous episode). ``action_count`` is the
            ``Step:`` field on describe_state's user-text dump.
          - **all slots empty**: a fresh game cannot have occupied build
            slots; the bug case had slots 1 + 3 still holding prior cards.
          - **mana_max consistent with mana**: a fresh game initializes
            mana_max either to 0 or to the starting mana (always equal to
            the current mana). The mash-up frame had mana_max=193 while
            mana=81 — clearly stale.
        """
        if not isinstance(state, dict):
            return False
        if float(state.get("mana", 0) or 0) <= 0:
            return False
        if not state.get("valid_actions"):
            return False
        # Note: don't use ``or -1`` here — that would short-circuit to -1
        # when action_count is the literal 0 we're trying to match. Use
        # an explicit ``is None`` / sentinel instead.
        ac = state.get("action_count")
        if ac is None:
            return False
        try:
            if int(ac) != 0:
                return False
        except (TypeError, ValueError):
            return False

        # All slots must be empty. The slot serializer always emits 7
        # entries (new + 1..5 + sell); a missing list is itself a sign
        # the bridge is mid-load and should be polled again.
        slots = state.get("slots")
        if not isinstance(slots, list) or len(slots) == 0:
            return False
        for slot in slots:
            if isinstance(slot, dict) and slot.get("occupied", False):
                return False

        # mana_max must be either 0 (uninitialized) or equal to the
        # current mana (a fresh game initializes mana_max to the starting
        # mana, which IS the current mana before any actions). Anything
        # else is a stale value bleeding through from the prior episode.
        try:
            mana = float(state.get("mana", 0) or 0)
            mmax = float(state.get("mana_max", 0) or 0)
        except (TypeError, ValueError):
            return False
        if mmax != 0 and abs(mmax - mana) > 0.5:
            return False

        return True

    @staticmethod
    def _is_broken_loading_state(state: dict) -> bool:
        """True iff ``state`` looks like the bridge's "scene loading" sentinel.

        After scene reload, the bridge sometimes returns frames where Unity
        has wiped the previous game's singletons but not yet booted the
        new ones. The frame's signature is unmistakable:
            mana=0, mana_max=0, action_count=None, no valid_actions, no
            occupied slots.
        In describe_state's user-text dump this renders as a single line
        ``Mana: 0 | Best: 0 | Step: ?/?`` with nothing else — the model
        has no information to act on.

        In run_1ffefc335187 every zero-score episode followed this exact
        pattern after step 0: 200 consecutive blank frames burned through
        with a=0 fallbacks because the env had no way to tell the bridge
        was lost. Detecting it lets step() raise BridgeDisconnectedError
        so the runner's recovery path (recreate env, retry) kicks in
        instead of grinding through wasted LLM calls.

        Note: this is intentionally narrow. We only return True when ALL
        of the following hold, so we don't accidentally trip during a
        normal mid-game state where mana legitimately bottoms out at 0
        but the slots/valid_actions/action_count are still present.
        """
        if not isinstance(state, dict):
            return True  # No state at all is definitely broken.
        # action_count present but None is the sentinel — anything else
        # (an int, even 0) means the bridge is reporting a real frame.
        if state.get("action_count") is not None:
            return False
        if float(state.get("mana", 0) or 0) > 0:
            return False
        if state.get("valid_actions"):
            return False
        slots = state.get("slots") or []
        for slot in slots:
            if isinstance(slot, dict) and slot.get("occupied", False):
                return False
        return True

    def _wait_for_fresh_state(self, timeout: float = 15.0) -> dict:
        """Poll get_state until the response looks like a fresh game.

        Replaces the old ``time.sleep(3.0)`` race. Polls every 200ms for up
        to ``timeout`` seconds. Raises BridgeDisconnectedError on timeout
        rather than handing back a corrupt state — a noisy failure here is
        much better than the silent zero-score episodes we used to log.
        """
        deadline = time.monotonic() + timeout
        last_state: dict = {}
        error_count = 0
        while time.monotonic() < deadline:
            response = self._send_command({"type": "get_state"})

            # Unity's AgentBridge sends {"type": "error", "message": "Game
            # not ready"} while CacheReferencesDelayed hasn't finished. These
            # DON'T carry a top-level "error" key (that's the server format),
            # so _send_command lets them through. Recognise them here and keep
            # polling — the scene just hasn't booted yet.
            if isinstance(response, dict) and response.get("type") == "error":
                error_count += 1
                time.sleep(0.2)
                continue

            if self._is_fresh_state(response):
                if error_count > 0:
                    logger.debug(
                        "fresh state arrived after %d 'not ready' errors",
                        error_count,
                    )
                return response
            last_state = response
            time.sleep(0.2)

        # Build a useful diagnostic from the last response we saw, so the
        # benchmark log shows WHY we gave up rather than just "timeout".
        diag = {
            "mana": last_state.get("mana"),
            "action_count": last_state.get("action_count"),
            "valid_actions_count": len(last_state.get("valid_actions") or []),
            "error_responses": error_count,
        }
        raise BridgeDisconnectedError(
            f"scene reload never produced a fresh state within {timeout}s "
            f"(last seen: {diag})"
        )

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

        # Poll get_state until the scene reload finishes and Unity is serving
        # a fresh game. The previous implementation was a fixed time.sleep(3.0)
        # which silently lost ~50% of episodes on EASY: when scene reload took
        # longer than 3s, get_state returned the stale post-game-over state
        # (mana=0, no slots, no valid actions), and the LLM then ran the full
        # max_steps cap on a corpse of a game while scoring 0.
        #
        # The "ready" signal is the conjunction of:
        #   - mana > 0       (post-game-over leaks mana=0)
        #   - non-empty valid_actions (a freshly reset game always has at
        #     least DRAW available)
        #   - action_count == 0 (we're at step 0, not still seeing the
        #     final-step state of the previous episode)
        # Scale the fresh-state timeout with the command timeout so
        # parallel workers (command_timeout=120) get enough polling
        # headroom even when the browser tab is slightly throttled.
        fresh_timeout = max(15.0, getattr(self, "command_timeout", 30.0))
        response = self._wait_for_fresh_state(timeout=fresh_timeout)
        self._state = response
        self._prev_mana = self._state.get("mana", 200)
        self._prev_mana_max = self._state.get("mana_max", self._prev_mana)
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

        # Draw-settle: Unity's card spawn is async — the draw_card command
        # returns immediately but the card GameObject may not exist yet when
        # get_state runs. Without this retry the model sees an empty "new"
        # slot and wastes a step. Empirically ~7% of draws were lost this
        # way (~2 per episode, always the first 2). A short poll fixes it.
        if action == ACTION_DRAW:
            slots = self._state.get("slots") or []
            new_slot = slots[0] if slots else {}
            if isinstance(new_slot, dict) and not new_slot.get("occupied", False):
                for _ in range(5):
                    time.sleep(0.1)
                    retry = self._send_command({"type": "get_state"})
                    retry_slots = retry.get("slots") or []
                    retry_new = retry_slots[0] if retry_slots else {}
                    if isinstance(retry_new, dict) and retry_new.get("occupied", False):
                        self._state = retry
                        break

        # Detect the bridge's "scene loading" sentinel before treating
        # this as a real step. Without this check the env would keep
        # round-tripping blank frames through the LLM until max_steps —
        # see _is_broken_loading_state for the failure-mode rationale
        # and the run_1ffefc335187 ghost-episode evidence.
        if self._is_broken_loading_state(self._state):
            raise BridgeDisconnectedError(
                "bridge returned a 'scene loading' sentinel mid-episode "
                "(mana=0, action_count=None, no slots, no valid_actions). "
                "The previous episode's scene teardown is still racing the "
                "next start_game — recreating the env."
            )

        self._step_count += 1

        # Compute reward. The unproductive slot-to-slot move penalty is
        # applied by the Unity bridge as an in-game mana deduction, so it
        # flows through the mana-delta term here automatically — no extra
        # shaping needed on the Python side.
        reward = self._compute_reward()
        self._prev_mana = self._state.get("mana", 0)
        self._prev_mana_max = self._state.get("mana_max", self._prev_mana_max)

        # Termination
        terminated = self._state.get("game_over", False)
        truncated = False  # Timer expiry is a normal end, not truncation

        obs = self._state_to_obs(self._state)
        max_mana = self._state.get("mana_max", 0)
        info = {
            "raw_state": self._state,
            "max_mana": max_mana,
            "surplus": max_mana - INITIAL_MANA,
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
        if self._ws and self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._ws.close(), self._loop,
                ).result(timeout=5)
            except Exception:
                # Best-effort close — a dead socket is fine, we're shutting down.
                pass
        self._ws = None
        if self._loop:
            if self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
            if self._loop_thread is not None:
                self._loop_thread.join(timeout=5)
                self._loop_thread = None
            try:
                self._loop.close()
            except Exception:
                pass
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
            mask[ACTION_DRAW] = 1  # fallback: draw is usually valid
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

        # Bonus for a genuinely new mana_max (Best). The gate compares against
        # the PREVIOUS step's mana_max, not prev_mana — otherwise the bonus
        # fires every time the bank climbs above the previous bank level,
        # which is noise, not a new personal best.
        mana_max = self._state.get("mana_max", 0)
        if mana_max > self._prev_mana_max:
            reward += 0.1

        # Penalty for game over, but ONLY if mana actually bottomed out.
        # Timer expiry also flips game_over, and penalizing every run-to-completion
        # would bake a constant -1.0 into every episode and confound capability
        # with episode length.
        if self._state.get("game_over", False) and mana <= 0:
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
