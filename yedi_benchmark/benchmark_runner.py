"""
Benchmark Runner — run agents across multiple game configurations.

Two CLI modes:

LEGACY (string-name agents, no registry interaction):
    python -m yedi_benchmark.benchmark_runner --agent random --configs EASY --episodes 5
    python -m yedi_benchmark.benchmark_runner --agent claude-meta-a --configs EASY --episodes 3
    python -m yedi_benchmark.benchmark_runner --agent claude-meta-b --configs EASY --episodes 3
    python -m yedi_benchmark.benchmark_runner --agent claude-vision-a --configs EASY --episodes 3
    python -m yedi_benchmark.benchmark_runner --agent claude-vision-b --configs EASY --episodes 3

REGISTRY (looks up AgentConfig + Prompt from yedi_benchmark/data/, creates a
RunRecord that the web UI can read):
    python -m yedi_benchmark.benchmark_runner \\
        --agent-id agent_xxxxxx --mode metadata-b --configs EASY --episodes 3
    python -m yedi_benchmark.benchmark_runner \\
        --agent-id agent_xxxxxx --prompt-id prompt_yyyyyy --mode vision-a --configs ALL --episodes 1

Cherry-pick configs in either mode:
    --configs easy_math_add,med_math_gcd
"""

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np

from .yedi_env import YediEnv, BridgeDisconnectedError, action_to_command, INITIAL_MANA
from .yedi_vlm_env import YediVLMEnv
from .replay_logger import ReplayLogger
from .benchmark_configs import TIERS, ALL_BENCHMARKS
from .agents.random_agent import RandomAgent
from .agents.greedy_agent import GreedyAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")

# Maximum number of consecutive bridge failures (timeout, ws closed, etc.) we
# tolerate before giving up on the whole run. With the per-episode catch in
# place, a single hung draw_card no longer kills the run — but if every
# episode in a row is failing, the bridge is genuinely dead and there's no
# point burning the next 30s wait.
MAX_CONSECUTIVE_BRIDGE_FAILURES = 3

AGENT_TYPES = [
    "random",
    "greedy",
    "claude-meta-a", "claude-meta-b", "claude-meta-c",
    "claude-vision-a", "claude-vision-b", "claude-vision-c",
]

_LEGACY_MODE_SUFFIX = {"a": "stateless", "b": "conversational", "c": "compact"}


def create_agent(agent_type: str, game_modes: dict = None, **kwargs):
    """Factory for creating legacy string-named agents.

    The registry-driven path uses `create_agent_from_registry()` instead.
    """
    if agent_type == "random":
        return RandomAgent(seed=kwargs.get("seed"))

    if agent_type == "greedy":
        return GreedyAgent()

    if agent_type.startswith("claude-"):
        from .agents.llm_agent import LLMAgent

        # Parse: claude-{meta|vision}-{a|b|c}
        parts = agent_type.split("-")
        use_screenshot = parts[1] == "vision"
        mode = _LEGACY_MODE_SUFFIX.get(parts[2])
        if mode is None:
            raise ValueError(f"Unknown agent type: {agent_type}. Choose from: {AGENT_TYPES}")

        return LLMAgent(
            model=kwargs.get("model", "claude-sonnet-4-20250514"),
            mode=mode,
            use_screenshot=use_screenshot,
            game_modes=game_modes or {},
            max_tokens=kwargs.get("max_tokens", 512),
        )

    raise ValueError(f"Unknown agent type: {agent_type}. Choose from: {AGENT_TYPES}")


