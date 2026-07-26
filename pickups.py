"""
pickups.py
----------
Collectible credit coins -- the actual "earn money during the run"
mechanic. Killing an enemy has a good chance to drop coins (sometimes a
whole small cluster, not just one), a boss kill always scatters a big
treasure burst, and flying through a coin adds to your credits
immediately (with a little floating "+N" popup for feedback).

Visual design: coins spin as a proper little disc (embossed rim, a
moving specular highlight, a star emblem stamped in the middle) and
trail a short fading sparkle wake as they fall, instead of the flat
tinted blob from the first pass. Higher-value coins (big drops and every
boss coin) get a brighter "premium" cyan-white shimmer so the reward
size is readable from across the screen, not just from the popup text.

Kept deliberately separate from enemy.py/hazard.py: coins have no health,
don't damage the player, and despawn on a timer if never collected rather
than falling forever.
"""

import math
import random
from collections import deque

import pygame

import settings

COIN_DROP_CHANCE = 0.55        # chance a regular enemy kill drops coin(s)
CLUSTER_CHANCE = 0.22          # chance a drop is a small 2-3 coin cluster
COIN_VALUE_RANGE = (6, 16)
BOSS_COIN_VALUE_RANGE = (14, 30)
BOSS_COIN_BURST_COUNT = 18

PREMIUM_VALUE_THRESHOLD = 18   # coins worth at least this get the shimmer look
PREMIUM_COLOR = (170, 235, 255)
PREMIUM_RIM_COLOR = (90, 170, 220)
GOLD_RIM_COLOR = (150, 100, 20)


