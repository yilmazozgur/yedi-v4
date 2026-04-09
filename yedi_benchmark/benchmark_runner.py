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

from .yedi_env import YediEnv, BridgeDisconnectedError, action_to_command
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
    agent.reset()
    obs, info = env.reset()

    if replay_logger:
        replay_logger.start_episode(
            config=env.game_config,
            agent_name=agent.name,
        )

    total_reward = 0
    step = 0

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
        "total_reward": total_reward,
        "steps": step,
        "game_over": terminated,
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
            logger.info(f"  -> Max mana: {result['max_mana']}, steps: {result['steps']}")

        env.close()

        # Aggregate
        max_manas = [r["max_mana"] for r in episode_results]
        results[config_name] = {
            "mean_max_mana": float(np.mean(max_manas)),
            "std_max_mana": float(np.std(max_manas)),
            "max_max_mana": float(np.max(max_manas)),
            "episodes": episode_results,
        }

        logger.info(f"  Summary: mean={results[config_name]['mean_max_mana']:.0f} "
                     f"std={results[config_name]['std_max_mana']:.0f} "
                     f"best={results[config_name]['max_max_mana']:.0f}")

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

    # Counters used to decide when bridge failures have become a
    # run-level death rather than a transient blip. Reset on every
    # successful episode. ``failed_episodes`` is also tracked locally
    # because the ``record`` variable above is a stale snapshot taken at
    # create time — refreshing from disk for every check would be wasteful.
    consecutive_bridge_failures = 0
    successful_episodes = 0
    failed_episodes = 0
    last_bridge_error: Optional[str] = None

    def _make_env_for(modes):
        return env_cls(
            server_url=server_url,
            game_config={
                "modes": modes,
                "perfect_memory": perfect_memory,
            },
            max_steps=max_steps,
        )

    def _safe_close(e):
        try:
            e.close()
        except Exception:  # pragma: no cover — close is best-effort
            logger.exception("env.close raised; ignoring")

    try:
        for cfg_name, modes in config_modes.items():
            _check_cancel()

            # Per-config closure that captures the current episode index
            # via a mutable holder. The agent only knows step_in_episode;
            # the runner advances ep_state["episode"] before each episode.
            ep_state = {"episode": 0, "system_prompt": None}

            def _on_exchange(*, user_text, response, action, latency_ms,
                              error, step_in_episode, _cfg=cfg_name):
                # 1. In-memory live trace (feeds the dashboard trace view).
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
                # 2. Persistent per-episode trace.jsonl. Writing through the
                # replay_logger here (rather than inside run_episode) means
                # every LLM call — including the fallback path where the
                # runner never sees the error — lands on disk.
                try:
                    replay_logger.log_exchange(
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
                except Exception:  # pragma: no cover — never let disk I/O break a run
                    logger.exception("replay_logger.log_exchange raised; ignoring")

            on_exchange = _on_exchange if is_llm else None

            # Closure the LLM provider checks during long backoff sleeps so a
            # Cancel click in the dashboard breaks out within ~1s instead of
            # waiting up to 120s for a rate-limit retry.
            should_cancel = (
                (lambda: cancel_event.is_set()) if cancel_event is not None else None
            )

            # New agent per config so the system prompt is rebuilt for the active modes.
            agent = create_agent_from_registry(
                agent_cfg, prompt, mode_enum,
                game_modes=modes, on_exchange=on_exchange,
                should_cancel=should_cancel,
                show_merge_previews=show_merge_previews,
            )

            # Capture the system prompt that this agent will use for this
            # config so the dashboard can show it once at the top. We also
            # stash it in ep_state so the _on_exchange closure can stamp
            # it into each episode's trace.jsonl header.
            if is_llm and hasattr(agent, "_system_prompt"):
                trace.set_system_prompt(cfg_name, agent._system_prompt)
                ep_state["system_prompt"] = agent._system_prompt

            logger.info(f"\n{'='*60}\nBenchmark: {cfg_name} ({modes})\nAgent: {agent.name}\n{'='*60}")

            env = _make_env_for(modes)

            try:
                for ep_idx in range(episodes_per_config):
                    _check_cancel()
                    ep_state["episode"] = ep_idx
                    logger.info(f"  Episode {ep_idx+1}/{episodes_per_config}...")
                    ep_started = _now_iso()

                    try:
                        result = run_episode(
                            env, agent, replay_logger,
                            max_steps=max_steps * 2,
                            cancel_event=cancel_event,
                        )
                    except BridgeDisconnectedError as bde:
                        # The browser bridge died (timeout, ws closed, ASGI
                        # send error). Don't take down the whole run — record
                        # the failure, recreate the env so the next episode
                        # gets a fresh ws connection, and keep going.
                        consecutive_bridge_failures += 1
                        failed_episodes += 1
                        err_msg = str(bde)
                        last_bridge_error = err_msg
                        logger.warning(
                            "  Episode %d/%d FAILED (bridge): %s",
                            ep_idx + 1, episodes_per_config, err_msg,
                        )
                        rr.record_episode_error(
                            record.id, cfg_name, ep_idx, err_msg,
                        )
                        if consecutive_bridge_failures >= MAX_CONSECUTIVE_BRIDGE_FAILURES:
                            raise BridgeDisconnectedError(
                                f"aborting run after "
                                f"{consecutive_bridge_failures} consecutive "
                                f"bridge failures: {err_msg}"
                            ) from bde
                        # Recreate the env so the next attempt starts from a
                        # clean ws connection. The old env may be holding a
                        # half-dead socket.
                        _safe_close(env)
                        env = _make_env_for(modes)
                        continue

                    rr.append_episode(
                        record.id,
                        cfg_name,
                        EpisodeResult(
                            episode_idx=ep_idx,
                            max_mana=float(result["max_mana"]),
                            total_reward=float(result["total_reward"]),
                            steps=int(result["steps"]),
                            game_over=bool(result["game_over"]),
                            started_at=ep_started,
                            finished_at=_now_iso(),
                        ),
                    )
                    consecutive_bridge_failures = 0
                    successful_episodes += 1
                    logger.info(
                        f"  -> Max mana: {result['max_mana']}, steps: {result['steps']}"
                    )
            finally:
                _safe_close(env)

        # Run finished its config loop. If at least one episode succeeded,
        # mark COMPLETED — the dashboard can show per-episode bridge errors
        # in the run detail. If literally nothing ran, mark FAILED with the
        # accumulated error so it doesn't masquerade as a successful empty
        # run.
        if successful_episodes == 0 and failed_episodes > 0:
            rr.set_error(
                record.id,
                f"all {failed_episodes} episodes failed; last error: {last_bridge_error}",
            )
            return rr.get(record.id)

        final = rr.update_status(record.id, RunStatus.COMPLETED)
        logger.info(
            "\nRun %s COMPLETED — %d/%d episodes ok, %d bridge errors",
            record.id, successful_episodes, record.episodes_total(),
            failed_episodes,
        )
        return final

    except RunCancelled:
        logger.info(f"Run {record.id} CANCELLED")
        rr.update_status(record.id, RunStatus.CANCELLED)
        return rr.get(record.id)

    except Exception as e:
        # ProviderCancelled bubbles up from LLMAgent when the user cancels
        # mid rate-limit-backoff. Treat it like a normal cancel, not a crash.
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
