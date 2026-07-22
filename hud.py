"""
hud.py
------
STEP 10: A proper heads-up display.

Replaces the old single line of plain debug text with a readable panel:
  - Ship name + an animated, color-coded HP bar with a % readout
  - A pulsing "LOW HP!" warning once health drops below 25%
  - Chip-style badges for SCORE / LEVEL / CREDITS
  - A weapon badge tinted to the current weapon's bullet color
  - Status bars for SHIELD and BOOST (active / recharging / ready)

Also owns the full-screen red "you got hit" flash. main.py just calls
hud.update(dt) once per frame, hud.trigger_hit_flash() whenever the
player actually takes damage, and hud.draw(...) / hud.draw_screen_flash(...)
during the draw phase.
"""

import math

import pygame

import settings


PANEL_X = 16
PANEL_Y = 60
BAR_WIDTH = 260
HP_BAR_HEIGHT = 22
STATUS_BAR_HEIGHT = 12
CHIP_ROW_HEIGHT = 52

HIT_FLASH_DURATION = 0.28
LOW_HP_RATIO = 0.25


def _lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_bar(surface, x, y, width, height, ratio, fill_color,
             bg_color=(22, 22, 40), border_color=(255, 255, 255),
             border_width=2, radius=6):
    """Generic rounded progress bar -- used for HP, shield, and boost."""
    ratio = max(0.0, min(1.0, ratio))
    bg_rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(surface, bg_color, bg_rect, border_radius=radius)
    fill_w = int(width * ratio)
    if fill_w > 0:
        pygame.draw.rect(surface, fill_color, pygame.Rect(x, y, fill_w, height), border_radius=radius)
    if border_color:
        pygame.draw.rect(surface, border_color, bg_rect, width=border_width, border_radius=radius)