class Coin:
    def __init__(self, x, y, value=None, vx=0.0, vy=None):
        self.x = x
        self.y = y
        self.value = value if value is not None else random.randint(*COIN_VALUE_RANGE)
        self.vx = vx
        self.vy = vy if vy is not None else random.uniform(55, 90)
        self.size = 13
        self.spin_phase = random.uniform(0, math.tau)
        self.spin_speed = random.uniform(5.5, 7.0)
        self.age = 0.0
        self.lifetime = 6.0  # despawns if never collected
        self.alive = True

        self.premium = self.value >= PREMIUM_VALUE_THRESHOLD
        self.color = PREMIUM_COLOR if self.premium else settings.GOLD
        self.rim_color = PREMIUM_RIM_COLOR if self.premium else GOLD_RIM_COLOR

        # Short trailing sparkle wake, sampled a few times a second so it
        # reads as a light streak rather than a smear.
        self.trail = deque(maxlen=6)
        self._trail_timer = 0.0

    def update(self, dt):
        self.age += dt
        self.y += self.vy * dt
        self.x += self.vx * dt
        self.vx *= 0.98  # any initial "burst" scatter velocity settles down
        self.vy = min(self.vy + 40 * dt, 140)  # gentle gravity-ish drift, capped
        self.spin_phase += dt * self.spin_speed
        self.x = max(self.size, min(settings.SCREEN_WIDTH - self.size, self.x))

        self._trail_timer -= dt
        if self._trail_timer <= 0:
            self.trail.append((self.x, self.y))
            self._trail_timer = 0.035

        if self.age > self.lifetime or self.y - self.size > settings.SCREEN_HEIGHT + 40:
            self.alive = False

    def get_rect(self):
        return pygame.Rect(
            int(self.x - self.size), int(self.y - self.size),
            self.size * 2, self.size * 2
        )

    def _draw_trail(self, surface, fade):
        n = len(self.trail)
        if n < 2:
            return
        for i, (tx, ty) in enumerate(self.trail):
            trail_fade = (i / n) * fade
            if trail_fade <= 0.02:
                continue
            r = max(1, int(self.size * 0.32 * (i / n)))
            pad = r + 2
            spark_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
            pygame.draw.circle(spark_surf, (*self.color, int(120 * trail_fade)), (pad, pad), r)
            surface.blit(spark_surf, (tx - pad, ty - pad))

    def draw(self, surface):
        # Fade out in the last second of its life instead of just
        # vanishing abruptly if the player never grabs it.
        fade = 1.0
        if self.age > self.lifetime - 1.0:
            fade = max(0.0, self.lifetime - self.age)

        self._draw_trail(surface, fade)

        # A coin "spinning" is a horizontal squash-and-stretch loop --
        # squash close to 0 means we're seeing it edge-on.
        squash = abs(math.cos(self.spin_phase))
        w = max(2, int(self.size * (0.28 + 0.72 * squash)))
        h = self.size

        pad = h + 10
        coin_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        cx, cy = pad, pad

        # --- Soft ambient glow, pulsing a little so it catches the eye
        # against a busy background instead of blending in ---
        pulse = 0.75 + 0.25 * abs(math.sin(self.age * 5))
        glow_r = int((h + 7) * pulse)
        pygame.draw.circle(coin_surf, (*self.color, int(75 * fade)), (cx, cy), glow_r)

        body_rect = pygame.Rect(0, 0, w * 2, h * 2)
        body_rect.center = (cx, cy)

        # --- Embossed disc: darker rim behind a slightly smaller bright
        # face, so it reads as a coin with real thickness instead of a
        # flat painted ellipse ---
        pygame.draw.ellipse(coin_surf, (*self.rim_color, int(255 * fade)), body_rect)
        inner_rect = body_rect.inflate(-max(2, int(w * 0.22)), -max(2, int(h * 0.22)))
        pygame.draw.ellipse(coin_surf, (*self.color, int(255 * fade)), inner_rect)

        # --- Stamped star emblem in the middle, only really visible
        # face-on -- fades out as the coin turns edge-on, like a real
        # embossed detail catching/losing the light ---
        if squash > 0.28 and inner_rect.width > 6:
            star_alpha = int(180 * fade * squash)
            star_r_outer = inner_rect.height * 0.34
            star_r_inner = star_r_outer * 0.45
            star_scale_x = inner_rect.width / (inner_rect.height + 0.001)
            points = []
            for i in range(10):
                r = star_r_outer if i % 2 == 0 else star_r_inner
                a = math.pi / 2 + i * math.pi / 5
                points.append((
                    cx + math.cos(a) * r * star_scale_x,
                    cy - math.sin(a) * r,
                ))
            pygame.draw.polygon(coin_surf, (*self.rim_color, star_alpha), points)

        # --- Moving specular highlight -- a bright streak that sweeps
        # across the face as the coin rotates, the actual "shine" cue
        # that makes it look like polished metal rather than flat paint ---
        highlight_offset = math.sin(self.spin_phase) * w * 0.5
        highlight_rect = pygame.Rect(0, 0, max(2, int(w * 0.28)), int(h * 1.7))
        highlight_rect.center = (int(cx + highlight_offset), cy)
        highlight_alpha = int(150 * fade * (0.4 + 0.6 * squash))
        pygame.draw.ellipse(coin_surf, (*settings.WHITE, highlight_alpha), highlight_rect)

        pygame.draw.ellipse(coin_surf, (*settings.WHITE, int(210 * fade)), body_rect, width=1)

        # Sharp edge-on glint, same beat as before but brighter/whiter
        if squash < 0.3:
            pygame.draw.line(coin_surf, (*settings.WHITE, int(240 * fade)),
                              (cx, cy - h + 2), (cx, cy + h - 2), width=2)

        # Premium coins additionally get a soft rotating rainbow-ish
        # rim glint so a big reward is unmistakable at a glance.
        if self.premium:
            ring_pulse = 0.6 + 0.4 * abs(math.sin(self.age * 3))
            ring_r = int((h + 5) * ring_pulse)
            pygame.draw.circle(coin_surf, (*settings.WHITE, int(90 * fade)), (cx, cy), ring_r, width=2)

        surface.blit(coin_surf, (self.x - pad, self.y - pad))


def maybe_drop_coin(x, y, chance=COIN_DROP_CHANCE):
    """Call on a regular enemy kill. Returns a list of Coins -- usually
    empty, often a single coin, and sometimes (CLUSTER_CHANCE) a small
    2-3 coin cluster for a chunkier reward."""
    if random.random() >= chance:
        return []

    if random.random() < CLUSTER_CHANCE:
        count = random.randint(2, 3)
    else:
        count = 1

    coins = []
    for _ in range(count):
        coins.append(Coin(
            x + random.uniform(-14, 14), y + random.uniform(-10, 10),
            vx=random.uniform(-45, 45),
        ))
    return coins


def spawn_boss_coin_burst(x, y, count=BOSS_COIN_BURST_COUNT):
    """Call once when a boss dies -- scatters a big handful of coins
    outward from the boss's position."""
    coins = []
    for _ in range(count):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(60, 190)
        coins.append(Coin(
            x, y, value=random.randint(*BOSS_COIN_VALUE_RANGE),
            vx=math.cos(angle) * speed, vy=math.sin(angle) * speed - 60
        ))
    return coins