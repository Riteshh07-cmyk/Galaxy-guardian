"""
pickups.py
----------
Collectible credit coins -- the actual "earn money during the run"
mechanic. Previously credits only came from a flat `score // 5` bonus
tallied up at game-over; this adds a real mid-run loop: killing an enemy
has a chance to drop a coin, a boss kill always drops a whole burst of
them, and flying through one adds to your credits immediately (with a
little floating "+N" popup for feedback).

Kept deliberately separate from enemy.py/hazard.py: coins have no health,
don't damage the player, and despawn on a timer if never collected rather
than falling forever.
"""

import math
import random

import pygame

import settings

COIN_DROP_CHANCE = 0.35        # chance a regular enemy kill drops one
COIN_VALUE_RANGE = (4, 12)
BOSS_COIN_VALUE_RANGE = (10, 20)


class Coin:
    def __init__(self, x, y, value=None, vx=0.0, vy=None):
        self.x = x
        self.y = y
        self.value = value if value is not None else random.randint(*COIN_VALUE_RANGE)
        self.vx = vx
        self.vy = vy if vy is not None else random.uniform(55, 90)
        self.size = 10
        self.spin_phase = random.uniform(0, math.tau)
        self.age = 0.0
        self.lifetime = 6.0  # despawns if never collected
        self.alive = True

    def update(self, dt):
        self.age += dt
        self.y += self.vy * dt
        self.x += self.vx * dt
        self.vx *= 0.98  # any initial "burst" scatter velocity settles down
        self.vy = min(self.vy + 40 * dt, 140)  # gentle gravity-ish drift, capped
        self.spin_phase += dt * 6
        self.x = max(self.size, min(settings.SCREEN_WIDTH - self.size, self.x))
        if self.age > self.lifetime or self.y - self.size > settings.SCREEN_HEIGHT + 40:
            self.alive = False

    def get_rect(self):
        return pygame.Rect(
            int(self.x - self.size), int(self.y - self.size),
            self.size * 2, self.size * 2
        )

    def draw(self, surface):
        # Fade out in the last second of its life instead of just
        # vanishing abruptly if the player never grabs it.
        fade = 1.0
        if self.age > self.lifetime - 1.0:
            fade = max(0.0, self.lifetime - self.age)

        # A coin "spinning" is just a horizontal squash-and-stretch loop.
        squash = abs(math.cos(self.spin_phase))
        w = max(2, int(self.size * (0.35 + 0.65 * squash)))
        h = self.size

        pad = h + 6
        coin_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        pygame.draw.circle(coin_surf, (*settings.GOLD, int(70 * fade)), (pad, pad), h + 4)
        body_rect = pygame.Rect(0, 0, w * 2, h * 2)
        body_rect.center = (pad, pad)
        pygame.draw.ellipse(coin_surf, (*settings.GOLD, int(255 * fade)), body_rect)
        pygame.draw.ellipse(coin_surf, (*settings.WHITE, int(200 * fade)), body_rect, width=1)
        # A little glint that only shows when the coin is near "edge-on"
        if squash < 0.35:
            pygame.draw.line(coin_surf, (*settings.WHITE, int(220 * fade)),
                              (pad, pad - h + 2), (pad, pad + h - 2), width=1)
        surface.blit(coin_surf, (self.x - pad, self.y - pad))


def maybe_drop_coin(x, y, chance=COIN_DROP_CHANCE):
    """Call on a regular enemy kill. Returns a Coin or None."""
    if random.random() < chance:
        return Coin(x, y)
    return None


def spawn_boss_coin_burst(x, y, count=10):
    """Call once when a boss dies -- scatters a whole handful of coins
    outward from the boss's position."""
    coins = []
    for _ in range(count):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(60, 170)
        coins.append(Coin(
            x, y, value=random.randint(*BOSS_COIN_VALUE_RANGE),
            vx=math.cos(angle) * speed, vy=math.sin(angle) * speed - 60
        ))
    return coins