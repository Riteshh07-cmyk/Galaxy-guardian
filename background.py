"""
background.py
--------------
Minimal premium background: deep gradient sky, a sparse single star
layer, and the occasional slow-drifting planet. No nebula clutter, no
asteroid clutter -- calm and clean instead of busy.
"""

import random
import math

import pygame

import settings
import theme


class Star:
    def __init__(self):
        self.x = random.uniform(0, settings.SCREEN_WIDTH)
        self.y = random.uniform(0, settings.SCREEN_HEIGHT)
        self.size = random.choice([1, 1, 1, 2])
        self.speed = random.uniform(10, 40)
        self.twinkle_phase = random.uniform(0, math.tau)
        self.twinkle_speed = random.uniform(1.0, 2.2)

    def update(self, dt, speed_mult=1.0):
        self.y += self.speed * speed_mult * dt
        if self.y > settings.SCREEN_HEIGHT:
            self.y = 0
            self.x = random.uniform(0, settings.SCREEN_WIDTH)
        self.twinkle_phase += self.twinkle_speed * dt

    def draw(self, surface):
        brightness = 0.5 + 0.5 * (0.5 + 0.5 * math.sin(self.twinkle_phase))
        color = theme.shade(theme.INK_WHITE, brightness)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size)


class Planet:
    """A single soft, minimally-shaded sphere drifting by occasionally --
    no ring, no bands, no glow clutter. Just clean gradient shading."""

    def __init__(self):
        self.radius = random.randint(40, 70)
        self.x = random.uniform(self.radius, settings.SCREEN_WIDTH - self.radius)
        self.y = random.uniform(-260, -self.radius)
        self.speed = random.uniform(3, 6)
        self.color = random.choice([theme.ACCENT_CYAN, theme.ACCENT_MAGENTA, theme.ACCENT_GOLD])
        self._surf = self._build_surface()

    def _build_surface(self):
        r = self.radius
        pad = int(r * 1.3)
        surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        cx, cy = pad, pad
        steps = 8
        for i in range(steps, 0, -1):
            frac = i / steps
            shade_factor = 0.3 + 0.7 * (1 - frac)
            offset = r * (1 - frac) * 0.5
            ox, oy = cx - offset, cy - offset
            pygame.draw.circle(surf, theme.shade(self.color, shade_factor), (int(ox), int(oy)), int(r * frac) + 1)
        pygame.draw.circle(surf, (*theme.shade(self.color, 0.25), 140), (cx, cy), r, width=1)
        return surf

    def update(self, dt):
        self.y += self.speed * dt
        if self.y - self.radius > settings.SCREEN_HEIGHT:
            self.__init__()
            self.y = -self.radius

    def draw(self, surface):
        pad = self._surf.get_width() / 2
        surface.blit(self._surf, (self.x - pad, self.y - pad))


class Starfield:
    """Minimal version: gradient sky backdrop, one sparse star layer,
    and a rare drifting planet. No nebula clouds, no asteroids."""

    def __init__(self, num_stars=70, num_planets=1):
        self.stars = [Star() for _ in range(num_stars)]
        self.planets = [Planet() for _ in range(num_planets)]
        self._sky = self._build_sky()

    def _build_sky(self):
        surf = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        theme.draw_vertical_gradient(
            surf, (0, 0, settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT),
            theme.BG_PANEL, theme.BG_DEEP,
        )
        return surf

    def update(self, dt, speed_mult=1.0):
        for star in self.stars:
            star.update(dt, speed_mult)
        for planet in self.planets:
            planet.update(dt)

    def draw(self, surface):
        surface.blit(self._sky, (0, 0))
        for planet in self.planets:
            planet.draw(surface)
        for star in self.stars:
            star.draw(surface)