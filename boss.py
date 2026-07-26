"""
boss.py
-------
Boss enemies: big, multi-phase set-piece fights that show up periodically
as the player levels up.

Design:
  - A boss has 3 PHASES based on remaining health (healthy / damaged /
    critical). Each phase fires a different, progressively nastier bullet
    pattern -- this is what makes a boss feel different from just "a
    regular enemy with more HP".
  - Bosses fly in from off-screen with a dramatic spin-and-grow entrance,
    hover at the top, and sway side to side while firing -- they don't
    chase the player like some regular enemies do.
  - The silhouette is a twin-blade starfighter: a narrow central spine
    plus two large sweptback wing-blades ending in sharp spikes, with
    glowing wingtip thrusters and a pulsing core -- built entirely out of
    pygame polygons so no image assets are required.
  - main.py is responsible for pausing normal enemy spawns and freezing
    level-ups while `boss is not None`, and for colliding boss bullets
    against the player and player bullets against the boss (this file
    just returns plain Bullet objects from update(), it doesn't know
    about the player's bullet list).
"""

import math
import random

import pygame

import settings
from bullet import Bullet


BOSS_TYPES = {
    "sentinel": {
        "label": "SENTINEL",
        "health": 90,
        "size": 170,
        "speed": 90,
        "color": (150, 80, 220),
        "core_color": (255, 60, 200),
        "score": 1400,
    },
    "dreadnought": {
        "label": "DREADNOUGHT",
        "health": 150,
        "size": 200,
        "speed": 70,
        "color": (90, 95, 110),
        "core_color": (255, 60, 60),
        "score": 2200,
    },
    "leviathan": {
        "label": "LEVIATHAN",
        "health": 220,
        "size": 230,
        "speed": 60,
        "color": (60, 150, 210),
        "core_color": (255, 210, 60),
        "score": 3200,
    },
}
BOSS_ORDER = ["sentinel", "dreadnought", "leviathan"]


def boss_for_level(level):
    """Cycles through the boss roster as levels climb. `loop` counts how
    many times we've been all the way through the roster, so the same
    boss coming back around is visibly tougher than last time."""
    index = (level - 1) % len(BOSS_ORDER)
    loop = (level - 1) // len(BOSS_ORDER)
    return BOSS_ORDER[index], loop


def _rotate_points(points, cx, cy, angle_deg):
    """Rotates a list of (x, y) points around (cx, cy) by angle_deg."""
    if not angle_deg:
        return points
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    out = []
    for px, py in points:
        dx, dy = px - cx, py - cy
        out.append((cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a))
    return out


