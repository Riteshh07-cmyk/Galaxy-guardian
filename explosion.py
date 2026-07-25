"""
explosion.py
------------
STEP 9: Collision animation.

Whenever something is destroyed -- an enemy killed by a bullet, or the
player getting hit by an enemy -- we spawn one of these. It's a short,
self-contained burst that owns its own lifetime, so main.py just has to:

    explosions.append(Explosion(x, y, color=...))
    ...
    for e in explosions: e.update(dt)
    explosions = [e for e in explosions if e.alive]
    for e in explosions: e.draw(screen)

Visually it's three layered effects so it reads as "impact" rather than
just "particles":
  1. A bright white-hot flash at the center that fades almost instantly.
  2. An expanding, fading shockwave ring (matches the neon outline look
     used everywhere else in the game).
  3. A shower of colored particles (tinted to whatever died) that fly
     outward and drift/slow down like debris.
"""

import math
import random

import pygame

import settings


class Particle:
    """A single glowing ember flying outward from the impact point."""

    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(70, 280)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.size = random.uniform(2, 5)
        self.life = random.uniform(0.35, 0.7)
        self.age = 0.0

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        # Drag -- debris slows down instead of flying forever at full speed
        self.vx *= 0.92
        self.vy *= 0.92

    @property
    def alive(self):
        return self.age < self.life

    def draw(self, surface):
        progress = min(1.0, self.age / self.life)
        alpha = max(0, int(255 * (1 - progress)))
        size = max(0.6, self.size * (1 - progress * 0.55))
        pad = int(size) + 2
        particle_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        pygame.draw.circle(particle_surf, (*self.color, alpha), (pad, pad), size)
        surface.blit(particle_surf, (self.x - pad, self.y - pad))


class Explosion:
    """
    A full collision-death animation at a single point.

    big=True (used for player hits / tougher enemies) makes the shockwave
    ring and particle count noticeably larger, so a hit on the PLAYER
    reads as more significant than a small drone popping.
    """

    def __init__(self, x, y, color=None, big=False):
        self.x = x
        self.y = y
        self.color = color if color is not None else settings.GOLD

        num_particles = 32 if big else 18
        self.particles = [Particle(x, y, self.color) for _ in range(num_particles)]

        self.flash_timer = 0.14 if big else 0.10
        self.flash_max = self.flash_timer

        self.ring_radius = 4.0
        self.ring_max_radius = 90 if big else 46
        self.ring_speed = 320 if big else 200
        self.ring_alpha = 220.0
        self.ring_width = 4 if big else 3

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

        self.flash_timer = max(0.0, self.flash_timer - dt)
        self.ring_radius += self.ring_speed * dt
        self.ring_alpha = max(0.0, self.ring_alpha - dt * 460)

    @property
    def alive(self):
        return bool(self.particles) or self.ring_alpha > 0 or self.flash_timer > 0

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)

        # --- Expanding shockwave ring ---
        if self.ring_alpha > 0 and self.ring_radius < self.ring_max_radius:
            pad = self.ring_max_radius + 4
            ring_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                ring_surf, (*self.color, int(self.ring_alpha)),
                (pad, pad), int(self.ring_radius), width=self.ring_width
            )
            surface.blit(ring_surf, (cx - pad, cy - pad))

        # --- Particle debris ---
        for p in self.particles:
            p.draw(surface)

        # --- White-hot core flash (drawn last so it's the brightest thing) ---
        if self.flash_timer > 0:
            flash_progress = self.flash_timer / self.flash_max
            radius = int(6 + 20 * flash_progress)
            flash_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            alpha = int(255 * flash_progress)
            pygame.draw.circle(flash_surf, (*settings.WHITE, alpha), (radius, radius), radius)
            pygame.draw.circle(flash_surf, (*self.color, alpha), (radius, radius), radius, width=2)
            surface.blit(flash_surf, (cx - radius, cy - radius))