def create_agent_from_registry(
    agent_cfg,
    prompt,
    mode_enum,
    game_modes: dict = None,
    on_exchange=None,
    should_cancel=None,
    show_merge_previews: bool = False,
):
    """Build a runtime agent from a registry AgentConfig + Prompt + AgentMode.

    Args:
        agent_cfg: AgentConfig record (from AgentRegistry.get()).
        prompt: Prompt record (from PromptRegistry.get_active() or .get(id)),
            or None for non-LLM agents.
        mode_enum: AgentMode enum value (metadata-a/b, vision-a/b).
        game_modes: active dimension modes for this config (passed to LLMAgent
            so the system prompt is built correctly).
        on_exchange: optional callback fired by LLMAgent after every provider
            call. Used by the dashboard to stream live LLM thinking. Random
            and greedy agents ignore it.
        should_cancel: optional callable returning True when the runner wants
            this agent to abort. Plumbed into the LLM provider so a Cancel
            click breaks out of rate-limit backoff sleeps quickly. Random
            and greedy agents ignore it (they don't sleep).
        show_merge_previews: per-run ablation. When True, the LLM agent
            renders the bridge's pre-computed merge_previews block in its
            state description. Random and greedy ignore the flag (greedy
            always reads merge_previews directly from raw_state).
    """
    if agent_cfg.provider == "random":
        return RandomAgent()

    if agent_cfg.provider == "greedy":
        return GreedyAgent(name=agent_cfg.name)

    if agent_cfg.provider == "human":
        from .agents.human_agent import HumanAgent
        return HumanAgent(name=agent_cfg.name)

    if agent_cfg.provider == "bc":
        # Hack: the `model` field carries the checkpoint path for BC agents.
        # See providers.registry.validate_bc_checkpoint for the rationale.
        from .agents.bc_agent import BehaviorCloningAgent
        from .providers.registry import validate_bc_checkpoint

        ok, msg = validate_bc_checkpoint(agent_cfg.model)
        if not ok:
            raise ValueError(f"BC agent {agent_cfg.name!r}: {msg}")
        return BehaviorCloningAgent(agent_cfg.model, name=agent_cfg.name)

    if agent_cfg.provider == "dt":
        # Same pseudo-provider pattern as BC — the `model` field holds a
        # path to a Decision Transformer checkpoint (.pt).
        from .agents.dt_agent import DecisionTransformerAgent
        from .providers.registry import validate_dt_checkpoint

        ok, msg = validate_dt_checkpoint(agent_cfg.model)
        if not ok:
            raise ValueError(f"DT agent {agent_cfg.name!r}: {msg}")
        return DecisionTransformerAgent(agent_cfg.model, name=agent_cfg.name)

    from .providers.registry import create_provider
    from .agents.llm_agent import LLMAgent

    provider = create_provider(
        provider=agent_cfg.provider,
        model=agent_cfg.model,
        api_key_env=agent_cfg.api_key_env,
        base_url=agent_cfg.base_url,
        max_tokens=agent_cfg.max_tokens,
        supports_vision=agent_cfg.supports_vision,
        num_ctx=getattr(agent_cfg, "num_ctx", None),
    )

    llm_mode = mode_enum.memory_label  # "stateless" | "conversational" | "compact"
    return LLMAgent(
        provider=provider,
        prompt=prompt,
        mode=llm_mode,
        use_screenshot=mode_enum.use_screenshot,
        game_modes=game_modes or {},
        name=agent_cfg.name,
        on_exchange=on_exchange,
        should_cancel=should_cancel,
        show_merge_previews=show_merge_previews,
    )


def _ws_url_to_http_base(server_url: str) -> str:
    """Derive the HTTP base URL (scheme + host) from the agent WebSocket URL.

    The bridge exposes ``/api/agent/events`` on the same FastAPI process
    that serves ``/ws/agent``, so we just swap the scheme and strip the
    path. Used by the human recorder to drain queued bridge events.
    """
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(server_url)
    scheme = "https" if parsed.scheme == "wss" else "http"
    return urlunparse((scheme, parsed.netloc, "", "", "", ""))


def _drain_agent_events(http_base: str, timeout: float = 5.0) -> list:
    """Pull queued bridge events from /api/agent/events. Returns [] on error."""
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen(
            f"{http_base}/api/agent/events", timeout=timeout
        ) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        logger.warning("agent_events poll failed: %s", e)
        return []


