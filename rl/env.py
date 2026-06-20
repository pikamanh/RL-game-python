from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import gymnasium as gym
import numpy as np
import pygame
from gymnasium import spaces

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
        self.last_team_distance = 0.0
        self.fire = PlayerState(0, 0)
        self.water = PlayerState(0, 0)
        self.red_gems: set[tuple[int, int]] = set()
        self.blue_gems: set[tuple[int, int]] = set()
        self.arm_opened = False
        self.button_opened = False
        self.box: pygame.Rect | None = None
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
        self.button_opened = False
        self._load_level()
        self.last_team_distance = self._team_distance()
        obs = self._obs_all()
        infos = {agent: {} for agent in AGENTS}
        return obs, infos

    def step(self, action_dict: dict[str, int]):
        self.steps += 1
        old_distance = self.last_team_distance

        self._apply_player_action(self.fire, int(action_dict.get(FIREBOY, ACTION_NOOP)))
        self._apply_player_action(self.water, int(action_dict.get(WATERGIRL, ACTION_NOOP)))
        self._update_box()
        self._update_mechanisms()
        self._collect_gems()
        self._update_doors()

        death = self._death()
        win = self.fire.door_opened and self.water.door_opened
        truncated = self.steps >= self.max_steps

        new_distance = self._team_distance()
        progress_reward = (old_distance - new_distance) * 0.02
        self.last_team_distance = new_distance

        reward = -0.01 + progress_reward
        if self._both_idle(action_dict):
            reward -= 0.04
        if self.arm_opened:
            reward += 0.005
        if self.button_opened:
            reward += 0.005
        if death:
            reward -= 20.0
        if win:
            reward += 100.0

        obs = self._obs_all()
        rewards = {agent: float(reward) for agent in AGENTS}
        terminateds = {agent: bool(death or win) for agent in AGENTS}
        truncateds = {agent: bool(truncated) for agent in AGENTS}
        terminateds["__all__"] = bool(death or win)
        truncateds["__all__"] = bool(truncated)
        infos = {agent: {"death": death, "win": win, "steps": self.steps} for agent in AGENTS}

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
        else:
            self.fire = PlayerState(60, 742)
            self.water = PlayerState(60, 572)
            self.platforms = [
                pygame.Rect(0, 792, 1100, 10), pygame.Rect(10, 680, 350, 20),
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
            self.hazards = [
                Hazard(pygame.Rect(518, 792, 180, 20), "fire"),
                Hazard(pygame.Rect(758, 792, 180, 20), "water"),
                Hazard(pygame.Rect(686, 622, 160, 20), "poison"),
            ]
            self.red_gems = {(290, 50), (200, 360), (1020, 650), (545, 731)}
            self.blue_gems = {(60, 130), (700, 390), (550, 556), (775, 731)}
            self.box = None
            self.button_rect = pygame.Rect(300, 406, 55, 20)

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
            if rect.colliderect(platform) and player.vy >= 0 and rect.bottom - player.vy <= platform.top + 4:
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
            if fire_rect.colliderect(arm_rect) or water_rect.colliderect(arm_rect):
                self.arm_opened = True
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
        fire_rect = self._rect(self.fire)
        water_rect = self._rect(self.water)
        for hazard in self.hazards:
            if hazard.kind in ("water", "poison") and fire_rect.colliderect(hazard.rect):
                return True
            if hazard.kind in ("fire", "poison") and water_rect.colliderect(hazard.rect):
                return True
        return False

    def _both_idle(self, action_dict: dict[str, int]) -> bool:
        return int(action_dict.get(FIREBOY, ACTION_NOOP)) == ACTION_NOOP and int(action_dict.get(WATERGIRL, ACTION_NOOP)) == ACTION_NOOP

    def _team_distance(self) -> float:
        return self._distance_to_rect(self.fire, self.fire_door) + self._distance_to_rect(self.water, self.water_door)

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
        nearest_hazard = self._nearest_hazard(own)
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

    def _nearest_hazard(self, player: PlayerState) -> tuple[float, float]:
        if not self.hazards:
            return 0.0, 0.0
        rect = self._rect(player)
        hazard = min(self.hazards, key=lambda item: math.hypot(rect.centerx - item.rect.centerx, rect.centery - item.rect.centery))
        return float(hazard.rect.centerx), float(hazard.rect.centery)

    def _rect(self, player: PlayerState) -> pygame.Rect:
        return pygame.Rect(int(player.x), int(player.y), self.player_w, self.player_h)
