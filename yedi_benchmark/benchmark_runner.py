"""
Benchmark Runner — run agents across multiple game configurations.

Usage:
    # Random baseline
    python -m yedi_benchmark.benchmark_runner --agent random --configs EASY --episodes 5

    # Claude metadata-only, stateless (Mode A)
    python -m yedi_benchmark.benchmark_runner --agent claude-meta-a --configs EASY --episodes 3

    # Claude metadata-only, conversational (Mode B)
    python -m yedi_benchmark.benchmark_runner --agent claude-meta-b --configs EASY --episodes 3

    # Claude screenshot, stateless (Mode A)
    python -m yedi_benchmark.benchmark_runner --agent claude-vision-a --configs EASY --episodes 3

    # Claude screenshot, conversational (Mode B)
    python -m yedi_benchmark.benchmark_runner --agent claude-vision-b --configs EASY --episodes 3

    # Cherry-pick games
    python -m yedi_benchmark.benchmark_runner --agent claude-meta-b --configs easy_math_add,med_math_gcd --episodes 5

    # Run everything
    python -m yedi_benchmark.benchmark_runner --agent claude-meta-b --configs ALL --episodes 1
"""

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

from .yedi_env import YediEnv, action_to_command
from .yedi_vlm_env import YediVLMEnv
from .replay_logger import ReplayLogger
from .benchmark_configs import TIERS, ALL_BENCHMARKS
from .agents.random_agent import RandomAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")

AGENT_TYPES = ["random", "claude-meta-a", "claude-meta-b", "claude-vision-a", "claude-vision-b"]


def create_agent(agent_type: str, game_modes: dict = None, **kwargs):
    """Factory for creating agents by name."""
    if agent_type == "random":
        return RandomAgent(seed=kwargs.get("seed"))

    if agent_type.startswith("claude-"):
        from .agents.llm_agent import LLMAgent

        # Parse: claude-{meta|vision}-{a|b}
        parts = agent_type.split("-")  # ["claude", "meta"|"vision", "a"|"b"]
        use_screenshot = parts[1] == "vision"
        mode = "stateless" if parts[2] == "a" else "conversational"

        return LLMAgent(
            model=kwargs.get("model", "claude-sonnet-4-20250514"),
            mode=mode,
            use_screenshot=use_screenshot,
            game_modes=game_modes or {},
            max_tokens=kwargs.get("max_tokens", 512),
        )

    raise ValueError(f"Unknown agent type: {agent_type}. Choose from: {AGENT_TYPES}")


def run_episode(env, agent, replay_logger=None, max_steps: int = 200) -> dict:
    """Run a single episode and return results."""
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
        action = agent.act(obs, info)
        command = action_to_command(action)

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


def main():
    parser = argparse.ArgumentParser(description="Yedi AI Benchmark Runner")
    parser.add_argument("--agent", default="random", choices=AGENT_TYPES,
                        help="Agent type")
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
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="LLM model ID (for claude agents)")
    args = parser.parse_args()

    # Resolve config names — support tier names (EASY, MEDIUM, HARD, BRAINFRY, ALL)
    configs_upper = args.configs.upper()
    if configs_upper == "ALL":
        config_names = list(ALL_BENCHMARKS.keys())
    elif configs_upper in TIERS:
        config_names = list(TIERS[configs_upper].keys())
    else:
        config_names = [c.strip() for c in args.configs.split(",")]

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