def _bridge_alive(http_base: str, timeout: float = 2.0) -> bool:
    """Return True if both game and agent WebSockets are up server-side.

    The human recorder polls /api/agent/events over HTTP, which returns []
    whenever ``agent_connection`` is None on the server. If either side of
    the bridge has died — browser tab closed, agent WS reaped — the poll
    loop would otherwise spin forever waiting for events that can never
    arrive. This check lets the loop exit with a synthetic game_over.
    """
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen(
            f"{http_base}/api/bridge/status", timeout=timeout
        ) as resp:
            status = json.loads(resp.read().decode())
            return bool(status.get("game_connected")) and bool(
                status.get("agent_connected")
            )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def _run_episode_human(
    env,
    agent,
    replay_logger=None,
    max_steps: int = 200,
    cancel_event=None,
    poll_interval: float = 0.25,
) -> dict:
    """Record a single episode of live human play.

    Bypasses the act/step loop. Instead:
      1. ``env.reset()`` boots a fresh game in the browser.
      2. The bridge is flipped into ``recordingMode`` so every drag/draw
         the player performs emits a ``human_step`` event.
      3. We poll ``/api/agent/events`` until ``human_game_over`` arrives
         (or the bridge state flips ``game_over=True``, or the player
         hits ``max_steps``).
      4. Each ``human_step`` is written through ReplayLogger using the
         exact same schema as an AI episode — that's the whole point: the
         resulting ``events.jsonl`` is the training data.
    """
    agent.reset()
    obs, info = env.reset()

    if replay_logger:
        replay_logger.start_episode(
            config=env.game_config,
            agent_name=agent.name,
        )

    http_base = _ws_url_to_http_base(env.server_url)

    # Drain anything that was queued before we reset (e.g. stale
    # human_step events from a previous browser session).
    _drain_agent_events(http_base)

    env._send_command({"type": "set_recording_mode", "recording_mode": True})
    logger.info(
        "  Recording human play. Drag cards in the browser; "
        "the run ends when mana hits 0 or step %d is reached.",
        max_steps,
    )

    total_reward = 0.0
    step = 0
    terminated = False
    last_state = info.get("raw_state", {}) or {}
    prev_mana = float(last_state.get("mana", INITIAL_MANA) or INITIAL_MANA)
    prev_mana_max = float(last_state.get("mana_max", prev_mana) or prev_mana)
    # Check bridge liveness every N polls (not every iteration — the status
    # HTTP call is cheap but still adds up at 4 Hz polling).
    bridge_check_interval = 8  # ~2 s at 250 ms poll_interval
    since_bridge_check = 0

    try:
        while step < max_steps:
            if cancel_event is not None and cancel_event.is_set():
                raise RunCancelled("run cancelled by user")

            events = _drain_agent_events(http_base)
            for ev in events:
                etype = ev.get("type", "")
                # Older bridges wrap named events as
                # {"type":"event","name":"human_game_over"}; normalise so
                # either form terminates the loop.
                if etype == "event" and ev.get("name", "").startswith("human_"):
                    etype = ev["name"]
                if etype == "human_step":
                    action = int(ev.get("action", -1))
                    if action < 0:
                        continue
                    command = action_to_command(action)
                    # The bridge serializes the post-action state into
                    # the same fields as a normal "state" message, so we
                    # can feed it straight through _state_to_obs.
                    obs = env._state_to_obs(ev)

                    mana = float(ev.get("mana", prev_mana) or prev_mana)
                    mana_max = float(ev.get("mana_max", prev_mana_max) or prev_mana_max)
                    reward = (mana - prev_mana) / 100.0
                    if mana_max > prev_mana_max:
                        reward += 0.1
                    if ev.get("game_over", False) and mana <= 0:
                        reward -= 1.0
                    total_reward += reward

                    terminated = bool(ev.get("game_over", False))
                    info = {
                        "raw_state": ev,
                        "max_mana": mana_max,
                        "surplus": mana_max - INITIAL_MANA,
                        "step": step + 1,
                    }

                    if replay_logger:
                        replay_logger.log_step(
                            action=action,
                            command=command,
                            observation=obs,
                            reward=reward,
                            terminated=terminated,
                            truncated=False,
                            info=info,
                            fallback_reason=None,
                            raw_state=ev,
                        )

                    prev_mana = mana
                    prev_mana_max = mana_max
                    last_state = ev
                    step += 1
                    if terminated or step >= max_steps:
                        break

                elif etype == "human_game_over":
                    terminated = True

                elif etype == "human_step_missed":
                    logger.warning(
                        "  human_step_missed: action=%s reason=%s",
                        ev.get("action"), ev.get("reason"),
                    )

            if terminated:
                break

            # Liveness probe: if the bridge is down, no events can ever
            # arrive — exit with a synthetic terminal state rather than
            # hanging the run forever.
            since_bridge_check += 1
            if since_bridge_check >= bridge_check_interval:
                since_bridge_check = 0
                if not _bridge_alive(http_base):
                    logger.warning(
                        "  bridge disconnected mid-recording — ending episode "
                        "(logged %d steps)", step,
                    )
                    terminated = True
                    break

            time.sleep(poll_interval)
    finally:
        try:
            env._send_command({"type": "set_recording_mode", "recording_mode": False})
        except Exception:  # pragma: no cover — best-effort cleanup
            logger.exception("failed to clear recording_mode; ignoring")

        if replay_logger:
            replay_logger.end_episode(last_state)

    return {
        "max_mana": prev_mana_max,
        "surplus": prev_mana_max - INITIAL_MANA,
        "total_reward": total_reward,
        "steps": step,
        "game_over": terminated,
        "diagnostics": {
            "wasted_draws": 0,
            "merge_tiers_chosen": {},
            "sell_by_merges": {},
            "previews_available": 0,
            "previews_followed": 0,
            "mana_trajectory": [],
            "merge_details": [],
        },
        "episode_log_path": str(replay_logger.episode_dir) if replay_logger and replay_logger.episode_dir else None,
    }


