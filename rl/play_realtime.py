from __future__ import annotations

import argparse

from rl.common import compute_action, ensure_ray, load_algorithm
from rl.env import AGENTS, FireWaterEnv


def parse_args():
    parser = argparse.ArgumentParser(description="Run a trained agent in real time with automatic reset.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--level", type=int, choices=[1, 2], default=1)
    parser.add_argument("--max-steps", type=int, default=3000)
    parser.add_argument("--explore", action="store_true")
    parser.add_argument("--shared-policy", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--step-size", type=float, default=5.0)
    parser.add_argument("--gravity", type=float, default=0.55)
    parser.add_argument("--jump-velocity", type=float, default=8.0)
    return parser.parse_args()


def main():
    args = parse_args()
    ensure_ray()
    algo = load_algorithm(args.checkpoint)
    env = FireWaterEnv({**vars(args), "render_mode": "human", "auto_reset_on_done": True})
    obs, _ = env.reset()

    try:
        running = True
        while running:
            actions = {
                agent: compute_action(algo, obs[agent], agent, args.shared_policy, explore=args.explore)
                for agent in AGENTS
            }
            obs, _, terminateds, truncateds, _ = env.step(actions)
            env.render()
            running = env.screen is not None
            if terminateds["__all__"] or truncateds["__all__"]:
                obs, _ = env.reset()
    finally:
        env.close()
        algo.stop()


if __name__ == "__main__":
    main()
