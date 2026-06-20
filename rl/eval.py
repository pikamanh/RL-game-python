from __future__ import annotations

import sys

import ray
from ray.rllib.algorithms.ppo import PPO

from mappo import register_multiagent_env


def main():
    checkpoint = sys.argv[1] if len(sys.argv) > 1 else None
    ray.init(ignore_reinit_error=True, include_dashboard=False)
    register_multiagent_env()

    if checkpoint:
        algo = PPO.from_checkpoint(checkpoint)
    else:
        raise SystemExit("Pass a Ray checkpoint directory, for example: python rl/eval.py checkpoints/...")

    env = algo.workers.local_worker().env
    episodes = 20
    wins = 0
    rewards = []
    lengths = []

    for _ in range(episodes):
        obs, _ = env.reset()
        total_reward = 0.0
        steps = 0
        while True:
            actions = {
                agent_id: algo.compute_single_action(agent_obs, policy_id="shared_policy")
                for agent_id, agent_obs in obs.items()
            }
            obs, reward, terminated, truncated, info = env.step(actions)
            total_reward += reward["fireboy"] + reward["watergirl"]
            steps += 1
            if terminated["__all__"] or truncated["__all__"]:
                wins += int(info.get("win", False))
                rewards.append(total_reward)
                lengths.append(steps)
                break

    print(
        {
            "win_rate": wins / episodes,
            "avg_reward": sum(rewards) / len(rewards),
            "avg_len": sum(lengths) / len(lengths),
        }
    )


if __name__ == "__main__":
    main()
