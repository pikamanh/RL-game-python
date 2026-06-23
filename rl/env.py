from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import gymnasium as gym
import numpy as np
import pygame
from gymnasium import spaces

try:
    from .geometry import LETHAL_HAZARDS, PLAYER_HAZARD_INSETS, make_hazard_rects
except ImportError:
    from geometry import LETHAL_HAZARDS, PLAYER_HAZARD_INSETS, make_hazard_rects

try:
    from ray.rllib.env.multi_agent_env import MultiAgentEnv
except Exception:  # pragma: no cover - lets the env run without Ray installed.
    MultiAgentEnv = object


FIREBOY = "fireboy"
WATERGIRL = "watergirl"
AGENTS = (FIREBOY, WATERGIRL)

ACTION_NOOP = 0
ACTION_LEFT = 1
ACTION_RIGHT = 2
ACTION_JUMP = 3
ACTION_LEFT_JUMP = 4
ACTION_RIGHT_JUMP = 5


@dataclass(frozen=True)
class Hazard:
    rect: pygame.Rect
    kind: str


@dataclass(frozen=True)
class Checkpoint:
    name: str
    rect: pygame.Rect
    reward: float = 5.0


@dataclass
class PlayerState:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    door_opened: bool = False


class FireWaterEnv(MultiAgentEnv):
    """Small multi-agent RL environment based on the Pygame game geometry.

    This intentionally separates game logic from the original keyboard-driven
    Pygame loop so RL training can run headless and fast.
    """

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 60}

    def __init__(self, config: dict[str, Any] | None = None):
        config = config or {}
        self.level = int(config.get("level", 1))
        self.max_steps = int(config.get("max_steps", 3000))
        self.render_mode = config.get("render_mode")
        self.step_size = float(config.get("step_size", 5.0))
        self.gravity = float(config.get("gravity", 0.55))
        self.jump_velocity = float(config.get("jump_velocity", 8.0))
        self.auto_reset_on_done = bool(config.get("auto_reset_on_done", False))

        self.width, self.height = (1103, 817) if self.level == 2 else (1100, 817)
        self.player_w = 35
        self.player_h = 50
        self.action_space = spaces.Discrete(6)
        self.observation_space = spaces.Box(-1.0, 1.0, shape=(36,), dtype=np.float32)
        self.action_spaces = {agent: self.action_space for agent in AGENTS}
        self.observation_spaces = {agent: self.observation_space for agent in AGENTS}
        self._agent_ids = set(AGENTS)

        self.screen: pygame.Surface | None = None
        self.clock: pygame.time.Clock | None = None
        self.steps = 0
        self.last_fire_dist = 0.0
        self.last_water_dist = 0.0
        self._fire_door_rewarded = False
        self._water_door_rewarded = False
        self.fire = PlayerState(0, 0)
        self.water = PlayerState(0, 0)
        self.red_gems: set[tuple[int, int]] = set()
        self.blue_gems: set[tuple[int, int]] = set()
        self.arm_opened = False
        self.arm_was_pressed = False
        self.button_opened = False
        self.box: pygame.Rect | None = None
        self._fire_idle_steps = 0
        self._water_idle_steps = 0
        self._fire_checkpoints: set[str] = set()
        self._water_checkpoints: set[str] = set()
        self._team_checkpoints: set[str] = set()
        self._fire_checkpoint_zones: list[Checkpoint] = []
        self._water_checkpoint_zones: list[Checkpoint] = []
        self._episode_red_gems_collected = 0
        self._episode_blue_gems_collected = 0
        self._max_fire_x = 0.0
        self._max_water_x = 0.0
        self._last_team_checkpoint_count = 0
        self._steps_since_team_checkpoint = 0
        self._water_fire_edge_steps = 0
        self.last_episode_metrics: dict[str, float] = {}
        self._load_level()

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super_reset = getattr(super(), "reset", None)
        if callable(super_reset):
            try:
                super_reset(seed=seed)
            except TypeError:
                pass

        self.steps = 0
        self.arm_opened = False
        self.arm_was_pressed = False
        self.button_opened = False
        self._fire_idle_steps = 0
        self._water_idle_steps = 0
        self._fire_checkpoints = set()
        self._water_checkpoints = set()
        self._team_checkpoints = set()
        self._episode_red_gems_collected = 0
        self._episode_blue_gems_collected = 0
        self.last_episode_metrics = {}
        self._load_level()
        self._max_fire_x = self.fire.x
        self._max_water_x = self.water.x
        self._last_team_checkpoint_count = 0
        self._steps_since_team_checkpoint = 0
        self._water_fire_edge_steps = 0
        self.last_fire_dist = self._distance_to_rect(self.fire, self.fire_door)
        self.last_water_dist = self._distance_to_rect(self.water, self.water_door)
        self._fire_door_rewarded = False
        self._water_door_rewarded = False
        obs = self._obs_all()
        infos = {agent: {} for agent in AGENTS}
        return obs, infos

    def step(self, action_dict: dict[str, int]):
        self.steps += 1
        old_fire_dist = self.last_fire_dist
        old_water_dist = self.last_water_dist
        old_red_count = len(self.red_gems)
        old_blue_count = len(self.blue_gems)
        prev_fire_x = self.fire.x
        prev_water_x = self.water.x
        old_max_water_x = self._max_water_x
        old_team_min_x = min(prev_fire_x, prev_water_x)

        self._apply_player_action(self.fire, int(action_dict.get(FIREBOY, ACTION_NOOP)))
        self._apply_player_action(self.water, int(action_dict.get(WATERGIRL, ACTION_NOOP)))
        self._update_box()
        self._update_mechanisms()
        self._collect_gems()
        self._episode_red_gems_collected += old_red_count - len(self.red_gems)
        self._episode_blue_gems_collected += old_blue_count - len(self.blue_gems)
        self._update_doors()
        self._max_fire_x = max(self._max_fire_x, self.fire.x)
        self._max_water_x = max(self._max_water_x, self.water.x)

        # Per-agent idle tracking (x-axis only; jumping in place is caught here)
        if abs(self.fire.x - prev_fire_x) < 5.0:
            self._fire_idle_steps += 1
        else:
            self._fire_idle_steps = 0
        if abs(self.water.x - prev_water_x) < 5.0:
            self._water_idle_steps += 1
        else:
            self._water_idle_steps = 0
        if 500.0 <= self.water.x <= 535.0 and "cleared_fire_pool" not in self._water_checkpoints:
            self._water_fire_edge_steps += 1
        else:
            self._water_fire_edge_steps = 0
        _IDLE_THRESHOLD = 30
        fire_idle_pen = 0.05 if self._fire_idle_steps > _IDLE_THRESHOLD else 0.0
        water_idle_pen = 0.05 if self._water_idle_steps > _IDLE_THRESHOLD else 0.0

        fire_checkpoint = 0.0
        water_checkpoint = 0.0
        team_checkpoint = 0.0

        death = self._death()
        fire_died = self._death_agent(self.fire, LETHAL_HAZARDS[FIREBOY]) if death else False
        water_died = self._death_agent(self.water, LETHAL_HAZARDS[WATERGIRL]) if death else False
        win = self.fire.door_opened and self.water.door_opened
        truncated = self.steps >= self.max_steps

        if not death:
            old_fire_checkpoints = len(self._fire_checkpoints)
            old_water_checkpoints = len(self._water_checkpoints)
            fire_checkpoint = self._checkpoint_bonus(self.fire, self._fire_checkpoint_zones, self._fire_checkpoints)
            water_checkpoint = self._checkpoint_bonus(self.water, self._water_checkpoint_zones, self._water_checkpoints)
            fire_checkpoint_count = len(self._fire_checkpoints) - old_fire_checkpoints
            water_checkpoint_count = len(self._water_checkpoints) - old_water_checkpoints
            team_checkpoint = self._team_checkpoint_bonus()
            if len(self._team_checkpoints) > self._last_team_checkpoint_count:
                self._last_team_checkpoint_count = len(self._team_checkpoints)
                self._steps_since_team_checkpoint = 0
            else:
                self._steps_since_team_checkpoint += 1
        else:
            fire_checkpoint_count = 0
            water_checkpoint_count = 0

        new_fire_dist = self._distance_to_rect(self.fire, self.fire_door)
        new_water_dist = self._distance_to_rect(self.water, self.water_door)
        self.last_fire_dist = new_fire_dist
        self.last_water_dist = new_water_dist

        # Individual progress rewards — each agent rewarded for own door
        fire_progress = (old_fire_dist - new_fire_dist) * 0.05
        water_progress = (old_water_dist - new_water_dist) * 0.05
        water_x_delta = max(0.0, self._max_water_x - old_max_water_x)
        water_forward_progress = min(0.08, water_x_delta * 0.015)
        if 500.0 <= self.water.x <= 700.0:
            water_forward_progress += min(0.12, water_x_delta * 0.025)
        team_min_progress = min(0.06, max(0.0, min(self.fire.x, self.water.x) - old_team_min_x) * 0.01)

        # Gem collection rewards
        fire_gem_bonus = (old_red_count - len(self.red_gems)) * 5.0
        water_gem_bonus = (old_blue_count - len(self.blue_gems)) * 5.0

        # One-time door-reached bonus
        fire_door_bonus = 0.0
        if self.fire.door_opened and not self._fire_door_rewarded:
            fire_door_bonus = 20.0
            self._fire_door_rewarded = True
        water_door_bonus = 0.0
        if self.water.door_opened and not self._water_door_rewarded:
            water_door_bonus = 20.0
            self._water_door_rewarded = True

        shared_step = -0.01
        if self._both_idle(action_dict):
            shared_step -= 0.04
        if self.arm_opened:
            shared_step += 0.005
        if self.button_opened:
            shared_step += 0.005
        team_gap = max(0.0, abs(self.fire.x - self.water.x) - 180.0)
        team_gap_pen = min(0.025, team_gap / 9000.0)
        fire_abandon_pen = 0.0
        if self.fire.x > 600.0 and self.water.x < 520.0:
            fire_abandon_pen = min(0.04, (self.fire.x - self.water.x - 80.0) / 8000.0)
        stage_stall_pen = 0.0
        if len(self._team_checkpoints) < 4 and self._steps_since_team_checkpoint > 1000:
            stage_stall_pen = min(0.015, (self._steps_since_team_checkpoint - 1000) / 30000.0)
        water_fire_edge_pen = 0.0
        if self._water_fire_edge_steps > 45:
            water_fire_edge_pen = min(0.06, (self._water_fire_edge_steps - 45) / 1200.0)

        fire_reward = (shared_step + fire_progress + team_min_progress + fire_gem_bonus + fire_door_bonus
                       + fire_checkpoint + team_checkpoint - fire_idle_pen - team_gap_pen
                       - fire_abandon_pen - stage_stall_pen)
        water_reward = (shared_step + water_progress + water_forward_progress + team_min_progress
                        + water_gem_bonus + water_door_bonus
                        + water_checkpoint + team_checkpoint - water_idle_pen - team_gap_pen
                        - water_fire_edge_pen - stage_stall_pen)

        if death:
            fire_reward -= 100.0 if fire_died else 20.0
            water_reward -= 115.0 if water_died else 20.0
            if water_died and len(self._team_checkpoints) >= 2:
                water_reward -= 15.0
        if win:
            fire_reward += 100.0
            water_reward += 100.0
        if truncated:
            fire_reward -= 50.0
            water_reward -= 50.0

        if death or win or truncated:
            self.last_episode_metrics = {
                "win_rate": float(win),
                "death_rate": float(death),
                "fire_died_rate": float(fire_died),
                "water_died_rate": float(water_died),
                "truncated_rate": float(truncated and not death and not win),
                "gem_count": float(self._episode_red_gems_collected + self._episode_blue_gems_collected),
                "checkpoint_count": float(len(self._fire_checkpoints) + len(self._water_checkpoints)),
                "fire_checkpoint_count": float(len(self._fire_checkpoints)),
                "water_checkpoint_count": float(len(self._water_checkpoints)),
                "team_checkpoint_count": float(len(self._team_checkpoints)),
                "team_gap": float(abs(self.fire.x - self.water.x)),
                "max_fire_x": float(self._max_fire_x),
                "max_water_x": float(self._max_water_x),
                "water_cleared_fire_pool_rate": float("cleared_fire_pool" in self._water_checkpoints),
                "water_fire_edge_steps": float(self._water_fire_edge_steps),
                "steps_since_team_checkpoint": float(self._steps_since_team_checkpoint),
                "stage_stall_penalty": float(stage_stall_pen),
                "water_fire_edge_penalty": float(water_fire_edge_pen),
                "fire_final_x": float(self.fire.x),
                "fire_final_y": float(self.fire.y),
                "water_final_x": float(self.water.x),
                "water_final_y": float(self.water.y),
            }

        obs = self._obs_all()
        rewards = {FIREBOY: float(fire_reward), WATERGIRL: float(water_reward)}
        terminateds = {agent: bool(death or win) for agent in AGENTS}
        truncateds = {agent: bool(truncated) for agent in AGENTS}
        terminateds["__all__"] = bool(death or win)
        truncateds["__all__"] = bool(truncated)
        infos = {
            agent: {
                "death": death,
                "fire_died": fire_died,
                "water_died": water_died,
                "win": win,
                "steps": self.steps,
                "fire_final_pos": (self.fire.x, self.fire.y),
                "water_final_pos": (self.water.x, self.water.y),
                "gem_count": self._episode_red_gems_collected + self._episode_blue_gems_collected,
                "checkpoint_count": len(self._fire_checkpoints) + len(self._water_checkpoints),
                "fire_checkpoint_count": len(self._fire_checkpoints),
                "water_checkpoint_count": len(self._water_checkpoints),
                "team_checkpoint_count": len(self._team_checkpoints),
                "team_gap": abs(self.fire.x - self.water.x),
                "max_fire_x": self._max_fire_x,
                "max_water_x": self._max_water_x,
                "water_cleared_fire_pool": "cleared_fire_pool" in self._water_checkpoints,
                "water_fire_edge_steps": self._water_fire_edge_steps,
                "steps_since_team_checkpoint": self._steps_since_team_checkpoint,
                "stage_stall_penalty": stage_stall_pen,
                "water_fire_edge_penalty": water_fire_edge_pen,
                "step_checkpoint_count": fire_checkpoint_count if agent == FIREBOY else water_checkpoint_count,
            }
            for agent in AGENTS
        }

        if self.auto_reset_on_done and (death or win or truncated):
            reset_obs, reset_infos = self.reset()
            obs = reset_obs
            for agent in AGENTS:
                infos[agent].update(reset_infos[agent])
                infos[agent]["auto_reset"] = True

        return obs, rewards, terminateds, truncateds, infos

    def render(self):
        if self.screen is None:
            pygame.init()
            self.screen = pygame.display.set_mode((self.width, self.height))
            pygame.display.set_caption(f"RL Fireboy and Watergirl - Level {self.level}")
            self.clock = pygame.time.Clock()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                self.screen = None
                return None

        self.screen.fill((22, 24, 28))
        for platform in self.platforms:
            pygame.draw.rect(self.screen, (122, 84, 48), platform)
        for hazard in self.hazards:
            color = {"fire": (220, 70, 30), "water": (35, 110, 220), "poison": (50, 180, 70)}[hazard.kind]
            pygame.draw.rect(self.screen, color, hazard.rect)
        for gem in self.red_gems:
            pygame.draw.circle(self.screen, (230, 60, 60), gem, 8)
        for gem in self.blue_gems:
            pygame.draw.circle(self.screen, (70, 145, 240), gem, 8)
        pygame.draw.rect(self.screen, (255, 130, 50), self.fire_door)
        pygame.draw.rect(self.screen, (65, 170, 255), self.water_door)
        if self.box is not None:
            pygame.draw.rect(self.screen, (180, 135, 80), self.box)
        pygame.draw.rect(self.screen, (245, 95, 55), self._rect(self.fire))
        pygame.draw.rect(self.screen, (70, 170, 245), self._rect(self.water))
        pygame.draw.rect(self.screen, (255, 255, 255), self._hazard_rect(FIREBOY, self.fire), 1)
        pygame.draw.rect(self.screen, (255, 255, 255), self._hazard_rect(WATERGIRL, self.water), 1)
        pygame.display.flip()
        if self.clock is not None:
            self.clock.tick(self.metadata["render_fps"])
        return None

    def close(self):
        if self.screen is not None:
            pygame.quit()
            self.screen = None

    def _load_level(self):
        if self.level == 2:
            self.fire = PlayerState(530, 740)
            self.water = PlayerState(480, 740)
            self.platforms = [
                pygame.Rect(0, 790, 1103, 10), pygame.Rect(55, 650, 490, 25),
                pygame.Rect(590, 710, 40, 20), pygame.Rect(880, 170, 170, 20),
                pygame.Rect(0, 227, 450, 20), pygame.Rect(702, 540, 400, 20),
                pygame.Rect(15, 455, 70, 20), pygame.Rect(770, 284, 330, 20),
                pygame.Rect(583, 115, 240, 20), pygame.Rect(563, 368, 150, 20),
                pygame.Rect(132, 509, 550, 23), pygame.Rect(190, 400, 100, 20),
                pygame.Rect(455, 205, 115, 20), pygame.Rect(850, 380, 300, 40),
            ]
            self.fire_door = pygame.Rect(365, 138, 45, 70)
            self.water_door = pygame.Rect(40, 138, 45, 70)
            self.hazards = []
            self.red_gems = {(135, 150), (285, 330), (95, 560), (350, 720), (650, 50), (910, 220)}
            self.blue_gems = {(300, 150), (145, 330), (80, 726), (650, 641), (910, 100), (865, 460)}
            self.box = pygame.Rect(828, 235, 35, 35)
            self.button_rect = pygame.Rect(930, 520, 55, 20)
            self._fire_checkpoint_zones = []
            self._water_checkpoint_zones = []
        else:
            self.fire = PlayerState(60, 742)
            self.water = PlayerState(60, 572)
            self.platforms = [
                pygame.Rect(0, 792, 1100, 10), pygame.Rect(10, 680, 270, 20),
                pygame.Rect(190, 424, 365, 20), pygame.Rect(1020, 710, 50, 20),
                pygame.Rect(10, 200, 140, 140), pygame.Rect(505, 623, 425, 20),
                pygame.Rect(10, 540, 70, 20), pygame.Rect(150, 310, 790, 20),
                pygame.Rect(435, 168, 610, 20), pygame.Rect(572, 453, 510, 20),
                pygame.Rect(10, 568, 460, 20), pygame.Rect(247, 115, 113, 20),
                pygame.Rect(570, 263, 185, 20), pygame.Rect(132, 454, 50, 20),
                pygame.Rect(390, 145, 35, 70),
            ]
            self.fire_door = pygame.Rect(910, 85, 45, 70)
            self.water_door = pygame.Rect(995, 85, 45, 70)
            self.hazards = [Hazard(rect, kind) for kind, rect in make_hazard_rects(self.level)]
            self.red_gems = {(290, 50), (200, 360), (1020, 650), (545, 731)}
            self.blue_gems = {(60, 130), (700, 390), (550, 556), (775, 731)}
            self.box = None
            self.button_rect = pygame.Rect(300, 406, 55, 20)
            self._fire_checkpoint_zones = [
                Checkpoint("early_lower", pygame.Rect(220, 650, 180, 150), 1.0),
                Checkpoint("before_first_pool", pygame.Rect(410, 700, 110, 100), 1.5),
                Checkpoint("approach_fire_pool", pygame.Rect(525, 680, 100, 130), 3.0),
                Checkpoint("fire_pool_edge", pygame.Rect(500, 680, 55, 130), 1.0),
                Checkpoint("cleared_fire_pool", pygame.Rect(635, 680, 70, 130), 2.0),
                Checkpoint("after_fire_pool", pygame.Rect(645, 680, 150, 130), 5.0),
                Checkpoint("safe_after_fire_pool", pygame.Rect(660, 680, 90, 130), 2.0),
                Checkpoint("lower_right", pygame.Rect(860, 680, 180, 120), 4.0),
                Checkpoint("middle_platform", pygame.Rect(500, 560, 450, 90), 5.0),
                Checkpoint("upper_middle", pygame.Rect(560, 400, 540, 100), 5.0),
                Checkpoint("top_route", pygame.Rect(430, 120, 650, 100), 6.0),
            ]
            self._water_checkpoint_zones = [
                Checkpoint("early_lower", pygame.Rect(200, 620, 220, 180), 4.0),
                Checkpoint("before_first_pool", pygame.Rect(410, 680, 105, 120), 5.0),
                Checkpoint("fire_pool_edge", pygame.Rect(485, 660, 70, 140), 3.0),
                Checkpoint("approach_fire_pool", pygame.Rect(525, 660, 100, 140), 7.0),
                Checkpoint("cleared_fire_pool", pygame.Rect(635, 660, 90, 140), 40.0),
                Checkpoint("after_fire_pool", pygame.Rect(645, 660, 165, 140), 10.0),
                Checkpoint("safe_after_fire_pool", pygame.Rect(700, 660, 170, 140), 15.0),
                Checkpoint("lower_right", pygame.Rect(860, 680, 180, 120), 5.0),
                Checkpoint("middle_platform", pygame.Rect(500, 560, 450, 90), 5.0),
                Checkpoint("upper_middle", pygame.Rect(560, 400, 540, 100), 5.0),
                Checkpoint("top_route", pygame.Rect(430, 120, 650, 100), 6.0),
            ]

    def _apply_player_action(self, player: PlayerState, action: int):
        player.vx = 0.0
        if action in (ACTION_LEFT, ACTION_LEFT_JUMP):
            player.vx = -self.step_size
        elif action in (ACTION_RIGHT, ACTION_RIGHT_JUMP):
            player.vx = self.step_size
        if action in (ACTION_JUMP, ACTION_LEFT_JUMP, ACTION_RIGHT_JUMP) and player.on_ground:
            player.vy = -self.jump_velocity
            player.on_ground = False

        player.x = float(np.clip(player.x + player.vx, 0, self.width - self.player_w))
        player.vy += self.gravity
        player.y += player.vy
        self._resolve_platforms(player)

    def _resolve_platforms(self, player: PlayerState):
        player.on_ground = False
        rect = self._rect(player)
        for platform in self.platforms:
            if (
                rect.colliderect(platform)
                and player.vy >= 0
                and (rect.bottom - player.vy <= platform.top + 4 or rect.top < platform.top)
            ):
                player.y = platform.top - self.player_h
                player.vy = 0.0
                player.on_ground = True
                rect = self._rect(player)
        if player.y > self.height:
            player.y = self.height - self.player_h
            player.vy = 0.0

    def _update_box(self):
        if self.box is None:
            return
        box_on_platform = any(self.box.colliderect(platform) for platform in self.platforms)
        if not box_on_platform:
            self.box.y += 3
        for player, action_sign in ((self.fire, np.sign(self.fire.vx)), (self.water, np.sign(self.water.vx))):
            if self._rect(player).colliderect(self.box) and action_sign:
                self.box.x += int(action_sign * 8)
        self.box.x = int(np.clip(self.box.x, 0, self.width - self.box.width))

    def _update_mechanisms(self):
        fire_rect = self._rect(self.fire)
        water_rect = self._rect(self.water)
        if self.level == 1:
            arm_rect = pygame.Rect(270, 520, 55, 60)
            arm_pressed = fire_rect.colliderect(arm_rect) or water_rect.colliderect(arm_rect)
            if arm_pressed and not self.arm_was_pressed:
                self.arm_opened = not self.arm_opened
            self.arm_was_pressed = arm_pressed
            self.button_opened = fire_rect.colliderect(self.button_rect) or water_rect.colliderect(self.button_rect)
        else:
            box_pressed = self.box is not None and self.box.colliderect(self.button_rect)
            self.button_opened = fire_rect.colliderect(self.button_rect) or water_rect.colliderect(self.button_rect) or box_pressed

    def _collect_gems(self):
        fire_rect = self._rect(self.fire)
        water_rect = self._rect(self.water)
        self.red_gems = {gem for gem in self.red_gems if not fire_rect.collidepoint(gem)}
        self.blue_gems = {gem for gem in self.blue_gems if not water_rect.collidepoint(gem)}

    def _update_doors(self):
        self.fire.door_opened = self.fire.door_opened or self._rect(self.fire).colliderect(self.fire_door)
        self.water.door_opened = self.water.door_opened or self._rect(self.water).colliderect(self.water_door)

    def _death(self) -> bool:
        fire_rect = self._hazard_rect(FIREBOY, self.fire)
        water_rect = self._hazard_rect(WATERGIRL, self.water)
        for hazard in self.hazards:
            if hazard.kind in LETHAL_HAZARDS[FIREBOY] and fire_rect.colliderect(hazard.rect):
                return True
            if hazard.kind in LETHAL_HAZARDS[WATERGIRL] and water_rect.colliderect(hazard.rect):
                return True
        return False

    def _death_agent(self, player: PlayerState, lethal_kinds: set[str]) -> bool:
        agent = FIREBOY if player is self.fire else WATERGIRL
        rect = self._hazard_rect(agent, player)
        return any(hazard.kind in lethal_kinds and rect.colliderect(hazard.rect) for hazard in self.hazards)

    def _hazard_proximity_penalty(self, player: PlayerState, lethal_kinds: set[str]) -> float:
        agent = FIREBOY if player is self.fire else WATERGIRL
        rect = self._hazard_rect(agent, player)
        penalty = 0.0
        for hazard in self.hazards:
            if hazard.kind in lethal_kinds:
                dist = math.hypot(rect.centerx - hazard.rect.centerx, rect.centery - hazard.rect.centery)
                if dist < 200:
                    penalty += (1.0 - dist / 200.0) * 0.1
        return penalty

    def _both_idle(self, action_dict: dict[str, int]) -> bool:
        return int(action_dict.get(FIREBOY, ACTION_NOOP)) == ACTION_NOOP and int(action_dict.get(WATERGIRL, ACTION_NOOP)) == ACTION_NOOP

    def _team_distance(self) -> float:
        return self._distance_to_rect(self.fire, self.fire_door) + self._distance_to_rect(self.water, self.water_door)

    def _checkpoint_bonus(self, player: PlayerState, checkpoints: list[Checkpoint], reached: set[str]) -> float:
        rect = self._rect(player)
        bonus = 0.0
        for checkpoint in checkpoints:
            if checkpoint.name not in reached and rect.colliderect(checkpoint.rect):
                reached.add(checkpoint.name)
                bonus += checkpoint.reward
        return bonus

    def _team_checkpoint_bonus(self) -> float:
        bonus = 0.0
        common_checkpoints = self._fire_checkpoints & self._water_checkpoints
        for checkpoint_name in common_checkpoints:
            if checkpoint_name not in self._team_checkpoints:
                self._team_checkpoints.add(checkpoint_name)
                if checkpoint_name == "cleared_fire_pool":
                    bonus += 18.0
                elif checkpoint_name == "safe_after_fire_pool":
                    bonus += 10.0
                elif checkpoint_name == "fire_pool_edge":
                    bonus += 2.0
                elif checkpoint_name == "after_fire_pool":
                    bonus += 8.0
                elif checkpoint_name == "approach_fire_pool":
                    bonus += 6.0
                else:
                    bonus += 4.0
        return bonus

    def _distance_to_rect(self, player: PlayerState, target: pygame.Rect) -> float:
        return math.hypot(player.x - target.centerx, player.y - target.centery) / max(self.width, self.height)

    def _obs_all(self) -> dict[str, np.ndarray]:
        return {
            FIREBOY: self._obs(FIREBOY),
            WATERGIRL: self._obs(WATERGIRL),
        }

    def _obs(self, agent: str) -> np.ndarray:
        own = self.fire if agent == FIREBOY else self.water
        other = self.water if agent == FIREBOY else self.fire
        own_door = self.fire_door if agent == FIREBOY else self.water_door
        other_door = self.water_door if agent == FIREBOY else self.fire_door
        lethal_for_own = LETHAL_HAZARDS[agent]
        nearest_hazard = self._nearest_hazard(own, lethal_for_own)
        box = self.box or pygame.Rect(0, 0, 0, 0)
        red_total = 6 if self.level == 2 else 4
        blue_total = 6 if self.level == 2 else 4
        values = [
            own.x / self.width, own.y / self.height, self._unit_velocity_x(own.vx), self._unit_velocity_y(own.vy),
            float(own.on_ground), float(own.door_opened),
            other.x / self.width, other.y / self.height, self._unit_velocity_x(other.vx), self._unit_velocity_y(other.vy),
            float(other.on_ground), float(other.door_opened),
            own_door.centerx / self.width, own_door.centery / self.height,
            other_door.centerx / self.width, other_door.centery / self.height,
            nearest_hazard[0] / self.width, nearest_hazard[1] / self.height,
            len(self.red_gems) / red_total, len(self.blue_gems) / blue_total,
            float(self.arm_opened), float(self.button_opened),
            box.x / self.width, box.y / self.height, box.width / 100.0, box.height / 100.0,
            self.steps / self.max_steps,
            min(self._team_distance() / 2.0, 1.0),
            float(agent == FIREBOY), float(agent == WATERGIRL),
            self.button_rect.centerx / self.width, self.button_rect.centery / self.height,
            float(self.level == 1), float(self.level == 2),
            len(self.platforms) / 20.0, len(self.hazards) / 5.0,
        ]
        return np.asarray(values, dtype=np.float32) * 2.0 - 1.0

    def _unit_velocity_x(self, velocity: float) -> float:
        return float(np.clip((velocity / self.step_size + 1.0) / 2.0, 0.0, 1.0))

    def _unit_velocity_y(self, velocity: float) -> float:
        return float(np.clip((velocity / 15.0 + 1.0) / 2.0, 0.0, 1.0))

    def _nearest_hazard(self, player: PlayerState, lethal_kinds: set[str] | None = None) -> tuple[float, float]:
        hazards = [h for h in self.hazards if lethal_kinds is None or h.kind in lethal_kinds]
        if not hazards:
            return 0.0, 0.0
        rect = self._rect(player)
        hazard = min(hazards, key=lambda item: math.hypot(rect.centerx - item.rect.centerx, rect.centery - item.rect.centery))
        return float(hazard.rect.centerx), float(hazard.rect.centery)

    def _rect(self, player: PlayerState) -> pygame.Rect:
        return pygame.Rect(int(player.x), int(player.y), self.player_w, self.player_h)

    def _hazard_rect(self, agent: str, player: PlayerState) -> pygame.Rect:
        left, top, right, bottom = PLAYER_HAZARD_INSETS[agent]
        return pygame.Rect(
            int(player.x) + left,
            int(player.y) + top,
            max(1, self.player_w - left - right),
            max(1, self.player_h - top - bottom),
        )
