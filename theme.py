"""
theme.py
--------
Premium visual design system for Galaxy Guardian.

Goal: replace the "flat neon rectangles" look with something closer to a
modern premium HUD -- soft gradients, frosted-glass panels, subtle glows
and drop shadows, and a restrained, cohesive color palette instead of
every element picking its own saturated neon color.

Everything here is pure pygame -- no new dependencies. Other modules
(hud.py, menu.py, screens.py) import from here instead of hardcoding
colors/rects, so the whole game shares one visual identity.
"""

import math
import pygame


# ---------------------------------------------------------------------------
# PALETTE
# ---------------------------------------------------------------------------
BG_DEEP        = (8, 10, 18)
BG_PANEL       = (18, 22, 34)
BG_PANEL_LIGHT = (28, 33, 48)

INK_WHITE      = (238, 241, 248)
INK_MUTED      = (150, 160, 182)

ACCENT_CYAN    = (86, 214, 255)
ACCENT_GOLD    = (255, 196, 92)
ACCENT_MAGENTA = (224, 96, 196)
ACCENT_GREEN   = (98, 230, 168)
ACCENT_RED     = (255, 90, 96)

GLASS_BORDER   = (120, 150, 200)
GLASS_ALPHA    = 168

ROLE_HEALTH  = ACCENT_GREEN
ROLE_SHIELD  = ACCENT_CYAN
ROLE_BOOST   = ACCENT_GOLD
ROLE_DANGER  = ACCENT_RED
ROLE_ACCENT  = ACCENT_MAGENTA


