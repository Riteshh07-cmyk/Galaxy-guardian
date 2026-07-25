"""
hazard.py
---------
STEP 10: Boost hazards -- the "risk" side of extreme speed.

The open-palm boost makes you fast, but going that fast is dangerous:
while it's active, jagged energy-barrier debris streaks in from above and
you have to physically dodge it (Temple-Run style) or it wrecks your
hull. Unlike enemies, these can't be shot down -- the only way through
is around.

Kept deliberately separate from enemy.py: hazards have no health, don't
chase the player, and deal a big one-shot chunk of damage instead of a
small per-touch amount, so they read as "obstacle" rather than "foe".
"""

import math
import random

import pygame

import settings


class Hazard:
    def __init__(self):
        self.size = random.randint(26, 40)
        self.x = random.uniform(self.size, settings.SCREEN_WIDTH - self.size)
        self.y = -self.size - random.uniform(0, 60)

        # Hazards fall fast and mostly straight, with a little sideways
        # drift so they can't be dodged by just holding still.
        self.speed_y = random.uniform(360, 480)
        self.speed_x = random.uniform(-70, 70)

        self.damage = random.randint(28, 40)
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-220, 220)
        self.pulse_phase = random.uniform(0, math.tau)
        self.points = self._make_shape()
        self.alive = True

    def _make_shape(self):
        # Jagged crystalline shard -- visually distinct from the rounded
        # asteroids and the sleek enemy ships, so it reads as "hazard".
        pts = []
        num_points = random.randint(6, 8)
        for i in range(num_points):
            angle = (i / num_points) * math.tau
            r = self.size * random.uniform(0.55, 1.0)
            pts.append((math.cos(angle) * r, math.sin(angle) * r))
        return pts

    def update(self, dt):
        self.y += self.speed_y * dt
        self.x += self.speed_x * dt
        self.rotation += self.rotation_speed * dt
        self.pulse_phase += dt * 10
        self.x = max(self.size, min(settings.SCREEN_WIDTH - self.size, self.x))

    def is_offscreen(self):
        return self.y - self.size > settings.SCREEN_HEIGHT + 40

    def get_rect(self):
        # Slightly smaller than the visual shape so near-misses feel fair.
        hit_size = self.size * 1.5
        return pygame.Rect(
            int(self.x - hit_size / 2), int(self.y - hit_size / 2),
            hit_size, hit_size
        )

    def draw(self, surface):
        angle_rad = math.radians(self.rotation)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        transformed = [
            (self.x + px * cos_a - py * sin_a, self.y + px * sin_a + py * cos_a)
            for px, py in self.points
        ]

        # Pulsing danger glow so it reads as "don't touch" at a glance
        pulse = 0.6 + 0.4 * abs(math.sin(self.pulse_phase))
        glow_radius = int(self.size * 1.8)
        glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        alpha = int(70 * pulse)
        pygame.draw.circle(glow_surf, (*settings.DANGER_RED, alpha), (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surf, (int(self.x) - glow_radius, int(self.y) - glow_radius))

        pygame.draw.polygon(surface, (120, 20, 30), transformed)
        pygame.draw.polygon(surface, settings.DANGER_RED, transformed, width=2)

        # Little warning glint in the center
        pygame.draw.circle(surface, (255, 200, 200), (int(self.x), int(self.y)), max(2, self.size // 8))


def spawn_hazard():
    return Hazard()