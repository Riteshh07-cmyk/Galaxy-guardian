import math
import random

import pygame

import settings


ENEMY_TYPES = {
    "drone": {
        "health": 1, "speed": 70, "size": 24, "score": 50,
        "color": (120, 220, 255), "pattern": "straight", "collision_damage": 10,
    },
    "fighter": {
        "health": 2, "speed": 85, "size": 28, "score": 90,
        "color": (255, 140, 140), "pattern": "zigzag", "collision_damage": 15,
    },
    "tank": {
        "health": 5, "speed": 45, "size": 42, "score": 150,
        "color": (150, 150, 160), "pattern": "straight", "collision_damage": 25,
    },
    "interceptor": {
        "health": 2, "speed": 130, "size": 22, "score": 110,
        "color": (255, 220, 90), "pattern": "tracking", "collision_damage": 15,
    },
    "kamikaze": {
        "health": 1, "speed": 100, "size": 20, "score": 70,
        "color": (255, 80, 80), "pattern": "dive", "collision_damage": 30,
    },
    "stealth": {
        "health": 3, "speed": 75, "size": 26, "score": 130,
        "color": (150, 80, 220), "pattern": "circular", "collision_damage": 15,
    },
}

ENEMY_ORDER = list(ENEMY_TYPES.keys())