def run_episode(
    env,
    agent,
    replay_logger=None,
    max_steps: int = 200,
    cancel_event=None,
) -> dict:
    """Run a single episode and return results.

    Args:
        cancel_event: optional ``threading.Event`` (or anything with
            ``is_set()``). Checked before each step so a Cancel click in the
            UI can interrupt a long-running episode within a step boundary
            instead of having to wait for the whole episode to finish.
    """
    if getattr(agent, "is_human", False):
        return _run_episode_human(
            env, agent, replay_logger,
            max_steps=max_steps,
            cancel_event=cancel_event,
        )

    agent.reset()
    obs, info = env.reset()

    if replay_logger:
        replay_logger.start_episode(
            config=env.game_config,
            agent_name=agent.name,
        )

    total_reward = 0
    step = 0

    # ---- Diagnostic counters (benchmark quality tracking) ----
    diag_wasted_draws = 0      # draws that produced no card
    diag_merge_tiers = {}      # {tier: count} of merges executed
    diag_sell_by_merges = {}   # {merges_done: count} of sells
    diag_previews_available = 0  # turns where previews existed
    diag_previews_followed = 0   # turns where chosen action matched a preview
    diag_mana_trajectory = []    # mana value after each step
    diag_merge_details = []      # per-merge dimension gains
    prev_raw_state = info.get("raw_state", {})

    # Active dimensions for this config — needed to filter merge preview
    # gains.  Inactive dims always report gain=0, which would drag the
    # min-tier to "neutral" even when the active dim is GREAT.
    _active_dims = []
    _dim_to_gain = {"number": "number_gain", "color": "color_gain",
                    "shape": "shape_gain", "word": "word_gain"}
    for dim_key in ("number", "color", "shape", "word"):
        if env.game_config.get("modes", {}).get(dim_key):
            _active_dims.append(_dim_to_gain[dim_key])

    while step < max_steps:
        # Honour cancel BEFORE an LLM call so we can short-circuit a long
        # run within one step boundary. The LLM call itself is not
        # interruptible mid-flight (rate-limit retries excepted, see
        # LiteLLMProvider), so the worst-case stall is one provider call.
        if cancel_event is not None and cancel_event.is_set():
            raise RunCancelled("run cancelled by user")

        action = agent.act(obs, info)
        command = action_to_command(action)

        # LLMAgent sets _last_action_fallback_reason on its silent-fallback
        # path (provider crash etc.). Propagate to the replay log so offline
        # analysis can distinguish real model picks from salvaged defaults.
        fallback_reason = getattr(agent, "_last_action_fallback_reason", None)

        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward

        # ---- Diagnostic tracking ----
        # NOTE: step has NOT been incremented yet — diagnostics record the
        # step number at which the action was *decided*, matching events.jsonl.
        raw = info.get("raw_state", {})
        # Mana trajectory
        step_mana = raw.get("mana", 0)
        if isinstance(step_mana, (int, float)):
            diag_mana_trajectory.append(float(step_mana))
        # Wasted draw: action was draw but new slot is still empty
        if action == 0:
            slots = raw.get("slots") or []
            new_slot = slots[0] if slots else {}
            if isinstance(new_slot, dict) and not new_slot.get("occupied", False):
                diag_wasted_draws += 1
        # Sell: record how many merges the sold card had
        if 31 <= action <= 36:
            slot_idx = action - 31
            prev_slots = prev_raw_state.get("slots") or []
            if slot_idx < len(prev_slots):
                s = prev_slots[slot_idx]
                if isinstance(s, dict) and s.get("occupied"):
                    mc = int(s.get("merges_done", 0) or 0)
                    diag_sell_by_merges[mc] = diag_sell_by_merges.get(mc, 0) + 1
        # Merge previews: check if model followed them
        previews = prev_raw_state.get("merge_previews") or []
        if previews:
            diag_previews_available += 1
            preview_actions = {p.get("action") for p in previews if p.get("action") is not None}
            if action in preview_actions:
                diag_previews_followed += 1
                # Record which tier was chosen — use the MINIMUM gain
                # across ACTIVE dimensions only (the bottleneck dimension
                # determines merge quality).  Inactive dims always report
                # gain=0, so including them would drag every merge to
                # "neutral" regardless of actual quality.
                _tier_map = {3: "PERFECT", 2: "GREAT", 1: "GOOD",
                             0: "neutral", -1: "BAD"}
                for p in previews:
                    if p.get("action") == action:
                        dim_gains = {}
                        for field in _active_dims:
                            if p.get(field) is not None:
                                dim_gains[field] = int(p[field])
                        gains = list(dim_gains.values())
                        if gains:
                            min_gain = min(gains)
                            tier_name = _tier_map.get(min_gain, f"tier{min_gain}")
                            diag_merge_tiers[tier_name] = diag_merge_tiers.get(tier_name, 0) + 1
                            diag_merge_details.append({
                                "step": step,
                                "action": action,
                                "tier": tier_name,
                                "dim_gains": dim_gains,
                            })
                        break
        prev_raw_state = raw
        step += 1

        agent.on_step_result(action, reward, terminated, info)

        if replay_logger:
            replay_logger.log_step(
                action=action,
                command=command,
                observation=obs,
                reward=reward,
                terminated=terminated,
                truncated=truncated,
                info=info,
                fallback_reason=fallback_reason,
                raw_state=raw,
            )
            # Log screenshots at key moments
            screenshot = info.get("screenshot")
            if screenshot is not None and step % 10 == 0:
                replay_logger.log_screenshot(screenshot)

        if terminated or truncated:
            break

    if replay_logger:
        replay_logger.end_episode(info.get("raw_state"))

    return {
        "max_mana": info.get("max_mana", 0),
        "surplus": info.get("surplus", 0),
        "total_reward": total_reward,
        "steps": step,
        "game_over": terminated,
        "diagnostics": {
            "wasted_draws": diag_wasted_draws,
            "merge_tiers_chosen": diag_merge_tiers,
            "sell_by_merges": diag_sell_by_merges,
            "previews_available": diag_previews_available,
            "previews_followed": diag_previews_followed,
            "mana_trajectory": diag_mana_trajectory,
            "merge_details": diag_merge_details,
        },
        "episode_log_path": str(replay_logger.episode_dir) if replay_logger and replay_logger.episode_dir else None,
    }


