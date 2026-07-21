"""
bullet.py
---------
STEP 8: Laser bullets, now supporting angled movement (not just straight up).

A bullet has a velocity (vx, vy) instead of a fixed "speed" -- this is
what lets weapons.py create spread shots (bullets fired at different
angles) using the same Bullet class as straight-shooting weapons.

Collision with enemies is still a later step (collision.py) -- for now
bullets just fly and disappear once they leave the screen.
"""

import pygame

import settings


class Bullet:
    def __init__(self, x, y, vx=0.0, vy=-780.0, width=5, height=18,
                 color=None, damage=1, glow=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.width = width
        self.height = height
        self.color = color if color is not None else settings.NEON_GREEN
        self.damage = damage  # not used yet -- collision.py will read this later
        self.glow = glow
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Off-screen in ANY direction (spread shots can drift sideways,
        # not just travel straight up) -- a little margin so it disappears
        # just after leaving view, not abruptly at the exact edge.
        margin = 40
        if (self.y < -margin or self.y > settings.SCREEN_HEIGHT + margin or
                self.x < -margin or self.x > settings.SCREEN_WIDTH + margin):
            self.alive = False

    def get_rect(self):
        """Bounding box, used later for collision detection against enemies."""
        return pygame.Rect(
            int(self.x - self.width / 2), int(self.y - self.height / 2),
            self.width, self.height
        )

    def draw(self, surface):
        rect = self.get_rect()

        if self.glow:
            glow_surf = pygame.Surface((self.width + 12, self.height + 12), pygame.SRCALPHA)
            pygame.draw.rect(
                glow_surf, (*self.color, 90),
                glow_surf.get_rect(), border_radius=6
            )
            surface.blit(glow_surf, (rect.x - 6, rect.y - 6))

        pygame.draw.rect(surface, self.color, rect, border_radius=2)
        pygame.draw.rect(surface, settings.WHITE, rect, width=1, border_radius=2)