class Enemy:
    def __init__(self, enemy_type, x, y):
        cfg = ENEMY_TYPES[enemy_type]
        self.enemy_type = enemy_type
        self.x = x
        self.y = y
        self.spawn_x = x
        self.health = cfg["health"]
        self.max_health = cfg["health"]
        self.speed = cfg["speed"]
        self.size = cfg["size"]
        self.score_value = cfg["score"]
        self.color = cfg["color"]
        self.pattern = cfg["pattern"]
        self.collision_damage = cfg["collision_damage"]
        self.alive = True
        self.time_alive = 0.0
        self.circle_angle = random.uniform(0, math.tau)

    def update(self, dt, player_x, player_y):
        self.time_alive += dt

        if self.pattern == "straight":
            self.y += self.speed * dt

        elif self.pattern == "zigzag":
            self.y += self.speed * dt
            self.x = self.spawn_x + math.sin(self.time_alive * 4) * 80

        elif self.pattern == "tracking":
            dx = player_x - self.x
            dy = player_y - self.y
            dist = math.hypot(dx, dy)
            if dist > 1:
                self.x += (dx / dist) * self.speed * dt
                self.y += (dy / dist) * self.speed * dt

        elif self.pattern == "dive":
            if self.time_alive < 0.6:
                self.y += self.speed * 0.5 * dt
            else:
                dx = player_x - self.x
                dy = player_y - self.y
                dist = math.hypot(dx, dy)
                if dist > 1:
                    self.x += (dx / dist) * self.speed * dt
                    self.y += (dy / dist) * self.speed * dt

        elif self.pattern == "circular":
            self.y += self.speed * 0.6 * dt
            self.circle_angle += dt * 3
            self.x = self.spawn_x + math.sin(self.circle_angle) * 60

        self.x = max(self.size, min(settings.SCREEN_WIDTH - self.size, self.x))

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.alive = False

    def is_offscreen(self):
        return self.y - self.size > settings.SCREEN_HEIGHT + 40

    def get_rect(self):
        return pygame.Rect(
            int(self.x - self.size / 2), int(self.y - self.size / 2),
            self.size, self.size
        )

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        s = self.size
        hw, hh = s / 2, s / 2

        # engine trail above the ship (they fly nose-down, toward the player)
        flicker = 0.6 + 0.4 * abs(math.sin(self.time_alive * 12))
        flame_len = 10 * flicker
        pygame.draw.polygon(surface, settings.GOLD, [
            (cx - 4, cy - hh + 2), (cx + 4, cy - hh + 2), (cx, cy - hh - flame_len)
        ])

        if self.enemy_type == "drone":
            body = [(cx, cy + hh), (cx - hw, cy - hh * 0.3), (cx, cy - hh), (cx + hw, cy - hh * 0.3)]
            pygame.draw.polygon(surface, self.color, body)
            pygame.draw.polygon(surface, settings.WHITE, body, width=2)
            pygame.draw.circle(surface, settings.WHITE, (cx, cy), 3)

        elif self.enemy_type == "fighter":
            nose = (cx, cy + hh)
            body = [nose, (cx - hw * 0.35, cy - hh * 0.6), (cx + hw * 0.35, cy - hh * 0.6)]
            wing_l = [(cx - hw * 0.3, cy), (cx - hw, cy - hh * 0.7), (cx - hw * 0.25, cy - hh * 0.75)]
            wing_r = [(cx + hw * 0.3, cy), (cx + hw, cy - hh * 0.7), (cx + hw * 0.25, cy - hh * 0.75)]
            pygame.draw.polygon(surface, (120, 40, 40), wing_l)
            pygame.draw.polygon(surface, (120, 40, 40), wing_r)
            pygame.draw.polygon(surface, self.color, body)
            pygame.draw.polygon(surface, settings.WHITE, body, width=2)

        elif self.enemy_type == "tank":
            rect = pygame.Rect(cx - hw, cy - hh, s, s)
            pygame.draw.rect(surface, self.color, rect, border_radius=6)
            pygame.draw.rect(surface, settings.DANGER_RED, rect, width=2, border_radius=6)
            pygame.draw.rect(surface, (90, 90, 100), (cx - hw - 6, cy - 4, 6, 10))
            pygame.draw.rect(surface, (90, 90, 100), (cx + hw, cy - 4, 6, 10))
            pygame.draw.circle(surface, settings.DANGER_RED, (cx, cy), 5)

        elif self.enemy_type == "interceptor":
            pts = [(cx, cy + hh), (cx - hw, cy), (cx, cy - hh), (cx + hw, cy)]
            pygame.draw.polygon(surface, self.color, pts)
            pygame.draw.polygon(surface, settings.WHITE, pts, width=1)

        elif self.enemy_type == "kamikaze":
            pts = [(cx, cy + hh), (cx - hw * 0.7, cy - hh * 0.6), (cx, cy - hh * 0.2), (cx + hw * 0.7, cy - hh * 0.6)]
            glow = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*self.color, 80), (s, s), s)
            surface.blit(glow, (cx - s, cy - s))
            pygame.draw.polygon(surface, self.color, pts)
            pygame.draw.polygon(surface, settings.WHITE, pts, width=1)

        elif self.enemy_type == "stealth":
            pts = [(cx, cy + hh), (cx - hw, cy - hh * 0.2), (cx - hw * 0.3, cy - hh), (cx + hw * 0.3, cy - hh), (cx + hw, cy - hh * 0.2)]
            alpha_surf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
            shifted = [(px - cx + s, py - cy + s) for px, py in pts]
            pygame.draw.polygon(alpha_surf, (*self.color, 150), shifted)
            surface.blit(alpha_surf, (cx - s, cy - s))

        if self.max_health > 1:
            bar_w = s
            bar_h = 4
            fill = bar_w * (self.health / self.max_health)
            bar_rect = pygame.Rect(cx - bar_w // 2, cy - s // 2 - 10, bar_w, bar_h)
            pygame.draw.rect(surface, (60, 60, 60), bar_rect)
            pygame.draw.rect(surface, settings.NEON_GREEN, (bar_rect.x, bar_rect.y, fill, bar_h))


def spawn_random_enemy(level=1):
    enemy_type = random.choice(ENEMY_ORDER)
    size = ENEMY_TYPES[enemy_type]["size"]
    x = random.uniform(size, settings.SCREEN_WIDTH - size)
    y = -size
    enemy = Enemy(enemy_type, x, y)
    enemy.speed *= 1 + 0.06 * (level - 1)
    bonus_health = (level - 1) // 3
    if bonus_health > 0:
        enemy.health += bonus_health
        enemy.max_health = enemy.health
    return enemy