def run_benchmark(
    agent_type: str,
    config_names: list,
    episodes_per_config: int = 5,
    server_url: str = "ws://localhost:8000/ws/agent",
    log_dir: str = "./logs",
    agent_kwargs: dict = None,
    max_steps: int = 100,
):
    """Run a full benchmark suite."""
    agent_kwargs = agent_kwargs or {}
    replay_logger = ReplayLogger(log_dir=log_dir)

    # Determine env class: screenshot agents need VLM env
    use_vlm = "vision" in agent_type
    env_cls = YediVLMEnv if use_vlm else YediEnv

    results = {}

    for config_name in config_names:
        if config_name not in ALL_BENCHMARKS:
            logger.warning(f"Unknown config: {config_name}, skipping")
            continue

        modes = ALL_BENCHMARKS[config_name]

        # Create agent per-config so the system prompt matches the active modes
        agent = create_agent(agent_type, game_modes=modes, **agent_kwargs)

        logger.info(f"\n{'='*60}")
        logger.info(f"Benchmark: {config_name} ({modes})")
        logger.info(f"Agent: {agent.name}")
        logger.info(f"{'='*60}")

        episode_results = []
        env = env_cls(
            server_url=server_url,
            game_config={"modes": modes},
            max_steps=max_steps,
        )

        for ep in range(episodes_per_config):
            logger.info(f"  Episode {ep+1}/{episodes_per_config}...")
            result = run_episode(env, agent, replay_logger, max_steps=max_steps * 2)
            episode_results.append(result)
            logger.info(f"  -> Surplus: {result['surplus']}, steps: {result['steps']}")

        env.close()

        # Aggregate
        surpluses = [r["surplus"] for r in episode_results]
        results[config_name] = {
            "mean_surplus": float(np.mean(surpluses)),
            "std_surplus": float(np.std(surpluses)),
            "max_surplus": float(np.max(surpluses)),
            "episodes": episode_results,
        }

        logger.info(f"  Summary: mean_surplus={results[config_name]['mean_surplus']:.0f} "
                     f"std={results[config_name]['std_surplus']:.0f} "
                     f"best={results[config_name]['max_surplus']:.0f}")

    # Save results
    results_path = Path(log_dir) / f"benchmark_{agent_type}_{int(time.time())}.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump({
            "agent": agent_type,
            "agent_kwargs": {k: v for k, v in (agent_kwargs or {}).items()
                             if isinstance(v, (str, int, float, bool))},
            "max_steps": max_steps,
            "timestamp": time.time(),
            "configs": config_names,
            "results": results,
        }, f, indent=2)
    logger.info(f"\nResults saved to: {results_path}")

    return results


class RunCancelled(Exception):
    """Raised inside run_benchmark_with_registry when cancel_event is set."""


class _ConfigStats:
    """Mutable counters accumulated across configs, thread-safe for parallel use."""

    def __init__(self):
        import threading
        self._lock = threading.Lock()
        self.successful_episodes = 0
        self.failed_episodes = 0
        self.last_bridge_error: Optional[str] = None

    def record_success(self):
        with self._lock:
            self.successful_episodes += 1

    def record_failure(self, error_msg: str):
        with self._lock:
            self.failed_episodes += 1
            self.last_bridge_error = error_msg


def _safe_close(e):
    try:
        e.close()
    except Exception:
        logger.exception("env.close raised; ignoring")


