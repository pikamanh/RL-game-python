from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import gymnasium as gym
import numpy as np
from ray.rllib.env.multi_agent_env import MultiAgentEnv


@dataclass
class AgentState:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    last_x: float = 0.0
    stuck_steps: int = 0


@dataclass
class LevelSpec:
    width: int
    height: int
    spawn_fire: Tuple[float, float]
    spawn_water: Tuple[float, float]
    door_fire: Tuple[float, float, float, float]
    door_water: Tuple[float, float, float, float]
    platforms: List[Tuple[float, float, float, float]]
    hazards_fire: List[Tuple[float, float, float, float]]
    hazards_water: List[Tuple[float, float, float, float]]
    hazards_neutral: List[Tuple[float, float, float, float]]
    fire_gems: List[Tuple[float, float]]
    water_gems: List[Tuple[float, float]]
    fire_goal_x: float
    water_goal_x: float


class FireboyWatergirlEnv(MultiAgentEnv):
    metadata = {"render_modes": []}
    ACTION_NOOP = 0
    ACTION_LEFT = 1
    ACTION_RIGHT = 2
    ACTION_JUMP = 3

    def __init__(self, config: Dict | None = None):
        super().__init__()
        config = config or {}
        self.level = int(config.get("level", 1))
        self.max_steps = int(config.get("max_steps", 500))
        self.level_spec = self._build_level_spec(self.level)

        self.fire_size = (25, 25)
        self.water_size = (25, 25)
        self.step_size = 5
        self.jump_velocity = 8.0
        self.gravity = 0.55
        self.max_fall_speed = 12.0
        self.time_penalty = 0.01
        self.progress_scale = 0.25
        self.goal_reward = 40.0
        self.gem_reward = 3.0
        self.death_penalty = -30.0
        self.idle_penalty = 0.05
        self.stuck_penalty = 0.15
        self.stuck_limit = 30

        self.single_action_space = gym.spaces.Discrete(4)
        self.single_observation_space = gym.spaces.Box(low=-1.0, high=1.0, shape=(14,), dtype=np.float32)
        self.action_space = self.single_action_space
        self.observation_space = self.single_observation_space
        self.observation_spaces = {
            "fireboy": self.single_observation_space,
            "watergirl": self.single_observation_space,
        }
        self.action_spaces = {
            "fireboy": self.single_action_space,
            "watergirl": self.single_action_space,
        }
        self.possible_agents = ["fireboy", "watergirl"]
        self.agents = self.possible_agents.copy()
        self.reset()

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed, options=options)
        self.steps = 0
        self.done = False
        self.win = False
        self.fire = AgentState(*self.level_spec.spawn_fire, last_x=self.level_spec.spawn_fire[0])
        self.water = AgentState(*self.level_spec.spawn_water, last_x=self.level_spec.spawn_water[0])
        self.fire_gems = list(self.level_spec.fire_gems)
        self.water_gems = list(self.level_spec.water_gems)
        self.fire_open = False
        self.water_open = False
        self.agents = self.possible_agents.copy()
        obs = self._get_obs()
        info = {"win": False, "terminated": False, "steps": 0}
        return obs, info

    def step(self, actions: Dict[str, int]):
        if self.done:
            obs = self._get_obs()
            terminateds = {"fireboy": True, "watergirl": True, "__all__": True}
            truncateds = {"fireboy": False, "watergirl": False, "__all__": False}
            infos = {"fireboy": {"win": self.win, "terminated": True, "truncated": False, "steps": self.steps},
                     "watergirl": {"win": self.win, "terminated": True, "truncated": False, "steps": self.steps},
                     "__common__": {"win": self.win, "terminated": True, "truncated": False, "steps": self.steps}}
            return obs, self._empty_rewards(), terminateds, truncateds, infos

        self.steps += 1
        fire_action = int(actions.get("fireboy", self.ACTION_NOOP))
        water_action = int(actions.get("watergirl", self.ACTION_NOOP))

        fire_prev_x = self.fire.x
        water_prev_x = self.water.x

        reward_fire = -self.time_penalty + self._apply_action(self.fire, fire_action)
        reward_water = -self.time_penalty + self._apply_action(self.water, water_action)

        fire_progress = self._progress(self.level_spec.fire_goal_x, self.fire.x)
        water_progress = self._progress(self.level_spec.water_goal_x, self.water.x)
        reward_fire += self.progress_scale * (fire_progress - self._progress(self.level_spec.fire_goal_x, fire_prev_x))
        reward_water += self.progress_scale * (water_progress - self._progress(self.level_spec.water_goal_x, water_prev_x))

        shared_progress = self._team_distance_delta(fire_prev_x, water_prev_x)
        reward_fire += 0.1 * shared_progress
        reward_water += 0.1 * shared_progress

        gem_fire, gem_water = self._collect_gems()
        reward_fire += gem_fire
        reward_water += gem_water

        if self._touch_goal(self.fire, self.level_spec.door_fire):
            self.fire_open = True
            reward_fire += 1.5
        if self._touch_goal(self.water, self.level_spec.door_water):
            self.water_open = True
            reward_water += 1.5

        terminated = False
        truncated = False
        if self._is_dead(self.fire, "fireboy") or self._is_dead(self.water, "watergirl"):
            reward_fire += self.death_penalty
            reward_water += self.death_penalty
            terminated = True
            self.done = True
        elif self.fire_open and self.water_open:
            reward_fire += self.goal_reward
            reward_water += self.goal_reward
            terminated = True
            self.win = True
            self.done = True
        elif self.steps >= self.max_steps:
            truncated = True
            self.done = True

        if self.done:
            self.agents = []

        if abs(self.fire.x - fire_prev_x) < 0.1:
            reward_fire -= self.idle_penalty
            self.fire.stuck_steps += 1
        else:
            self.fire.stuck_steps = 0
        if abs(self.water.x - water_prev_x) < 0.1:
            reward_water -= self.idle_penalty
            self.water.stuck_steps += 1
        else:
            self.water.stuck_steps = 0

        if self.fire.stuck_steps > self.stuck_limit:
            reward_fire -= self.stuck_penalty
        if self.water.stuck_steps > self.stuck_limit:
            reward_water -= self.stuck_penalty

        obs = self._get_obs()
        rewards = {"fireboy": float(reward_fire), "watergirl": float(reward_water)}
        terminateds = {
            "fireboy": terminated,
            "watergirl": terminated,
            "__all__": terminated,
        }
        truncateds = {
            "fireboy": truncated,
            "watergirl": truncated,
            "__all__": truncated,
        }
        infos = {
            "fireboy": {"win": self.win, "terminated": terminated, "truncated": truncated, "steps": self.steps},
            "watergirl": {"win": self.win, "terminated": terminated, "truncated": truncated, "steps": self.steps},
            "__common__": {"win": self.win, "terminated": terminated, "truncated": truncated, "steps": self.steps},
        }
        return obs, rewards, terminateds, truncateds, infos

    def render(self):
        raise NotImplementedError("Rendering is not implemented in the RL env.")

    def _build_level_spec(self, level: int) -> LevelSpec:
        if level == 1:
            return LevelSpec(
                width=1100,
                height=817,
                spawn_fire=(60, 790),
                spawn_water=(60, 620),
                door_fire=(910, 85, 77, 83),
                door_water=(995, 85, 74, 85),
                platforms=[
                    (0, 792, 1100, 10),
                    (10, 680, 350, 20),
                    (190, 424, 365, 20),
                    (1020, 710, 50, 20),
                    (10, 200, 140, 140),
                    (505, 623, 425, 20),
                    (10, 540, 70, 20),
                    (150, 310, 790, 20),
                    (435, 168, 610, 20),
                    (572, 453, 510, 20),
                    (10, 568, 460, 20),
                    (247, 115, 113, 20),
                    (570, 263, 185, 20),
                    (132, 454, 50, 20),
                    (390, 145, 35, 70),
                ],
                hazards_fire=[(758, 792, 81, 2), (686, 622, 82, 3)],
                hazards_water=[(518, 792, 84, 2), (686, 622, 82, 3)],
                hazards_neutral=[(510, 783, 109, 3), (742, 783, 106, 4)],
                fire_gems=[(290, 50), (200, 360), (1020, 650), (545, 731)],
                water_gems=[(60, 130), (700, 390), (550, 556), (775, 731)],
                fire_goal_x=910,
                water_goal_x=995,
            )
        return LevelSpec(
            width=1103,
            height=817,
            spawn_fire=(530, 780),
            spawn_water=(480, 780),
            door_fire=(365, 138, 77, 83),
            door_water=(40, 138, 74, 85),
            platforms=[
                (0, 790, 1103, 10),
                (55, 650, 490, 25),
                (590, 710, 40, 20),
                (880, 170, 170, 20),
                (0, 227, 450, 20),
                (702, 540, 400, 20),
                (15, 455, 70, 20),
                (770, 284, 330, 20),
                (583, 115, 240, 20),
                (563, 368, 150, 20),
                (132, 509, 550, 23),
                (190, 400, 100, 20),
                (455, 205, 115, 20),
                (850, 380, 300, 40),
            ],
            hazards_fire=[(0, 760, 450, 57), (590, 760, 513, 57)],
            hazards_water=[(0, 760, 450, 57), (590, 760, 513, 57)],
            hazards_neutral=[(130, 560, 170, 20)],
            fire_gems=[(135, 150), (285, 330), (95, 560), (350, 720), (650, 50), (910, 220)],
            water_gems=[(300, 150), (145, 330), (80, 726), (650, 641), (910, 100), (865, 460)],
            fire_goal_x=365,
            water_goal_x=40,
        )

    def _apply_action(self, agent: AgentState, action: int) -> float:
        if action == self.ACTION_LEFT:
            agent.x -= self.step_size
        elif action == self.ACTION_RIGHT:
            agent.x += self.step_size
        elif action == self.ACTION_JUMP and agent.on_ground:
            agent.vy = self.jump_velocity
            agent.on_ground = False

        agent.x = float(np.clip(agent.x, 0, self.level_spec.width - self.fire_size[0]))

        if not agent.on_ground:
            agent.vy = max(agent.vy - self.gravity, -self.max_fall_speed)
            agent.y -= agent.vy

        agent.on_ground = False
        self._resolve_platforms(agent)
        self._resolve_bounds(agent)
        return 0.0

    def _resolve_platforms(self, agent: AgentState):
        rect = self._rect(agent.x, agent.y, *self.fire_size)
        for px, py, pw, ph in self.level_spec.platforms:
            plat = self._rect(px, py, pw, ph)
            if not rect.colliderect(plat):
                continue
            prev_bottom = rect.bottom - (agent.vy if agent.vy > 0 else 0)
            prev_top = rect.top - (agent.vy if agent.vy < 0 else 0)
            if prev_bottom <= plat.top and rect.bottom >= plat.top:
                agent.y = plat.top - self.fire_size[1]
                agent.vy = 0.0
                agent.on_ground = True
                rect = self._rect(agent.x, agent.y, *self.fire_size)
            elif prev_top >= plat.bottom and rect.top <= plat.bottom:
                agent.y = plat.bottom + 1
                agent.vy = 0.0
                rect = self._rect(agent.x, agent.y, *self.fire_size)

    def _resolve_bounds(self, agent: AgentState):
        if agent.y >= self.level_spec.height - self.fire_size[1]:
            agent.y = self.level_spec.height - self.fire_size[1]
            agent.vy = 0.0
            agent.on_ground = True
        if agent.y < 0:
            agent.y = 0.0
            agent.vy = 0.0

    def _collect_gems(self):
        reward_fire = 0.0
        reward_water = 0.0
        fire_rect = self._rect(self.fire.x, self.fire.y, *self.fire_size)
        water_rect = self._rect(self.water.x, self.water.y, *self.water_size)
        gem_w, gem_h = 45, 36

        next_fire = []
        for gx, gy in self.fire_gems:
            if fire_rect.colliderect(self._rect(gx, gy, gem_w, gem_h)):
                reward_fire += self.gem_reward
            else:
                next_fire.append((gx, gy))
        self.fire_gems = next_fire

        next_water = []
        for gx, gy in self.water_gems:
            if water_rect.colliderect(self._rect(gx, gy, gem_w, gem_h)):
                reward_water += self.gem_reward
            else:
                next_water.append((gx, gy))
        self.water_gems = next_water
        return reward_fire, reward_water

    def _is_dead(self, agent: AgentState, role: str) -> bool:
        rect = self._rect(agent.x, agent.y, *self.fire_size)
        hazards = self.level_spec.hazards_fire if role == "fireboy" else self.level_spec.hazards_water
        for hx, hy, hw, hh in hazards + self.level_spec.hazards_neutral:
            if rect.colliderect(self._rect(hx, hy, hw, hh)):
                return True
        return False

    def _touch_goal(self, agent: AgentState, goal_rect: Tuple[float, float, float, float]) -> bool:
        return self._rect(agent.x, agent.y, *self.fire_size).colliderect(self._rect(*goal_rect))

    def _progress(self, goal_x: float, x: float) -> float:
        return max(0.0, (goal_x - x) / float(self.level_spec.width))

    def _team_distance_delta(self, fire_prev_x: float, water_prev_x: float) -> float:
        before = abs(self.level_spec.fire_goal_x - fire_prev_x) + abs(self.level_spec.water_goal_x - water_prev_x)
        after = abs(self.level_spec.fire_goal_x - self.fire.x) + abs(self.level_spec.water_goal_x - self.water.x)
        return (before - after) / float(self.level_spec.width)

    def _nearest_gem(self, x: float, y: float, gems: List[Tuple[float, float]]):
        if not gems:
            return 0.0, 0.0, 0.0
        best = min(gems, key=lambda g: abs(g[0] - x) + abs(g[1] - y))
        dist = abs(best[0] - x) + abs(best[1] - y)
        return best[0], best[1], float(dist)

    def _get_obs(self):
        return {
            "fireboy": self._build_obs(self.fire, self.level_spec.fire_goal_x, self.fire_gems),
            "watergirl": self._build_obs(self.water, self.level_spec.water_goal_x, self.water_gems),
        }

    def _build_obs(self, agent: AgentState, goal_x: float, gems: List[Tuple[float, float]]):
        gem_x, gem_y, gem_dist = self._nearest_gem(agent.x, agent.y, gems)
        obs = np.array(
            [
                agent.x / self.level_spec.width,
                agent.y / self.level_spec.height,
                agent.vx / 10.0,
                agent.vy / 10.0,
                1.0 if agent.on_ground else 0.0,
                goal_x / self.level_spec.width,
                (goal_x - agent.x) / self.level_spec.width,
                gem_x / self.level_spec.width,
                gem_y / self.level_spec.height,
                gem_dist / max(self.level_spec.width, self.level_spec.height),
                len(gems) / 10.0,
                self.steps / max(1, self.max_steps),
                1.0 if self.fire_open else 0.0,
                1.0 if self.water_open else 0.0,
            ],
            dtype=np.float32,
        )
        return obs

    def _empty_rewards(self):
        return {"fireboy": 0.0, "watergirl": 0.0}

    def _rect(self, x, y, w, h):
        return _Rect(x, y, w, h)


@dataclass
class _Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.height

    def colliderect(self, other: "_Rect") -> bool:
        return not (
            self.right <= other.left
            or self.left >= other.right
            or self.bottom <= other.top
            or self.top >= other.bottom
        )