class Boss:
    def __init__(self, level):
        boss_type, loop = boss_for_level(level)
        cfg = BOSS_TYPES[boss_type]

        self.boss_type = boss_type
        self.label = cfg["label"]

        scale = 1 + 0.35 * loop
        self.max_health = int(cfg["health"] * scale)
        self.health = self.max_health
        self.size = cfg["size"]
        self.speed = cfg["speed"] * (1 + 0.1 * loop)
        self.color = cfg["color"]
        self.core_color = cfg["core_color"]
        self.score_value = int(cfg["score"] * scale)

        self.x = settings.SCREEN_WIDTH / 2
        self.y = -self.size
        self.entry_target_y = 150
        self.entered = False

        # --- Entrance animation (spin + grow while flying in) ---
        self.entry_elapsed = 0.0
        self.entry_duration = 1.3
        self.entry_spin = random.choice([-1, 1]) * 640  # degrees to unwind

        self.time_alive = 0.0
        self.alive = True
        self.hit_flash_timer = 0.0

        # --- Phase-change radial flash ---
        self._last_phase = 1
        self.phase_flash_timer = 0.0
        self.phase_changed_this_frame = False

        self.fire_timer = random.uniform(0.8, 1.4)
        self.move_direction = 1

    @property
    def phase(self):
        """1 = healthy (>66%), 2 = damaged (33-66%), 3 = critical (<=33%)."""
        ratio = self.health / self.max_health
        if ratio > 0.66:
            return 1
        elif ratio > 0.33:
            return 2
        return 3

    def take_damage(self, amount):
        self.health -= amount
        self.hit_flash_timer = 0.08
        if self.health <= 0:
            self.health = 0
            self.alive = False

    def get_rect(self):
        return pygame.Rect(
            int(self.x - self.size / 2), int(self.y - self.size / 2),
            self.size, self.size
        )

    def update(self, dt, player_x, player_y):
        """Returns a list of newly-fired Bullet objects (usually empty)."""
        self.time_alive += dt
        self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)
        self.phase_changed_this_frame = False

        if not self.entered:
            self.entry_elapsed += dt
            self.y += 90 * dt
            if self.y >= self.entry_target_y:
                self.y = self.entry_target_y
                self.entered = True
            return []

        current_phase = self.phase
        if current_phase != self._last_phase:
            self._last_phase = current_phase
            self.phase_flash_timer = 0.4
            self.phase_changed_this_frame = True
        self.phase_flash_timer = max(0.0, self.phase_flash_timer - dt)

        sway_speed = self.speed * (1 + 0.3 * (current_phase - 1))
        self.x += self.move_direction * sway_speed * dt
        margin = self.size * 0.65
        if self.x < margin:
            self.x = margin
            self.move_direction = 1
        elif self.x > settings.SCREEN_WIDTH - margin:
            self.x = settings.SCREEN_WIDTH - margin
            self.move_direction = -1

        return self._update_firing(dt, player_x, player_y)

    def _update_firing(self, dt, player_x, player_y):
        self.fire_timer -= dt
        if self.fire_timer > 0:
            return []

        phase = self.phase
        ratio = self.health / self.max_health
        enraged = phase == 3 and ratio <= 0.15

        if enraged:
            fire_rate = 0.22
        else:
            fire_rate = {1: 0.95, 2: 0.55, 3: 0.34}[phase]
        self.fire_timer = fire_rate
        return self._fire_pattern(phase, player_x, player_y, enraged)

    def _fire_pattern(self, phase, player_x, player_y, enraged=False):
        bullets = []
        nose_x, nose_y = self.x, self.y + self.size * 0.42

        if phase == 1:
            # Phase 1: fast shot aimed straight at the player.
            dx, dy = player_x - nose_x, player_y - nose_y
            dist = math.hypot(dx, dy) or 1
            speed = 420
            bullets.append(Bullet(
                nose_x, nose_y, vx=dx / dist * speed, vy=dy / dist * speed,
                width=13, height=13, color=self.core_color, damage=13
            ))
        elif phase == 2:
            # Phase 2: wide 5-way spread, faster still.
            for angle_deg in (-32, -16, 0, 16, 32):
                angle_rad = math.radians(angle_deg)
                speed = 460
                vx = speed * math.sin(angle_rad)
                vy = speed * math.cos(angle_rad)
                bullets.append(Bullet(
                    nose_x, nose_y, vx=vx, vy=vy,
                    width=11, height=11, color=self.core_color, damage=9
                ))
        else:
            # Phase 3 (critical): full-ring burst -- and once health drops
            # below 15%, an all-out enraged barrage: denser ring, faster
            # bullets, fired almost continuously.
            count = 18 if enraged else 13
            speed = 400 if enraged else 340
            damage = 7 if enraged else 6
            for i in range(count):
                angle_rad = (i / count) * math.tau
                vx = speed * math.sin(angle_rad)
                vy = speed * math.cos(angle_rad)
                bullets.append(Bullet(
                    nose_x, nose_y, vx=vx, vy=vy,
                    width=9, height=9, color=self.core_color, damage=damage
                ))
        return bullets

    def draw(self, surface):
        cx, cy = self.x, self.y
        s = self.size

        if not self.entered:
            t = min(1.0, self.entry_elapsed / self.entry_duration)
            ease = 1 - (1 - t) ** 3  # ease-out cubic
            scale = 0.2 + 0.8 * ease
            rotation = (1 - ease) * self.entry_spin
        else:
            scale = 1.0
            rotation = 0.0

        hw = (s * scale) / 2
        if hw < 2:
            return

        flash = self.hit_flash_timer > 0
        body_color = settings.WHITE if flash else self.color
        accent_color = self.core_color

        # --- Ambient outer glow, pulsing gently ---
        pulse = 0.7 + 0.3 * abs(math.sin(self.time_alive * 2))
        glow_r = int(hw * 1.7 * pulse)
        glow_pad = glow_r + 4
        glow_surf = pygame.Surface((glow_pad * 2, glow_pad * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 40), (glow_pad, glow_pad), glow_r)
        surface.blit(glow_surf, (cx - glow_pad, cy - glow_pad))

        # --- Phase-change shockwave ring ---
        if self.phase_flash_timer > 0:
            ring_progress = 1 - (self.phase_flash_timer / 0.4)
            ring_r = int(hw * (1.1 + ring_progress * 1.8))
            ring_alpha = int(210 * (1 - ring_progress))
            ring_pad = ring_r + 6
            ring_surf = pygame.Surface((ring_pad * 2, ring_pad * 2), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (*accent_color, ring_alpha),
                                (ring_pad, ring_pad), ring_r, width=5)
            surface.blit(ring_surf, (cx - ring_pad, cy - ring_pad))

        def rot(pts):
            return _rotate_points(pts, cx, cy, rotation)

        # --- Central fuselage (nose points toward the player, downward) ---
        body_pts = rot([
            (cx, cy - hw * 1.1),              # tail spike
            (cx - hw * 0.3, cy - hw * 0.25),
            (cx - hw * 0.22, cy + hw * 0.55),
            (cx, cy + hw * 1.35),             # nose tip
            (cx + hw * 0.22, cy + hw * 0.55),
            (cx + hw * 0.3, cy - hw * 0.25),
        ])

        def wing_pts(side):
            return rot([
                (cx + side * hw * 0.18, cy - hw * 0.25),
                (cx + side * hw * 0.95, cy - hw * 1.05),   # sharp spike tip
                (cx + side * hw * 0.55, cy - hw * 0.45),
                (cx + side * hw * 1.25, cy - hw * 0.05),
                (cx + side * hw * 1.45, cy + hw * 0.55),   # wingtip
                (cx + side * hw * 0.6, cy + hw * 0.35),
                (cx + side * hw * 0.25, cy + hw * 0.1),
            ])

        def wing_accent_pts(side):
            return rot([
                (cx + side * hw * 0.4, cy - hw * 0.35),
                (cx + side * hw * 0.85, cy - hw * 0.9),
                (cx + side * hw * 0.65, cy - hw * 0.42),
                (cx + side * hw * 1.05, cy + hw * 0.05),
                (cx + side * hw * 0.85, cy + hw * 0.4),
                (cx + side * hw * 0.5, cy + hw * 0.2),
            ])

        left_wing = wing_pts(-1)
        right_wing = wing_pts(1)

        pygame.draw.polygon(surface, body_color, left_wing)
        pygame.draw.polygon(surface, body_color, right_wing)
        pygame.draw.polygon(surface, accent_color, wing_accent_pts(-1))
        pygame.draw.polygon(surface, accent_color, wing_accent_pts(1))
        pygame.draw.polygon(surface, settings.WHITE, left_wing, width=2)
        pygame.draw.polygon(surface, settings.WHITE, right_wing, width=2)

        pygame.draw.polygon(surface, body_color, body_pts)
        pygame.draw.polygon(surface, settings.WHITE, body_pts, width=2)

        # --- Glowing wingtip thrusters ---
        for side, wing in ((-1, left_wing), (1, right_wing)):
            tip_x, tip_y = wing[4]
            flicker = 0.6 + 0.4 * abs(math.sin(self.time_alive * 14 + side))
            flame_r = max(2, int(hw * 0.2 * flicker)) + 2
            pad = flame_r * 2
            flame_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
            pygame.draw.circle(flame_surf, (*settings.GOLD, 190), (pad, pad), flame_r)
            pygame.draw.circle(flame_surf, (*settings.WHITE, 220), (pad, pad), max(1, int(flame_r * 0.5)))
            surface.blit(flame_surf, (tip_x - pad, tip_y - pad))

        # --- Pulsing core (cockpit-like glow) ---
        pulse_speed = 3 + self.phase * 2
        core_pulse = 0.7 + 0.3 * abs(math.sin(self.time_alive * pulse_speed))
        core_r = max(3, int(hw * 0.22 * core_pulse))
        core_x, core_y = rot([(cx, cy - hw * 0.05)])[0]
        pygame.draw.circle(surface, accent_color, (int(core_x), int(core_y)), core_r)
        pygame.draw.circle(surface, settings.WHITE, (int(core_x), int(core_y)), core_r, width=2)

    def draw_health_bar(self, surface, font):
        bar_w = 560
        bar_h = 24
        bar_rect = pygame.Rect(0, 0, bar_w, bar_h)
        bar_rect.midtop = (settings.SCREEN_WIDTH // 2, 12)

        pygame.draw.rect(surface, (30, 30, 40), bar_rect, border_radius=6)
        ratio = self.health / self.max_health
        fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, int(bar_w * ratio), bar_h)
        if ratio > 0.5:
            fill_color = settings.NEON_GREEN
        elif ratio > 0.25:
            fill_color = settings.GOLD
        else:
            fill_color = settings.DANGER_RED
        pygame.draw.rect(surface, fill_color, fill_rect, border_radius=6)
        pygame.draw.rect(surface, settings.WHITE, bar_rect, width=2, border_radius=6)

        label_surf = font.render(f"{self.label}  [PHASE {self.phase}]", True, settings.WHITE)
        label_rect = label_surf.get_rect(midbottom=(bar_rect.centerx, bar_rect.y - 4))
        surface.blit(label_surf, label_rect)