def _run_single_config(
    cfg_name: str,
    modes: dict,
    agent_cfg,
    prompt,
    mode_enum,
    env_cls,
    server_url: str,
    replay_logger,
    trace,
    record_id: str,
    rr,
    episodes_per_config: int,
    max_steps: int,
    cancel_event,
    show_merge_previews: bool,
    perfect_memory: bool,
    is_llm: bool,
    stats: _ConfigStats,
    command_timeout: float = 30.0,
) -> None:
    """Run all episodes for a single config, recording results into the RunRecord.

    Designed to be called from both the sequential and parallel paths.

    Args:
        command_timeout: per-command WS timeout in seconds. The parallel
            path passes 120s to tolerate hidden-tab throttling; the
            sequential (single-worker) path uses the default 30s.
    """
    from .registries import EpisodeResult
    from datetime import datetime, timezone

    def _now_iso():
        return datetime.now(timezone.utc).isoformat()

    def _check_cancel():
        if cancel_event is not None and cancel_event.is_set():
            raise RunCancelled("run cancelled by user")

    def _make_env(modes_dict):
        return env_cls(
            server_url=server_url,
            game_config={
                "modes": modes_dict,
                "perfect_memory": perfect_memory,
            },
            max_steps=max_steps,
            command_timeout=command_timeout,
        )

    _check_cancel()

    # Per-config closure that captures the current episode index.
    ep_state = {"episode": 0, "system_prompt": None}

    # Per-config replay logger — in the parallel path each thread needs its own
    # logger to avoid cross-thread file handle conflicts. Create a fresh one
    # sharing the same log directory.
    config_replay = ReplayLogger(log_dir=replay_logger.log_dir)

    def _on_exchange(*, user_text, response, action, latency_ms,
                      error, step_in_episode, _cfg=cfg_name):
        trace.record(
            config=_cfg,
            episode=ep_state["episode"],
            step=step_in_episode,
            user_text=user_text,
            response=response,
            action=action,
            latency_ms=latency_ms,
            error=error,
        )
        try:
            config_replay.log_exchange(
                step_in_episode=step_in_episode,
                user_text=user_text,
                response=response,
                action=action,
                latency_ms=latency_ms,
                error=error,
                system_prompt=ep_state["system_prompt"],
                fallback_reason=(
                    f"llm_error: {error}" if error else None
                ),
            )
        except Exception:
            logger.exception("replay_logger.log_exchange raised; ignoring")

    on_exchange = _on_exchange if is_llm else None

    should_cancel = (
        (lambda: cancel_event.is_set()) if cancel_event is not None else None
    )

    agent = create_agent_from_registry(
        agent_cfg, prompt, mode_enum,
        game_modes=modes, on_exchange=on_exchange,
        should_cancel=should_cancel,
        show_merge_previews=show_merge_previews,
    )

    if is_llm and hasattr(agent, "_system_prompt"):
        if trace is not None:
            trace.set_system_prompt(cfg_name, agent._system_prompt)
        ep_state["system_prompt"] = agent._system_prompt

    logger.info(f"\n{'='*60}\nBenchmark: {cfg_name} ({modes})\nAgent: {agent.name}\n{'='*60}")

    consecutive_bridge_failures = 0
    env = _make_env(modes)

    try:
        for ep_idx in range(episodes_per_config):
            _check_cancel()
            ep_state["episode"] = ep_idx
            logger.info(f"  Episode {ep_idx+1}/{episodes_per_config}...")
            ep_started = _now_iso()

            try:
                result = run_episode(
                    env, agent, config_replay,
                    max_steps=max_steps * 2,
                    cancel_event=cancel_event,
                )
            except BridgeDisconnectedError as bde:
                consecutive_bridge_failures += 1
                err_msg = str(bde)
                stats.record_failure(err_msg)
                logger.warning(
                    "  Episode %d/%d FAILED (bridge): %s",
                    ep_idx + 1, episodes_per_config, err_msg,
                )
                rr.record_episode_error(
                    record_id, cfg_name, ep_idx, err_msg,
                )
                if consecutive_bridge_failures >= MAX_CONSECUTIVE_BRIDGE_FAILURES:
                    raise BridgeDisconnectedError(
                        f"aborting config {cfg_name} after "
                        f"{consecutive_bridge_failures} consecutive "
                        f"bridge failures: {err_msg}"
                    ) from bde
                _safe_close(env)
                env = _make_env(modes)
                continue

            rr.append_episode(
                record_id,
                cfg_name,
                EpisodeResult(
                    episode_idx=ep_idx,
                    max_mana=float(result["max_mana"]),
                    surplus=float(result["surplus"]),
                    total_reward=float(result["total_reward"]),
                    steps=int(result["steps"]),
                    game_over=bool(result["game_over"]),
                    started_at=ep_started,
                    finished_at=_now_iso(),
                    diagnostics=result.get("diagnostics"),
                    episode_log_path=result.get("episode_log_path"),
                ),
            )
            consecutive_bridge_failures = 0
            stats.record_success()
            logger.info(
                f"  -> Surplus: {result['surplus']}, steps: {result['steps']}"
            )
    finally:
        _safe_close(env)


def _run_configs_sequential(
    config_modes: dict,
    agent_cfg,
    prompt,
    mode_enum,
    env_cls,
    server_url: str,
    replay_logger,
    trace,
    record_id: str,
    rr,
    episodes_per_config: int,
    max_steps: int,
    cancel_event,
    show_merge_previews: bool,
    perfect_memory: bool,
    is_llm: bool,
) -> _ConfigStats:
    """Run all configs sequentially on a single server. Returns stats."""
    stats = _ConfigStats()
    for cfg_name, modes in config_modes.items():
        _run_single_config(
            cfg_name=cfg_name,
            modes=modes,
            agent_cfg=agent_cfg,
            prompt=prompt,
            mode_enum=mode_enum,
            env_cls=env_cls,
            server_url=server_url,
            replay_logger=replay_logger,
            trace=trace,
            record_id=record_id,
            rr=rr,
            episodes_per_config=episodes_per_config,
            max_steps=max_steps,
            cancel_event=cancel_event,
            show_merge_previews=show_merge_previews,
            perfect_memory=perfect_memory,
            is_llm=is_llm,
            stats=stats,
        )
    return stats


