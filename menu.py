"""
menu.py
-------
Main menu UI.

Contains:
  Button   - a single clickable menu item with a smooth hover animation
  MainMenu - owns all buttons, the title/logo, and reports back which
             action the player picked (so main.py can react to it)

Design choice: MainMenu doesn't know anything about pygame events directly
handling "what to do" -- it just tells main.py "the player clicked PLAY"
and main.py decides what that means. This keeps menu.py reusable and
main.py in charge of overall game flow.
"""

import math
import random

import pygame

import settings


def _ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _blurred_text(text, font, color, alpha=255, passes=2):
    """A cheap but genuinely smooth glow: render the text, shrink it down
    hard and scale it back up (repeatedly) so smoothscale's interpolation
    does the blurring for us. Looks like a soft bloom instead of the
    'stacked offset copies' trick, which reads as ghosting/double-vision
    rather than a glow."""
    base = font.render(text, True, color)
    w, h = base.get_size()
    if w < 4 or h < 4:
        return base
    blurred = base
    for _ in range(passes):
        small = pygame.transform.smoothscale(blurred, (max(1, w // 8), max(1, h // 8)))
        blurred = pygame.transform.smoothscale(small, (w, h))
    blurred.set_alpha(alpha)
    return blurred


def _load_display_font(size):
    """Tries to find a bolder, more distinctive display font on the
    system for the title (arcade titles look weak in a plain monospace
    terminal font); falls back to Consolas bold if none of these exist."""
    for name in ("arialblack", "impact", "bahnschrift", "segoeuiblack", "verdana"):
        path = pygame.font.match_font(name, bold=True)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("consolas", size, bold=True)


def _load_body_font(size, bold=False):
    path = pygame.font.match_font("segoeui", bold=bold) or pygame.font.match_font("verdana", bold=bold)
    if path:
        return pygame.font.Font(path, size)
    return pygame.font.SysFont("consolas", size, bold=bold)


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

    def draw(self, surface, x_offset=0):
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
        draw_rect.center = (self.rect.centerx + x_offset, self.rect.centery)

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

        # Small chevron tick that slides in on hover -- a subtle "selected"
        # cue beyond just the color/scale change.
        if self.hover_amount > 0.01:
            tick_x = draw_rect.x - 14 - (1 - self.hover_amount) * 10
            tick_pts = [
                (tick_x, draw_rect.centery - 8),
                (tick_x + 10, draw_rect.centery),
                (tick_x, draw_rect.centery + 8),
            ]
            pygame.draw.polygon(surface, hover_color, tick_pts)

        pygame.draw.rect(surface, (15, 15, 35), draw_rect, border_radius=12)
        pygame.draw.rect(surface, color, draw_rect, width=2, border_radius=12)

        highlight_rect = draw_rect.inflate(-14, -14)
        highlight_rect.height = max(2, highlight_rect.height // 3)
        highlight_surf = pygame.Surface(highlight_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(highlight_surf, (255, 255, 255, 14), highlight_surf.get_rect(), border_radius=8)
        surface.blit(highlight_surf, highlight_rect.topleft)

        text_surf = self.font.render(self.label, True, settings.WHITE)
        text_rect = text_surf.get_rect(center=draw_rect.center)
        surface.blit(text_surf, text_rect)


def _draw_corner_brackets(surface, t):
    """Thin sci-fi HUD corner brackets framing the whole menu."""
    margin = 26
    length = 46
    pulse = 0.6 + 0.4 * abs(math.sin(t * 1.4))
    color = tuple(int(c * pulse) for c in settings.NEON_BLUE)
    w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT

    corners = [
        ((margin, margin), (1, 1)),
        ((w - margin, margin), (-1, 1)),
        ((margin, h - margin), (1, -1)),
        ((w - margin, h - margin), (-1, -1)),
    ]
    for (x, y), (dx, dy) in corners:
        pygame.draw.line(surface, color, (x, y), (x + dx * length, y), width=3)
        pygame.draw.line(surface, color, (x, y), (x, y + dy * length), width=3)
        pygame.draw.circle(surface, color, (x, y), 3)


def _draw_background_motifs(surface, t):
    """A couple of large, extremely faint slowly-rotating hexagon
    outlines behind everything -- reads as subtle texture rather than
    a competing decoration."""
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    specs = [
        (150, 140, 100, 3), (1130, 140, 130, -2.5),
        (settings.SCREEN_WIDTH // 2, 760, 260, 1.5),
    ]
    for x, y, r, speed in specs:
        angle_off = t * speed
        pts = [
            (x + math.cos(math.radians(60 * i + angle_off)) * r,
             y + math.sin(math.radians(60 * i + angle_off)) * r)
            for i in range(6)
        ]
        pygame.draw.polygon(layer, (*settings.NEON_BLUE, 10), pts, width=2)
    surface.blit(layer, (0, 0))


def _draw_wreath(surface, cx, cy, r, color):
    """A small laurel-style flourish beneath the badge -- the kind of
    detail that pushes a logo from 'icon' to 'crest'."""
    for side in (-1, 1):
        for i, a_deg in enumerate(range(22, 88, 13)):
            a = math.radians(a_deg)
            lx = cx + side * math.cos(a) * r
            ly = cy + math.sin(a) * r
            leaf_w = max(4, 13 - i * 1.6)
            leaf_h = max(3, 6 - i * 0.6)
            leaf_rect = pygame.Rect(0, 0, leaf_w, leaf_h)
            leaf_rect.center = (lx, ly)
            pygame.draw.ellipse(surface, color, leaf_rect)


def _draw_logo(surface, cx, cy, t, radius=56):
    """The game's emblem: a crest-style badge -- a slow rotating tick
    ring, a beveled double ring, a shield-shaped plate holding a
    twin-wing ship silhouette (echoing the player/boss ship design
    language), and a laurel flourish underneath for a more official,
    'professional' badge feel. Kept deliberately restrained -- fewer
    moving parts reads as more polished, not less."""

    # --- Ambient glow ---
    glow_pad = radius + 30
    glow_surf = pygame.Surface((glow_pad * 2, glow_pad * 2), pygame.SRCALPHA)
    pulse = 0.7 + 0.3 * abs(math.sin(t * 1.5))
    pygame.draw.circle(glow_surf, (*settings.NEON_BLUE, int(45 * pulse)), (glow_pad, glow_pad), int(radius * 1.35))
    surface.blit(glow_surf, (cx - glow_pad, cy - glow_pad))

    # --- Outer tick ring (slow rotation, uniform weight) ---
    tick_count = 20
    for i in range(tick_count):
        angle = math.radians((360 / tick_count) * i + t * 10)
        long_tick = i % 5 == 0
        r_in = radius - (10 if long_tick else 5)
        x1 = cx + math.cos(angle) * radius
        y1 = cy + math.sin(angle) * radius
        x2 = cx + math.cos(angle) * r_in
        y2 = cy + math.sin(angle) * r_in
        pygame.draw.line(surface, settings.NEON_BLUE, (x1, y1), (x2, y2), width=2 if long_tick else 1)

    # --- Beveled double ring (the "metallic" badge edge) ---
    pygame.draw.circle(surface, (70, 76, 100), (int(cx), int(cy)), int(radius * 0.86), width=4)
    pygame.draw.circle(surface, (150, 160, 190), (int(cx), int(cy)), int(radius * 0.86), width=1)

    # --- Laurel flourish beneath the badge ---
    _draw_wreath(surface, cx, cy + radius * 0.05, radius * 0.78, settings.GOLD)

    # --- Shield-shaped inner plate ---
    r = radius * 0.72
    shield_pts = [
        (cx - r * 0.5, cy - r * 0.95),
        (cx + r * 0.5, cy - r * 0.95),
        (cx + r, cy - r * 0.45),
        (cx + r, cy + r * 0.15),
        (cx + r * 0.55, cy + r * 0.7),
        (cx, cy + r * 1.05),
        (cx - r * 0.55, cy + r * 0.7),
        (cx - r, cy + r * 0.15),
        (cx - r, cy - r * 0.45),
    ]
    pygame.draw.polygon(surface, (12, 14, 30), shield_pts)
    pygame.draw.polygon(surface, settings.NEON_PURPLE, shield_pts, width=2)

    # --- Twin-wing ship silhouette inside the shield ---
    hw, hh = r * 0.5, r * 0.55
    body = [
        (cx, cy - hh * 0.85),
        (cx - hw * 0.3, cy + hh * 0.5),
        (cx, cy + hh * 0.2),
        (cx + hw * 0.3, cy + hh * 0.5),
    ]
    wing_l = [(cx - hw * 0.22, cy - hh * 0.1), (cx - hw * 0.95, cy + hh * 0.3), (cx - hw * 0.18, cy + hh * 0.5)]
    wing_r = [(cx + hw * 0.22, cy - hh * 0.1), (cx + hw * 0.95, cy + hh * 0.3), (cx + hw * 0.18, cy + hh * 0.5)]
    pygame.draw.polygon(surface, (200, 140, 40), wing_l)
    pygame.draw.polygon(surface, (200, 140, 40), wing_r)
    pygame.draw.polygon(surface, settings.GOLD, body)
    pygame.draw.polygon(surface, settings.WHITE, body, width=1)

    # Pulsing engine-core glow beneath the ship
    core_pulse = 0.6 + 0.4 * abs(math.sin(t * 5))
    core_r = int(3 + 2 * core_pulse)
    pygame.draw.circle(surface, settings.NEON_GREEN, (int(cx), int(cy + hh * 0.6)), core_r)


class MainMenu:
    """Owns the title/logo + all buttons. Call update(), draw(), and
    handle_click() from main.py's game loop."""

    def __init__(self):
        self.title_font = _load_display_font(60)
        self.subtitle_font = _load_body_font(16)
        self.tag_font = _load_body_font(13)
        self.time_elapsed = 0.0

        self.title_text = settings.GAME_TITLE.upper()

        center_x = settings.SCREEN_WIDTH // 2
        start_y = 362
        gap = 58

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

        # --- Ambient floating dust, purely decorative ---
        random.seed(42)
        self.particles = [
            {
                "x": random.uniform(0, settings.SCREEN_WIDTH),
                "y": random.uniform(0, settings.SCREEN_HEIGHT),
                "vy": random.uniform(-10, -3),
                "phase": random.uniform(0, math.tau),
                "size": random.uniform(1.0, 2.2),
            }
            for _ in range(40)
        ]
        random.seed()

    def update(self, dt, mouse_pos):
        self.time_elapsed += dt
        for button in self.buttons:
            button.update(dt, mouse_pos)
        for p in self.particles:
            p["y"] += p["vy"] * dt
            if p["y"] < -10:
                p["y"] = settings.SCREEN_HEIGHT + 10
                p["x"] = random.uniform(0, settings.SCREEN_WIDTH)

    def _draw_title(self, surface, title_y):
        """Renders the title letter-by-letter, each one fading + sliding
        up into place with a staggered delay -- a one-time "materializing"
        entrance the first time the menu appears."""
        cx = settings.SCREEN_WIDTH // 2
        widths = [self.title_font.size(ch)[0] for ch in self.title_text]
        total_w = sum(widths)
        start_x = cx - total_w // 2

        # Static ambient glow behind the whole title (always fully visible,
        # so the letters look like they're materializing out of it). Uses
        # a real shrink/scale blur instead of stacked offset copies.
        glow_text = _blurred_text(self.title_text, self.title_font, settings.NEON_BLUE, alpha=140)
        glow_rect = glow_text.get_rect(center=(cx, title_y))
        surface.blit(glow_text, glow_rect)

        x = start_x
        for i, ch in enumerate(self.title_text):
            ch_w = widths[i]
            reveal_start = i * 0.045
            eased = _ease_out_cubic((self.time_elapsed - reveal_start) / 0.35)
            alpha = int(255 * eased)
            y_off = (1 - eased) * 18

            if alpha > 0 and ch != " ":
                shadow_surf = self.title_font.render(ch, True, (10, 10, 25))
                shadow_surf.set_alpha(alpha)
                surface.blit(shadow_surf, (x + 3, title_y - shadow_surf.get_height() // 2 + 3 + y_off))

                ch_surf = self.title_font.render(ch, True, settings.NEON_BLUE)
                ch_surf.set_alpha(alpha)
                surface.blit(ch_surf, (x, title_y - ch_surf.get_height() // 2 + y_off))
            x += ch_w

        return pygame.Rect(start_x, title_y - self.title_font.get_height() // 2, total_w, self.title_font.get_height())

    def draw(self, surface):
        _draw_background_motifs(surface, self.time_elapsed)
        _draw_corner_brackets(surface, self.time_elapsed)

        # Ambient dust, twinkling gently
        for p in self.particles:
            twinkle = 0.3 + 0.5 * abs(math.sin(self.time_elapsed * 2 + p["phase"]))
            alpha = int(140 * twinkle)
            pygame.draw.circle(surface, (*settings.WHITE, alpha), (int(p["x"]), int(p["y"])), p["size"])

        # Title + logo gently bob together as one unit
        bob_offset = math.sin(self.time_elapsed * 1.5) * 6
        logo_y = 98 + bob_offset
        title_y = 200 + bob_offset

        _draw_logo(surface, settings.SCREEN_WIDTH // 2, logo_y, self.time_elapsed)
        title_rect = self._draw_title(surface, title_y)

        # Flanking chevrons framing the title, like a sci-fi logotype lockup
        chevron_alpha = int(255 * _ease_out_cubic((self.time_elapsed - 0.9) / 0.4))
        if chevron_alpha > 0:
            chevron_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            gap_x = title_rect.width // 2 + 30
            for side in (-1, 1):
                base_x = title_rect.centerx + side * gap_x
                pts = [
                    (base_x, title_rect.centery - 14),
                    (base_x + side * 16, title_rect.centery),
                    (base_x, title_rect.centery + 14),
                ]
                pygame.draw.polygon(chevron_surf, (*settings.NEON_PURPLE, chevron_alpha), pts, width=3)
            surface.blit(chevron_surf, (0, 0))

        # Subtitle fades in after the title finishes revealing
        subtitle_alpha = int(255 * _ease_out_cubic((self.time_elapsed - 1.1) / 0.5))
        subtitle_y = title_y + 46
        if subtitle_alpha > 0:
            subtitle_surf = self.subtitle_font.render(
                "GESTURE CONTROLLED SPACE SHOOTER", True, settings.NEON_PURPLE
            )
            subtitle_surf.set_alpha(subtitle_alpha)
            subtitle_rect = subtitle_surf.get_rect(center=(settings.SCREEN_WIDTH // 2, subtitle_y))
            surface.blit(subtitle_surf, subtitle_rect)

            bar_pulse = 0.5 + 0.5 * abs(math.sin(self.time_elapsed * 2.2))
            bar_width = int(220 * (0.85 + 0.15 * bar_pulse))
            bar_color = tuple(int(c * (0.5 + 0.5 * bar_pulse)) for c in settings.NEON_BLUE)
            bar_rect = pygame.Rect(0, 0, bar_width, 2)
            bar_rect.center = (settings.SCREEN_WIDTH // 2, subtitle_y + 20)
            bar_surf = pygame.Surface((bar_rect.width, bar_rect.height), pygame.SRCALPHA)
            bar_surf.fill((*bar_color, subtitle_alpha))
            surface.blit(bar_surf, bar_rect.topleft)

        # Buttons slide in from the right, staggered by index
        for i, button in enumerate(self.buttons):
            reveal_start = 0.55 + i * 0.09
            eased = _ease_out_cubic((self.time_elapsed - reveal_start) / 0.45)
            x_offset = int((1 - eased) * 240)
            button.draw(surface, x_offset=x_offset)

        version_surf = self.tag_font.render("v1.0", True, (110, 120, 150))
        surface.blit(version_surf, (settings.SCREEN_WIDTH - version_surf.get_width() - 20,
                                     settings.SCREEN_HEIGHT - 28))

    def handle_click(self, mouse_pos):
        """Returns the action string of the clicked button, or None."""
        for button in self.buttons:
            if button.rect.collidepoint(mouse_pos):
                return button.action
        return None