class HUD:
    def __init__(self):
        self.label_font = pygame.font.SysFont("consolas", 14, bold=True)
        self.value_font = pygame.font.SysFont("consolas", 18, bold=True)
        self.ship_font = pygame.font.SysFont("consolas", 22, bold=True)
        self.warning_font = pygame.font.SysFont("consolas", 26, bold=True)

        self.time_elapsed = 0.0
        self.screen_flash_timer = 0.0

    def trigger_hit_flash(self):
        self.screen_flash_timer = HIT_FLASH_DURATION

    def update(self, dt):
        self.time_elapsed += dt
        self.screen_flash_timer = max(0.0, self.screen_flash_timer - dt)

    def draw_screen_flash(self, surface):
        """Call this LAST in the draw phase so the flash sits over everything."""
        if self.screen_flash_timer <= 0:
            return
        alpha = int(150 * (self.screen_flash_timer / HIT_FLASH_DURATION))
        flash_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        flash_surf.fill((255, 30, 30, alpha))
        surface.blit(flash_surf, (0, 0))

    def draw(self, surface, player, ship_label, score, level, credits_amount, weapon_label, weapon_color):
        x, y = PANEL_X, PANEL_Y

        # --- Ship name -------------------------------------------------
        ship_surf = self.ship_font.render(ship_label.upper(), True, settings.NEON_BLUE)
        surface.blit(ship_surf, (x, y))
        y += ship_surf.get_height() + 4

        # --- HP bar (color shifts green -> gold -> pulsing red) --------
        hp_ratio = player.hp_display / player.max_health if player.max_health else 0
        if hp_ratio > 0.6:
            hp_color = settings.NEON_GREEN
        elif hp_ratio > LOW_HP_RATIO:
            hp_color = settings.GOLD
        else:
            pulse = 0.5 + 0.5 * abs(math.sin(self.time_elapsed * 8))
            hp_color = _lerp_color((150, 20, 20), settings.DANGER_RED, pulse)

        border_color = settings.WHITE
        if hp_ratio <= LOW_HP_RATIO:
            pulse = 0.5 + 0.5 * abs(math.sin(self.time_elapsed * 10))
            border_color = _lerp_color(settings.WHITE, settings.DANGER_RED, pulse)

        draw_bar(surface, x, y, BAR_WIDTH, HP_BAR_HEIGHT, hp_ratio, hp_color, border_color=border_color)
        pct_surf = self.value_font.render(f"{max(0, int(round(hp_ratio * 100)))}%", True, settings.WHITE)
        surface.blit(pct_surf, pct_surf.get_rect(center=(x + BAR_WIDTH // 2, y + HP_BAR_HEIGHT // 2)))
        y += HP_BAR_HEIGHT + 6

        # --- Low HP warning ---------------------------------------------
        if hp_ratio <= LOW_HP_RATIO and hp_ratio > 0:
            pulse = 0.5 + 0.5 * abs(math.sin(self.time_elapsed * 10))
            warn_color = _lerp_color((120, 0, 0), settings.DANGER_RED, pulse)
            warn_surf = self.warning_font.render("\u26a0 LOW HP!", True, warn_color)
            surface.blit(warn_surf, (x, y))
            y += warn_surf.get_height() + 6

        # --- SCORE / LEVEL / CREDITS chips -------------------------------
        chips = [
            ("SCORE", str(score), settings.GOLD),
            ("LEVEL", str(level), settings.NEON_PURPLE),
            ("CREDITS", str(credits_amount), settings.NEON_GREEN),
        ]
        chip_x = x
        for label, value, color in chips:
            label_surf = self.label_font.render(label, True, (170, 170, 195))
            value_surf = self.value_font.render(value, True, color)
            chip_w = max(label_surf.get_width(), value_surf.get_width()) + 18
            chip_rect = pygame.Rect(chip_x, y, chip_w, CHIP_ROW_HEIGHT)
            pygame.draw.rect(surface, (14, 14, 30), chip_rect, border_radius=8)
            pygame.draw.rect(surface, color, chip_rect, width=2, border_radius=8)
            surface.blit(label_surf, (chip_rect.x + 9, chip_rect.y + 5))
            surface.blit(value_surf, (chip_rect.x + 9, chip_rect.y + 5 + label_surf.get_height() + 2))
            chip_x += chip_w + 10
        y += CHIP_ROW_HEIGHT + 10

        # --- Weapon badge, tinted to the weapon's bullet color -----------
        weapon_surf = self.value_font.render(weapon_label, True, settings.WHITE)
        weapon_rect = pygame.Rect(x, y, weapon_surf.get_width() + 36, 30)
        pygame.draw.rect(surface, (14, 14, 30), weapon_rect, border_radius=8)
        pygame.draw.rect(surface, weapon_color, weapon_rect, width=2, border_radius=8)
        pygame.draw.circle(surface, weapon_color, (weapon_rect.x + 15, weapon_rect.centery), 6)
        pygame.draw.circle(surface, settings.WHITE, (weapon_rect.x + 15, weapon_rect.centery), 6, width=1)
        surface.blit(weapon_surf, (weapon_rect.x + 28, weapon_rect.y + 6))
        y += weapon_rect.height + 10

        # --- Shield status bar --------------------------------------------
        if player.is_shielded:
            shield_ratio = player.shield_timer / player.shield_duration
            shield_color = settings.NEON_BLUE
            shield_text = f"SHIELD ACTIVE  {player.shield_timer:.1f}s"
        elif player.shield_cooldown_timer > 0:
            total = player.shield_duration + player.shield_cooldown
            shield_ratio = 1.0 - (player.shield_cooldown_timer / total)
            shield_color = (100, 100, 130)
            shield_text = "SHIELD RECHARGING"
        else:
            shield_ratio = 1.0
            shield_color = settings.NEON_BLUE
            shield_text = "SHIELD READY"

        label_surf = self.label_font.render(shield_text, True, (200, 205, 225))
        surface.blit(label_surf, (x, y))
        y += label_surf.get_height() + 2
        draw_bar(surface, x, y, BAR_WIDTH, STATUS_BAR_HEIGHT, shield_ratio, shield_color)
        y += STATUS_BAR_HEIGHT + 8

        # --- Boost status bar ----------------------------------------------
        if player.is_boosting:
            boost_ratio = player.boost_timer / player.boost_duration
            boost_color = settings.GOLD
            boost_text = f"BOOST ACTIVE  {player.boost_timer:.1f}s"
        elif player.boost_cooldown_timer > 0:
            total = player.boost_duration + player.boost_cooldown
            boost_ratio = 1.0 - (player.boost_cooldown_timer / total)
            boost_color = (100, 100, 130)
            boost_text = "BOOST RECHARGING"
        else:
            boost_ratio = 1.0
            boost_color = settings.GOLD
            boost_text = "BOOST READY"

        label_surf = self.label_font.render(boost_text, True, (200, 205, 225))
        surface.blit(label_surf, (x, y))
        y += label_surf.get_height() + 2
        draw_bar(surface, x, y, BAR_WIDTH, STATUS_BAR_HEIGHT, boost_ratio, boost_color)