def _finalize_run(record, rr, stats: _ConfigStats):
    """Mark the run as COMPLETED or FAILED based on aggregated stats."""
    from .registries import RunStatus

    if stats.successful_episodes == 0 and stats.failed_episodes > 0:
        rr.set_error(
            record.id,
            f"all {stats.failed_episodes} episodes failed; "
            f"last error: {stats.last_bridge_error}",
        )
        return rr.get(record.id)

    final = rr.update_status(record.id, RunStatus.COMPLETED)
    logger.info(
        "\nRun %s COMPLETED — %d/%d episodes ok, %d bridge errors",
        record.id, stats.successful_episodes, record.episodes_total(),
        stats.failed_episodes,
    )
    return final


def run_benchmark_with_registry(
    agent_id: str,
    prompt_id: str = None,
    mode: str = "metadata-b",
    config_names: list = None,
    episodes_per_config: int = 5,
    server_url: str = "ws://localhost:8000/ws/agent",
    log_dir: str = "./logs",
    max_steps: int = 100,
    cancel_event=None,
    show_merge_previews: bool = False,
    perfect_memory: bool = False,
    workers: int = 1,
):
    """Registry-driven benchmark run.

    Looks up the AgentConfig + Prompt from the local registries, creates a
    persistent RunRecord (visible to the web UI), and appends episode results
    as they complete. The run is marked COMPLETED on success, CANCELLED if
    `cancel_event` is set, or FAILED with an error message on any other
    exception.

    Args:
        cancel_event: optional threading.Event. Checked before each config and
            after each episode; if set, a RunCancelled exception is raised and
            the run record is marked CANCELLED.
        show_merge_previews: per-run ablation — when True, the LLM agent
            renders the bridge's pre-computed merge_previews in its state
            description. Default False (canonical benchmark).
        perfect_memory: per-run ablation — when True, the bridge ships hidden
            card values + previews regardless of Memory mode. Default False
            (Memory dimension stays meaningful).
        workers: number of parallel worker servers. When > 1, the run
            delegates to ``parallel_runner.run_benchmark_parallel()`` which
            spawns N server+browser subprocesses and dispatches configs across
            them via a shared work queue.
    """
    from .registries import (
        AgentRegistry,
        PromptRegistry,
        RunRegistry,
        AgentMode,
        EpisodeResult,
        RunStatus,
    )
    from datetime import datetime, timezone

    def _now_iso():
        return datetime.now(timezone.utc).isoformat()

    def _check_cancel():
        if cancel_event is not None and cancel_event.is_set():
            raise RunCancelled("run cancelled by user")

    ar = AgentRegistry()
    pr = PromptRegistry()
    rr = RunRegistry()

    agent_cfg = ar.get(agent_id)

    # Resolve the prompt: explicit > active > none (programmatic baselines only).
    if prompt_id:
        prompt = pr.get(prompt_id)
    elif agent_cfg.provider not in ("random", "greedy"):
        prompt = pr.get_active()
    else:
        prompt = None

    mode_enum = AgentMode(mode)

    # Resolve and order config names (drop unknowns with a warning).
    if not config_names:
        raise ValueError("config_names must be non-empty")
    valid_configs = []
    for name in config_names:
        if name in ALL_BENCHMARKS:
            valid_configs.append(name)
        else:
            logger.warning(f"Unknown config: {name}, skipping")
    if not valid_configs:
        raise ValueError("No valid configs to run")

    config_modes = {name: ALL_BENCHMARKS[name] for name in valid_configs}

    # Create the run record (snapshots agent + prompt at this moment).
    record = rr.create(
        agent=agent_cfg,
        prompt=prompt,
        configs=valid_configs,
        episodes_per_config=episodes_per_config,
        max_steps=max_steps,
        mode=mode_enum,
        config_modes=config_modes,
        show_merge_previews=show_merge_previews,
        perfect_memory=perfect_memory,
        workers=workers,
    )
    rr.update_status(record.id, RunStatus.RUNNING)
    logger.info(f"Created run {record.id} (agent={agent_cfg.name}, mode={mode_enum.value})")

    use_vlm = mode_enum.use_screenshot
    env_cls = YediVLMEnv if use_vlm else YediEnv
    replay_logger = ReplayLogger(log_dir=log_dir)

    # Live trace store — used by the dashboard's Run page to stream LLM
    # thinking. We only create the trace for actual LLM agents; random and
    # greedy never produce exchanges, and creating an empty trace would
    # leave the dashboard's poll loop stuck on "Waiting for the model's
    # first move…" forever (the JS distinguishes "no trace" from "trace
    # exists but no entries yet").
    is_llm = agent_cfg.provider not in ("random", "greedy")
    trace = None
    if is_llm:
        from .run_trace import get_run_trace_store
        trace = get_run_trace_store().get_or_create(record.id)

    # ---- parallel path ----
    if workers > 1:
        from .parallel_runner import run_benchmark_parallel
        return run_benchmark_parallel(
            record=record,
            config_modes=config_modes,
            agent_cfg=agent_cfg,
            prompt=prompt,
            mode_enum=mode_enum,
            env_cls=env_cls,
            replay_logger=replay_logger,
            trace=trace,
            rr=rr,
            episodes_per_config=episodes_per_config,
            max_steps=max_steps,
            cancel_event=cancel_event,
            show_merge_previews=show_merge_previews,
            perfect_memory=perfect_memory,
            is_llm=is_llm,
            n_workers=workers,
        )

    # ---- sequential path ----
    try:
        stats = _run_configs_sequential(
            config_modes=config_modes,
            agent_cfg=agent_cfg,
            prompt=prompt,
            mode_enum=mode_enum,
            env_cls=env_cls,
            server_url=server_url,
            replay_logger=replay_logger,
            trace=trace,
            record_id=record.id,
            rr=rr,
            episodes_per_config=episodes_per_config,
            max_steps=max_steps,
            cancel_event=cancel_event,
            show_merge_previews=show_merge_previews,
            perfect_memory=perfect_memory,
            is_llm=is_llm,
        )
        return _finalize_run(record, rr, stats)

    except RunCancelled:
        logger.info(f"Run {record.id} CANCELLED")
        rr.update_status(record.id, RunStatus.CANCELLED)
        return rr.get(record.id)

    except Exception as e:
        from .providers.base import ProviderCancelled
        if isinstance(e, ProviderCancelled):
            logger.info(f"Run {record.id} CANCELLED (during provider call)")
            rr.update_status(record.id, RunStatus.CANCELLED)
            return rr.get(record.id)
        logger.error(f"Run {record.id} FAILED: {e}", exc_info=True)
        rr.set_error(record.id, str(e))
        raise


