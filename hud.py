"""
hud.py
------
STEP 10: A proper heads-up display.

Replaces the old single line of plain debug text with three segmented
"block" bars (health / shield / boost), little hand-drawn icons instead
of emoji (emoji don't render reliably through SysFont), a glowing weapon
name badge, and a pulsing low-HP warning. Everything here is pure
pygame.draw shapes -- no image assets required.
"""

import math

import pygame

import settings
import weapons


PANEL_X = 16
PANEL_Y = 16
BAR_WIDTH = 260
BAR_HEIGHT = 20
BAR_SEGMENTS = 16
ROW_GAP = 46


def _segmented_bar(surface, x, y, width, height, fraction, fill_color,
                    segments=BAR_SEGMENTS, bg_color=(25, 25, 40), border_color=None):
    """Draws a health-bar-style row of blocks, like '########..' but as
    real filled rectangles with a thin glowing border."""
    border_color = border_color or fill_color
    fraction = max(0.0, min(1.0, fraction))
    filled_segments = round(fraction * segments)

    gap = 3
    seg_w = (width - gap * (segments - 1)) / segments

    # Backing panel
    panel_rect = pygame.Rect(x - 4, y - 4, width + 8, height + 8)
    pygame.draw.rect(surface, (8, 8, 18), panel_rect, border_radius=6)
    pygame.draw.rect(surface, border_color, panel_rect, width=1, border_radius=6)

    for i in range(segments):
        seg_x = x + i * (seg_w + gap)
        seg_rect = pygame.Rect(int(seg_x), y, math.ceil(seg_w), height)
        if i < filled_segments:
            pygame.draw.rect(surface, fill_color, seg_rect, border_radius=2)
        else:
            pygame.draw.rect(surface, bg_color, seg_rect, border_radius=2)


def _draw_heart(surface, cx, cy, size, color):
    r = size / 2.4
    pygame.draw.circle(surface, color, (int(cx - r * 0.9), int(cy - r * 0.4)), int(r))
    pygame.draw.circle(surface, color, (int(cx + r * 0.9), int(cy - r * 0.4)), int(r))
    pygame.draw.polygon(surface, color, [
        (cx - size * 0.95, cy - r * 0.15),
        (cx + size * 0.95, cy - r * 0.15),
        (cx, cy + size * 0.95),
    ])


def _draw_shield_icon(surface, cx, cy, size, color):
    pts = [
        (cx, cy - size), (cx + size * 0.85, cy - size * 0.5),
        (cx + size * 0.85, cy + size * 0.25), (cx, cy + size),
        (cx - size * 0.85, cy + size * 0.25), (cx - size * 0.85, cy - size * 0.5),
    ]
    pygame.draw.polygon(surface, color, pts)
    pygame.draw.polygon(surface, settings.WHITE, pts, width=2)


def _draw_bolt_icon(surface, cx, cy, size, color):
    pts = [
        (cx + size * 0.15, cy - size), (cx - size * 0.55, cy + size * 0.15),
        (cx - size * 0.05, cy + size * 0.15), (cx - size * 0.15, cy + size),
        (cx + size * 0.55, cy - size * 0.15), (cx + size * 0.05, cy - size * 0.15),
    ]
    pygame.draw.polygon(surface, color, pts)
    pygame.draw.polygon(surface, settings.WHITE, pts, width=1)