def _clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(_clamp(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def shade(color, factor):
    return tuple(_clamp(c * factor) for c in color)


# ---------------------------------------------------------------------------
# FONTS
# ---------------------------------------------------------------------------

_FONT_CACHE = {}


def _find_font_path():
    for name in ("segoeuisemibold", "segoeui", "verdana", "arial"):
        path = pygame.font.match_font(name, bold=False)
        if path:
            return path
    return None


def _find_display_font_path():
    for name in ("segoeuiblack", "arialblack", "impact", "bahnschrift"):
        path = pygame.font.match_font(name, bold=True)
        if path:
            return path
    return _find_font_path()


def get_font(size, display=False, bold=False):
    key = (size, display, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    path = _find_display_font_path() if display else _find_font_path()
    if path:
        font = pygame.font.Font(path, size)
    else:
        font = pygame.font.SysFont("consolas", size, bold=bold or display)
    _FONT_CACHE[key] = font
    return font


# ---------------------------------------------------------------------------
# DRAW HELPERS
# ---------------------------------------------------------------------------

def draw_vertical_gradient(surface, rect, top_color, bottom_color, border_radius=0):
    x, y, w, h = rect
    if w <= 0 or h <= 0:
        return
    grad = pygame.Surface((1, max(2, h)), pygame.SRCALPHA)
    for row in range(grad.get_height()):
        t = row / max(1, grad.get_height() - 1)
        grad.set_at((0, row), (*lerp_color(top_color, bottom_color, t), 255))
    grad = pygame.transform.smoothscale(grad, (max(1, w), max(1, h)))

    if border_radius > 0:
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=border_radius)
        grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    surface.blit(grad, (x, y))


def draw_drop_shadow(surface, rect, border_radius=12, offset=(0, 4), blur_pad=10, alpha=90):
    x, y, w, h = rect
    shadow_surf = pygame.Surface((w + blur_pad * 2, h + blur_pad * 2), pygame.SRCALPHA)
    layers = 5
    for i in range(layers, 0, -1):
        grow = int(blur_pad * (i / layers))
        a = int(alpha * (1 - i / (layers + 1)) / layers) + 2
        r = pygame.Rect(blur_pad - grow, blur_pad - grow, w + grow * 2, h + grow * 2)
        pygame.draw.rect(shadow_surf, (0, 0, 0, a), r, border_radius=border_radius + grow // 2)
    surface.blit(shadow_surf, (x - blur_pad + offset[0], y - blur_pad + offset[1]))


def draw_glass_panel(surface, rect, border_color=None, fill_top=None, fill_bottom=None,
                      border_radius=16, border_width=2, glow=True):
    x, y, w, h = rect
    border_color = border_color or GLASS_BORDER
    fill_top = fill_top or BG_PANEL_LIGHT
    fill_bottom = fill_bottom or BG_PANEL

    draw_drop_shadow(surface, rect, border_radius=border_radius)

    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    grad = pygame.Surface((1, h), pygame.SRCALPHA)
    for row in range(h):
        t = row / max(1, h - 1)
        grad.set_at((0, row), (*lerp_color(fill_top, fill_bottom, t), GLASS_ALPHA))
    grad = pygame.transform.smoothscale(grad, (w, h))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=border_radius)
    grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    panel.blit(grad, (0, 0))

    highlight = pygame.Surface((w, max(2, h // 3)), pygame.SRCALPHA)
    pygame.draw.rect(highlight, (255, 255, 255, 18), highlight.get_rect(), border_radius=border_radius)
    panel.blit(highlight, (0, 0))

    surface.blit(panel, (x, y))

    if glow:
        glow_surf = pygame.Surface((w + 16, h + 16), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*border_color, 40), glow_surf.get_rect(), border_radius=border_radius + 6)
        surface.blit(glow_surf, (x - 8, y - 8), special_flags=pygame.BLEND_RGBA_ADD)

    pygame.draw.rect(surface, border_color, (x, y, w, h), width=border_width, border_radius=border_radius)


def draw_gradient_bar(surface, rect, fraction, color, border_radius=8, bg_color=(255, 255, 255, 18)):
    x, y, w, h = rect
    fraction = max(0.0, min(1.0, fraction))

    track = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(track, bg_color, track.get_rect(), border_radius=border_radius)
    surface.blit(track, (x, y))

    fill_w = int(w * fraction)
    if fill_w > 2:
        fill_rect = pygame.Rect(x, y, fill_w, h)
        light = shade(color, 1.35)
        dark = shade(color, 0.75)
        draw_vertical_gradient(surface, fill_rect, light, dark, border_radius=min(border_radius, fill_w // 2))

        edge_x = x + fill_w
        edge_surf = pygame.Surface((18, h + 12), pygame.SRCALPHA)
        pygame.draw.ellipse(edge_surf, (*color, 130), edge_surf.get_rect())
        surface.blit(edge_surf, (edge_x - 9, y - 6), special_flags=pygame.BLEND_RGBA_ADD)

    pygame.draw.rect(surface, (*shade(color, 0.8), 200), (x, y, w, h), width=1, border_radius=border_radius)


def draw_glow_text(surface, text, font, pos, color, glow_color=None, center=False, glow_radius=6):
    glow_color = glow_color or color
    text_surf = font.render(text, True, color)
    rect = text_surf.get_rect(center=pos) if center else text_surf.get_rect(topleft=pos)

    glow_surf = pygame.Surface((rect.width + glow_radius * 4, rect.height + glow_radius * 4), pygame.SRCALPHA)
    glow_text = font.render(text, True, glow_color)
    small = pygame.transform.smoothscale(
        glow_text, (max(1, glow_text.get_width() // 6), max(1, glow_text.get_height() // 6))
    )
    blurred = pygame.transform.smoothscale(small, glow_text.get_size())
    blurred.set_alpha(120)
    glow_surf.blit(blurred, (glow_radius * 2, glow_radius * 2), special_flags=pygame.BLEND_RGBA_ADD)
    surface.blit(glow_surf, (rect.x - glow_radius * 2, rect.y - glow_radius * 2))

    surface.blit(text_surf, rect)
    return rect


def pulse(t, speed=2.0, lo=0.7, hi=1.0):
    return lo + (hi - lo) * (0.5 + 0.5 * math.sin(t * speed))