def main():
    parser = argparse.ArgumentParser(description="Yedi AI Benchmark Runner")

    # Legacy path
    parser.add_argument("--agent", default=None, choices=AGENT_TYPES,
                        help="(legacy) Agent type by string name")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="(legacy) LLM model ID for claude-* agents")

    # Registry-driven path
    parser.add_argument("--agent-id", default=None,
                        help="AgentConfig id from the registry (e.g. agent_xxxxxx)")
    parser.add_argument("--prompt-id", default=None,
                        help="Prompt id from the registry; defaults to the active prompt")
    parser.add_argument("--mode", default="metadata-b",
                        choices=["metadata-a", "metadata-b", "vision-a", "vision-b"],
                        help="Observation/memory mode (registry path only)")

    # Common
    parser.add_argument("--configs", default="easy_math_add",
                        help="Comma-separated config names, or tier: EASY, MEDIUM, HARD, BRAINFRY, ALL")
    parser.add_argument("--episodes", type=int, default=5,
                        help="Episodes per config (default: 5)")
    parser.add_argument("--server", default="ws://localhost:8000/ws/agent",
                        help="WebSocket server URL")
    parser.add_argument("--log-dir", default="./logs",
                        help="Directory for result logs")
    parser.add_argument("--max-steps", type=int, default=100,
                        help="Max actions per episode (default: 100)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel worker servers (default: 1 = sequential). "
                             "Each worker spawns its own server + browser tab.")

    args = parser.parse_args()

    if args.agent and args.agent_id:
        parser.error("Use either --agent (legacy) or --agent-id (registry), not both")
    if not args.agent and not args.agent_id:
        parser.error("Must specify --agent (legacy) or --agent-id (registry)")

    # Resolve config names — support tier names (EASY, MEDIUM, HARD, BRAINFRY, ALL)
    configs_upper = args.configs.upper()
    if configs_upper == "ALL":
        config_names = list(ALL_BENCHMARKS.keys())
    elif configs_upper in TIERS:
        config_names = list(TIERS[configs_upper].keys())
    else:
        config_names = [c.strip() for c in args.configs.split(",")]

    if args.agent_id:
        run_benchmark_with_registry(
            agent_id=args.agent_id,
            prompt_id=args.prompt_id,
            mode=args.mode,
            config_names=config_names,
            episodes_per_config=args.episodes,
            server_url=args.server,
            log_dir=args.log_dir,
            max_steps=args.max_steps,
            workers=args.workers,
        )
    else:
        run_benchmark(
            agent_type=args.agent,
            config_names=config_names,
            episodes_per_config=args.episodes,
            server_url=args.server,
            log_dir=args.log_dir,
            agent_kwargs={"model": args.model},
            max_steps=args.max_steps,
        )


if __name__ == "__main__":
    main()
