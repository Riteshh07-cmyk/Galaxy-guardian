"""
background.py
--------------
STEP 2: Animated space background.

Contains three layers of motion, all purely visual (no gameplay logic):
  1. Star  - tiny twinkling dots, multiple parallax layers (far/near)
  2. Planet - slow-drifting circles with an optional ring
  3. Asteroid - small rotating polygons drifting across the screen

Why classes for each? Because later, enemies/bullets/particles will follow
this exact same pattern (a class with update() and draw() methods), so
this is good practice for the structure the rest of the game will use.
"""

import random
import math

import pygame

import settings


class Star:
    """A single twinkling star. Belongs to one of several parallax layers."""

    def __init__(self, layer):
        self.x = random.uniform(0, settings.SCREEN_WIDTH)
        self.y = random.uniform(0, settings.SCREEN_HEIGHT)
        self.layer = layer  # 0 = far/small/slow, 2 = near/big/fast

        # Farther layers = smaller, dimmer, slower stars (parallax effect)
        self.size = 1 + layer
        self.speed = 15 + (layer * 25)  # pixels per second, drifting downward

        # Twinkle: each star oscillates its brightness on its own timer
        self.twinkle_phase = random.uniform(0, math.tau)
        self.twinkle_speed = random.uniform(1.5, 4.0)

    def update(self, dt, speed_mult=1.0):
        self.y += self.speed * speed_mult * dt
        if self.y > settings.SCREEN_HEIGHT:
            self.y = 0
            self.x = random.uniform(0, settings.SCREEN_WIDTH)
        self.twinkle_phase += self.twinkle_speed * dt

    def draw(self, surface):
        # Brightness oscillates between ~40% and 100% using a sine wave
        brightness = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(self.twinkle_phase))
        color = tuple(int(c * brightness) for c in settings.WHITE)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size)


class Planet:
    """A slow-drifting background planet with an optional ring."""

    def __init__(self):
        self.radius = random.randint(30, 70)
        self.x = random.uniform(0, settings.SCREEN_WIDTH)
        self.y = random.uniform(-200, -self.radius)  # start above screen
        self.speed = random.uniform(4, 10)
        self.color = random.choice(
            [settings.NEON_PURPLE, settings.NEON_BLUE, (200, 100, 60)]
        )
        self.has_ring = random.random() < 0.5

    def update(self, dt, speed_mult=1.0):
        self.y += self.speed * speed_mult * dt
        if self.y - self.radius > settings.SCREEN_HEIGHT:
            self.__init__()  # respawn as a "new" planet above the screen
            self.y = -self.radius

    def draw(self, surface):
        pos = (int(self.x), int(self.y))
        # Soft glow behind the planet (a few translucent circles)
        glow_surf = pygame.Surface(
            (self.radius * 4, self.radius * 4), pygame.SRCALPHA
        )
        for i in range(3, 0, -1):
            alpha = 15 * i
            glow_color = (*self.color, alpha)
            pygame.draw.circle(
                glow_surf, glow_color,
                (self.radius * 2, self.radius * 2), self.radius + i * 12
            )
        surface.blit(glow_surf, (pos[0] - self.radius * 2, pos[1] - self.radius * 2))

        pygame.draw.circle(surface, self.color, pos, self.radius)

        if self.has_ring:
            ring_rect = pygame.Rect(0, 0, self.radius * 2.6, self.radius * 0.8)
            ring_rect.center = pos
            pygame.draw.ellipse(surface, settings.WHITE, ring_rect, width=2)


class Asteroid:
    """A small rotating rocky polygon drifting diagonally across the screen."""

    def __init__(self):
        self.x = random.uniform(0, settings.SCREEN_WIDTH)
        self.y = random.uniform(-100, -20)
        self.size = random.randint(8, 20)
        self.speed_y = random.uniform(20, 45)
        self.speed_x = random.uniform(-10, 10)
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-60, 60)  # degrees/sec
        self.points = self._make_shape()

    def _make_shape(self):
        # A jagged circle-ish polygon so it reads as "rocky" not a smooth circle
        pts = []
        num_points = random.randint(6, 9)
        for i in range(num_points):
            angle = (i / num_points) * math.tau
            r = self.size * random.uniform(0.7, 1.0)
            pts.append((math.cos(angle) * r, math.sin(angle) * r))
        return pts

    def update(self, dt, speed_mult=1.0):
        self.y += self.speed_y * speed_mult * dt
        self.x += self.speed_x * speed_mult * dt
        self.rotation += self.rotation_speed * dt
        if self.y - self.size > settings.SCREEN_HEIGHT:
            self.__init__()

    def draw(self, surface):
        angle_rad = math.radians(self.rotation)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        transformed = [
            (
                self.x + px * cos_a - py * sin_a,
                self.y + px * sin_a + py * cos_a,
            )
            for px, py in self.points
        ]
        pygame.draw.polygon(surface, (120, 110, 100), transformed)
        pygame.draw.polygon(surface, (70, 65, 60), transformed, width=1)


class Starfield:
    """
    Owns and manages every background element. main.py only ever talks
    to this one object: starfield.update(dt) and starfield.draw(screen).
    """

    def __init__(self, num_stars_per_layer=40, num_planets=2, num_asteroids=6):
        self.stars = [
            Star(layer)
            for layer in range(3)
            for _ in range(num_stars_per_layer)
        ]
        self.planets = [Planet() for _ in range(num_planets)]
        self.asteroids = [Asteroid() for _ in range(num_asteroids)]

    def update(self, dt, speed_mult=1.0):
        for star in self.stars:
            star.update(dt, speed_mult)
        for planet in self.planets:
            planet.update(dt, speed_mult)
        for asteroid in self.asteroids:
            asteroid.update(dt, speed_mult)

    def draw(self, surface):
        surface.fill(settings.DARK_SPACE)
        # Draw order matters: planets behind stars behind asteroids
        # (planets furthest away, asteroids closest to camera)
        for planet in self.planets:
            planet.draw(surface)
        for star in self.stars:
            star.draw(surface)
        for asteroid in self.asteroids:
            asteroid.draw(surface)