"""
Replay Logger — complete game event logging for post-analysis and RL replay.

Logs every action, observation, reward, and screenshot to a JSONL file.
Screenshots saved as separate PNG files alongside the log.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np


class _NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class ReplayLogger:
    """Logs game episodes for replay and analysis."""

    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.episode_id = None
        self.episode_dir = None
        self.log_file = None
        self.trace_file = None
        self.step_count = 0

    def start_episode(self, config: dict, agent_name: str = "unknown"):
        """Begin logging a new episode."""
        self.episode_id = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}"
        self.episode_dir = self.log_dir / f"episode_{self.episode_id}"
        self.episode_dir.mkdir(exist_ok=True)

        log_path = self.episode_dir / "events.jsonl"
        self.log_file = open(log_path, "w")

        # trace.jsonl captures the raw LLM exchanges for this episode. It's
        # written lazily — we only open the file when log_exchange() is called,
        # so random/greedy episodes don't leave an empty trace file behind.
        self.trace_file = None
        self.step_count = 0

        self._write({
            "type": "episode_start",
            "episode_id": self.episode_id,
            "agent_name": agent_name,
            "config": config,
            "timestamp": time.time(),
        })

    def log_step(
        self,
        action: int,
        command: dict,
        observation: dict,
        reward: float,
        terminated: bool,
        truncated: bool,
        info: dict = None,
        fallback_reason: str = None,
    ):
        """Log a single step.

        ``fallback_reason`` is set by the runner when the agent's chosen
        action came from LLMAgent's silent-fallback path (provider error,
        parse failure, etc.) instead of a real model decision. Offline
        analysis uses this to distinguish "the model picked action X" from
        "the LLM crashed and we defaulted to the first valid action".
        """
        # Convert numpy arrays to lists for JSON serialization
        obs_serializable = {}
        for k, v in observation.items():
            if isinstance(v, np.ndarray):
                obs_serializable[k] = v.tolist()
            else:
                obs_serializable[k] = v

        self._write({
            "type": "step",
            "step": self.step_count,
            "timestamp": time.time(),
            "action": action,
            "command": command,
            "observation": obs_serializable,
            "reward": reward,
            "terminated": terminated,
            "truncated": truncated,
            "mana": observation.get("mana", [0])[0] if isinstance(observation.get("mana"), (list, np.ndarray)) else observation.get("mana", 0),
            "info_max_mana": info.get("max_mana") if info else None,
            "fallback_reason": fallback_reason,
        })

        self.step_count += 1

    def log_exchange(
        self,
        step_in_episode: int,
        user_text: str,
        response: str,
        action: int,
        latency_ms: float,
        error: str = None,
        system_prompt: str = None,
        fallback_reason: str = None,
    ):
        """Persist a single LLM exchange to ``trace.jsonl``.

        Mirrors the in-memory ``RunTraceStore`` entries so crashed or
        closed sessions can still be debugged offline. Called from the
        benchmark runner's ``_on_exchange`` closure after every LLM call
        (both success and error paths).

        The file is opened on first use so non-LLM episodes don't leave
        empty files behind.
        """
        if self.episode_dir is None:
            return
        if self.trace_file is None:
            trace_path = self.episode_dir / "trace.jsonl"
            self.trace_file = open(trace_path, "w")
            # Stamp the system prompt once at the top of the trace so
            # every entry after it can be interpreted without ambiguity.
            if system_prompt:
                self._write_trace({
                    "type": "system_prompt",
                    "timestamp": time.time(),
                    "system_prompt": system_prompt,
                })
        self._write_trace({
            "type": "exchange",
            "timestamp": time.time(),
            "step_in_episode": step_in_episode,
            "user_text": user_text,
            "response": response,
            "action": action,
            "latency_ms": latency_ms,
            "error": error,
            "fallback_reason": fallback_reason,
        })

    def log_screenshot(self, screenshot: np.ndarray):
        """Save a screenshot PNG and log a reference."""
        if screenshot is None or self.episode_dir is None:
            return

        filename = f"step_{self.step_count:04d}.png"
        filepath = self.episode_dir / filename

        try:
            from PIL import Image
            img = Image.fromarray(screenshot)
            img.save(filepath)

            self._write({
                "type": "screenshot",
                "step": self.step_count,
                "path": str(filepath),
                "timestamp": time.time(),
            })
        except ImportError:
            pass  # PIL not available, skip screenshots

    def end_episode(self, final_state: dict = None):
        """Finalize and close the episode log."""
        end_data = {
            "type": "episode_end",
            "episode_id": self.episode_id,
            "total_steps": self.step_count,
            "timestamp": time.time(),
        }
        if final_state:
            end_data["max_mana"] = final_state.get("mana_max", 0)
            end_data["game_time"] = final_state.get("game_time", 0)
            end_data["game_over"] = final_state.get("game_over", False)

        self._write(end_data)

        if self.log_file:
            self.log_file.close()
            self.log_file = None
        if self.trace_file:
            self.trace_file.close()
            self.trace_file = None

    def _write(self, data: dict):
        if self.log_file:
            self.log_file.write(json.dumps(data, cls=_NumpyEncoder) + "\n")
            self.log_file.flush()

    def _write_trace(self, data: dict):
        if self.trace_file:
            self.trace_file.write(json.dumps(data, cls=_NumpyEncoder) + "\n")
            self.trace_file.flush()
