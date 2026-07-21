"""
menu.py
-------
STEP 2: Main menu UI.

Contains:
  Button   - a single clickable menu item with a smooth hover animation
  MainMenu - owns all buttons, the title text, and reports back which
             action the player picked (so main.py can react to it)

Design choice: MainMenu doesn't know anything about pygame events directly
handling "what to do" -- it just tells main.py "the player clicked PLAY"
and main.py decides what that means. This keeps menu.py reusable and
main.py in charge of overall game flow.
"""

import math

import pygame

import settings


class Button:
    """A single menu button with a hover-glow animation."""

    def __init__(self, label, center_pos, action, width=280, height=56):
        self.label = label
        self.action = action  # a short string identifying what this button does
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = center_pos

        self.is_hovered = False
        # hover_amount smoothly animates 0 -> 1 when hovered, 1 -> 0 when not
        # (instead of snapping instantly, this makes hover feel "alive")
        self.hover_amount = 0.0

        self.font = pygame.font.SysFont("consolas", 28, bold=True)

    def update(self, dt, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        target = 1.0 if self.is_hovered else 0.0
        # Simple ease-toward-target animation (framerate independent enough
        # for a menu -- good enough here, we'll do proper tweening later)
        animation_speed = 8.0
        self.hover_amount += (target - self.hover_amount) * min(1.0, animation_speed * dt)

    def draw(self, surface):
        # Interpolate color + slight scale based on hover_amount
        base_color = settings.NEON_BLUE
        hover_color = settings.NEON_GREEN
        color = tuple(
            int(base_color[i] + (hover_color[i] - base_color[i]) * self.hover_amount)
            for i in range(3)
        )

        scale = 1.0 + 0.06 * self.hover_amount
        draw_rect = self.rect.copy()
        draw_rect.width = int(self.rect.width * scale)
        draw_rect.height = int(self.rect.height * scale)
        draw_rect.center = self.rect.center

        # Glow behind the button when hovered
        if self.hover_amount > 0.01:
            glow_surf = pygame.Surface(
                (draw_rect.width + 40, draw_rect.height + 40), pygame.SRCALPHA
            )
            alpha = int(80 * self.hover_amount)
            pygame.draw.rect(
                glow_surf, (*hover_color, alpha),
                glow_surf.get_rect(), border_radius=16
            )
            surface.blit(
                glow_surf,
                (draw_rect.centerx - glow_surf.get_width() // 2,
                 draw_rect.centery - glow_surf.get_height() // 2)
            )

        pygame.draw.rect(surface, (15, 15, 35), draw_rect, border_radius=12)
        pygame.draw.rect(surface, color, draw_rect, width=2, border_radius=12)

        text_surf = self.font.render(self.label, True, settings.WHITE)
        text_rect = text_surf.get_rect(center=draw_rect.center)
        surface.blit(text_surf, text_rect)


class MainMenu:
    """Owns the title + all buttons. Call update(), draw(), and
    handle_click() from main.py's game loop."""

    def __init__(self):
        self.title_font = pygame.font.SysFont("consolas", 64, bold=True)
        self.subtitle_font = pygame.font.SysFont("consolas", 18)
        self.time_elapsed = 0.0

        center_x = settings.SCREEN_WIDTH // 2
        start_y = 320
        gap = 62

        labels_and_actions = [
            ("PLAY", "play"),
            ("HANGAR", "hangar"),
            ("CONTROLS", "controls"),
            ("HIGH SCORES", "high_scores"),
            ("SETTINGS", "settings"),
            ("EXIT", "exit"),
        ]

        self.buttons = [
            Button(label, (center_x, start_y + i * gap), action)
            for i, (label, action) in enumerate(labels_and_actions)
        ]

    def update(self, dt, mouse_pos):
        self.time_elapsed += dt
        for button in self.buttons:
            button.update(dt, mouse_pos)

    def draw(self, surface):
        # Title with a gentle floating bob + glow
        bob_offset = math.sin(self.time_elapsed * 1.5) * 6
        title_y = 150 + bob_offset

        title_surf = self.title_font.render(settings.GAME_TITLE.upper(), True, settings.NEON_BLUE)
        title_rect = title_surf.get_rect(center=(settings.SCREEN_WIDTH // 2, title_y))

        # Cheap glow: draw the title a few times slightly offset with low alpha
        glow_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for offset in range(6, 0, -2):
            glow_text = self.title_font.render(
                settings.GAME_TITLE.upper(), True, (*settings.NEON_BLUE, 25)
            )
            glow_rect = glow_text.get_rect(center=(title_rect.centerx, title_rect.centery))
            glow_surf.blit(glow_text, (glow_rect.x - offset, glow_rect.y))
            glow_surf.blit(glow_text, (glow_rect.x + offset, glow_rect.y))
        surface.blit(glow_surf, (0, 0))

        surface.blit(title_surf, title_rect)

        subtitle_surf = self.subtitle_font.render(
            "GESTURE CONTROLLED SPACE SHOOTER", True, settings.NEON_PURPLE
        )
        subtitle_rect = subtitle_surf.get_rect(
            center=(settings.SCREEN_WIDTH // 2, title_y + 50)
        )
        surface.blit(subtitle_surf, subtitle_rect)

        for button in self.buttons:
            button.draw(surface)

    def handle_click(self, mouse_pos):
        """Returns the action string of the clicked button, or None."""
        for button in self.buttons:
            if button.rect.collidepoint(mouse_pos):
                return button.action
        return None