class HUD:
    def __init__(self):
        self.label_font = pygame.font.SysFont("consolas", 15, bold=True)
        self.pct_font = pygame.font.SysFont("consolas", 15, bold=True)
        self.weapon_font = pygame.font.SysFont("consolas", 20, bold=True)
        self.stat_font = pygame.font.SysFont("consolas", 17, bold=True)
        self.warning_font = pygame.font.SysFont("consolas", 26, bold=True)
        self.time_elapsed = 0.0

    def update(self, dt):
        self.time_elapsed += dt

    def _draw_row(self, surface, y, icon_fn, icon_color, label, fraction, fill_color, extra_text=""):
        icon_cx, icon_cy = PANEL_X + 12, y + BAR_HEIGHT // 2
        icon_fn(surface, icon_cx, icon_cy, 11, icon_color)

        label_surf = self.label_font.render(label, True, settings.WHITE)
        surface.blit(label_surf, (PANEL_X + 30, y - 17))

        bar_x = PANEL_X + 30
        _segmented_bar(surface, bar_x, y, BAR_WIDTH, BAR_HEIGHT, fraction, fill_color)

        pct_text = extra_text if extra_text else f"{int(round(fraction * 100))}%"
        pct_surf = self.pct_font.render(pct_text, True, settings.WHITE)
        surface.blit(pct_surf, (bar_x + BAR_WIDTH + 10, y + BAR_HEIGHT // 2 - pct_surf.get_height() // 2))

    def draw(self, surface, player, score, level, credits_amount):
        y = PANEL_Y + 20

        # --- Health bar ---
        low_hp = player.health_fraction <= 0.25
        if low_hp:
            pulse = 0.5 + 0.5 * abs(math.sin(self.time_elapsed * 8))
            hp_color = tuple(int(c) for c in (
                settings.DANGER_RED[0],
                settings.DANGER_RED[1] * pulse * 0.5,
                settings.DANGER_RED[2] * pulse * 0.5,
            ))
        elif player.health_fraction <= 0.5:
            hp_color = settings.GOLD
        else:
            hp_color = settings.NEON_GREEN

        self._draw_row(
            surface, y, _draw_heart, settings.DANGER_RED,
            "HEALTH", player.health_fraction, hp_color
        )
        y += ROW_GAP

        # --- Shield bar ---
        if player.is_shielded:
            shield_frac = player.shield_timer / player.shield_duration
            shield_text = f"ACTIVE {player.shield_timer:.1f}s"
            shield_color = settings.NEON_BLUE
        elif player.shield_cooldown_timer > 0:
            total_cd = player.shield_duration + player.shield_cooldown
            shield_frac = 1.0 - (player.shield_cooldown_timer / total_cd)
            shield_text = f"CHARGING {player.shield_cooldown_timer:.1f}s"
            shield_color = (90, 110, 160)
        else:
            shield_frac = 1.0
            shield_text = "READY"
            shield_color = settings.NEON_BLUE

        self._draw_row(
            surface, y, _draw_shield_icon, settings.NEON_BLUE,
            "SHIELD", shield_frac, shield_color, extra_text=shield_text
        )
        y += ROW_GAP

        # --- Boost / extreme speed bar ---
        if player.boost_locked_out:
            boost_color = settings.DANGER_RED
            boost_text = "OVERHEAT"
        elif player.boosting:
            boost_color = settings.GOLD
            boost_text = f"{int(player.boost_fraction * 100)}%"
        else:
            boost_color = settings.NEON_PURPLE
            boost_text = f"{int(player.boost_fraction * 100)}%"

        self._draw_row(
            surface, y, _draw_bolt_icon, settings.GOLD,
            "EXTREME BOOST", player.boost_fraction, boost_color, extra_text=boost_text
        )
        y += ROW_GAP + 4

        # --- Weapon badge ---
        weapon_color = _weapon_color(player.weapon_name)
        weapon_label = f">> {weapons.get_label(player.weapon_name)} <<"
        weapon_surf = self.weapon_font.render(weapon_label, True, settings.WHITE)
        badge_rect = pygame.Rect(PANEL_X, y, weapon_surf.get_width() + 34, 34)
        glow_surf = pygame.Surface((badge_rect.width + 16, badge_rect.height + 16), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*weapon_color, 70), glow_surf.get_rect(), border_radius=12)
        surface.blit(glow_surf, (badge_rect.x - 8, badge_rect.y - 8))
        pygame.draw.rect(surface, (12, 12, 26), badge_rect, border_radius=8)
        pygame.draw.rect(surface, weapon_color, badge_rect, width=2, border_radius=8)
        pygame.draw.circle(surface, weapon_color, (badge_rect.x + 16, badge_rect.centery), 6)
        surface.blit(weapon_surf, (badge_rect.x + 26, badge_rect.centery - weapon_surf.get_height() // 2))
        y += 46

        # --- Score / Level / Credits strip ---
        stat_text = f"SCORE {score:,}   *   LV.{level}   *   {credits_amount:,} CR"
        stat_surf = self.stat_font.render(stat_text, True, settings.GOLD)
        surface.blit(stat_surf, (PANEL_X, y))

        # --- Low HP warning banner ---
        if low_hp:
            blink_on = int(self.time_elapsed * 6) % 2 == 0
            if blink_on:
                warn_surf = self.warning_font.render("!! HULL CRITICAL !!", True, settings.DANGER_RED)
                warn_rect = warn_surf.get_rect(midtop=(settings.SCREEN_WIDTH // 2, 60))
                glow = pygame.Surface((warn_rect.width + 30, warn_rect.height + 16), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*settings.DANGER_RED, 60), glow.get_rect(), border_radius=10)
                surface.blit(glow, (warn_rect.x - 15, warn_rect.y - 8))
                surface.blit(warn_surf, warn_rect)


def _weapon_color(weapon_name):
    colors = {
        "normal": settings.NEON_GREEN,
        "double": settings.NEON_BLUE,
        "triple": settings.NEON_PURPLE,
        "spread": settings.GOLD,
        "rapid": (255, 240, 120),
        "plasma": (255, 60, 200),
    }
    return colors.get(weapon_name, settings.NEON_GREEN)


def draw_screen_flash(surface, alpha, color):
    """Full-screen tinted overlay -- brief flash when the player is hit."""
    if alpha <= 0:
        return
    flash_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    flash_surf.fill((*color, int(alpha)))
    surface.blit(flash_surf, (0, 0))