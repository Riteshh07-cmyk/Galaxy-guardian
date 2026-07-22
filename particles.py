"""
particles.py
------------
STEP 9: A tiny, dependency-free particle system.

Why this exists: right now enemies just vanish the instant their health
hits zero, and firing/boosting have no "impact". A real arcade shooter
sells every hit through juice -- explosions, sparks, trails -- even
though the underlying gameplay logic doesn't change at all. This module
is purely visual and purely additive: nothing here affects health,
damage, or score.

ParticleSystem owns a flat list of Particle objects and exposes a few
"spawn_*" convenience methods for the specific effects the game needs
(explosion, hit spark, muzzle burst, boost trail). main.py just calls
particles.update(dt) / particles.draw(screen) once per frame, same
pattern as every other game object.
"""

import math
import random

import pygame


class Particle:
    """A single fading, moving dot. Shrinks and fades out over its
    lifetime; optionally affected by gravity (used for debris chunks)."""

    def __init__(self, x, y, vx, vy, life, color, size, gravity=0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity

    @property
    def alive(self):
        return self.life > 0

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.life -= dt

    def draw(self, surface):
        if self.life <= 0:
            return
        progress = max(0.0, self.life / self.max_life)  # 1.0 -> 0.0
        alpha = int(255 * progress)
        size = max(1, int(self.size * (0.4 + 0.6 * progress)))

        # Soft additive glow behind the solid dot -- this is what makes
        # explosions/sparks read as "energy" instead of flat pixels.
        glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(
            glow_surf, (*self.color, alpha // 3),
            (size * 2, size * 2), size * 2
        )
        surface.blit(
            glow_surf, (self.x - size * 2, self.y - size * 2),
            special_flags=pygame.BLEND_RGBA_ADD
        )

        dot_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(dot_surf, (*self.color, alpha), (size, size), size)
        surface.blit(dot_surf, (self.x - size, self.y - size))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)

    def clear(self):
        self.particles.clear()

    # ------------------------------------------------------------------
    # Enemy destroyed -- a proper burst instead of "poof, it's gone"
    # ------------------------------------------------------------------
    def spawn_explosion(self, x, y, color=(255, 160, 60), count=24):
        # Outer ring of colored debris flying outward
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(70, 280)
            life = random.uniform(0.35, 0.75)
            size = random.uniform(2, 5)
            self.particles.append(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                life, color, size
            ))
        # Bright white flash core -- short-lived, makes the initial pop
        # feel punchy
        for _ in range(8):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(20, 90)
            self.particles.append(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                random.uniform(0.12, 0.22), (255, 255, 255), random.uniform(3, 6)
            ))
        # A few slow, glowing embers that linger after the flash fades
        for _ in range(6):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(10, 50)
            self.particles.append(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                random.uniform(0.5, 0.9), color, random.uniform(1.5, 3), gravity=30
            ))

    # ------------------------------------------------------------------
    # Bullet lands but doesn't kill -- a quick spark at the impact point
    # ------------------------------------------------------------------
    def spawn_hit_spark(self, x, y, color=(255, 255, 190), count=7):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(50, 160)
            self.particles.append(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                random.uniform(0.1, 0.22), color, random.uniform(1.5, 3)
            ))

    # ------------------------------------------------------------------
    # Weapon fired -- small forward-facing burst at the ship's nose
    # ------------------------------------------------------------------
    def spawn_muzzle_burst(self, x, y, color, count=8):
        for _ in range(count):
            # Cone pointing "up" (negative Y), roughly +/-35 degrees wide
            angle = random.uniform(-math.pi / 2 - 0.6, -math.pi / 2 + 0.6)
            speed = random.uniform(80, 220)
            self.particles.append(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                random.uniform(0.1, 0.2), color, random.uniform(1.5, 3)
            ))

    # ------------------------------------------------------------------
    # Boost active -- a steady stream of trail particles behind the ship
    # ------------------------------------------------------------------
    def spawn_boost_trail(self, x, y, color=(120, 200, 255)):
        vx = random.uniform(-25, 25)
        vy = random.uniform(90, 180)
        self.particles.append(Particle(
            x + random.uniform(-8, 8), y, vx, vy,
            random.uniform(0.18, 0.35), color, random.uniform(2, 4)
        ))