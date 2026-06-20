from __future__ import annotations

from pathlib import Path
from typing import Dict

import sys

RL_DIR = Path(__file__).resolve().parent
if str(RL_DIR) not in sys.path:
    sys.path.insert(0, str(RL_DIR))

from ray.rllib.algorithms.ppo import PPOConfig
from ray.tune.registry import register_env

from env import FireboyWatergirlEnv


def get_policy_config(env: FireboyWatergirlEnv):
    return {
        "shared_policy": (
            None,
            env.single_observation_space,
            env.single_action_space,
            {},
        )
    }


def build_config(env_name: str = "fireboy_watergirl"):
    env = FireboyWatergirlEnv({"level": 1, "max_steps": 500})
    return (
        PPOConfig()
        .environment(env=env_name, env_config={"level": 1, "max_steps": 500})
        .framework("torch")
        .env_runners(
            num_env_runners=0,
            create_local_env_runner=True,
            create_env_on_local_worker=True,
            rollout_fragment_length=64,
        )
        .training(
            gamma=0.98,
            lr=3e-4,
            train_batch_size=512,
            minibatch_size=128,
            num_epochs=4,
            model={"fcnet_hiddens": [128, 128], "fcnet_activation": "tanh"},
        )
        .fault_tolerance(restart_failed_sub_environments=True)
        .multi_agent(
            policies=get_policy_config(env),
            policy_mapping_fn=lambda agent_id, *args, **kwargs: "shared_policy",
            policies_to_train=["shared_policy"],
        )
    )


def register_multiagent_env(env_name: str = "fireboy_watergirl"):
    def _creator(config):
        return FireboyWatergirlEnv(config)

    register_env(env_name, _creator)
    return env_name


def build_algo(env_name: str = "fireboy_watergirl"):
    register_multiagent_env(env_name)
    config = build_config(env_name)
    return config.build_algo()
