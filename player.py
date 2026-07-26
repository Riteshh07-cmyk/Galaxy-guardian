"""
player.py
---------
STEP 6: The player's spaceship.

Handles:
  - Smoothed movement toward a target position (your index fingertip).
  - Keeping the ship on-screen (clamping to bounds).
  - Drawing the ship with a simple animated engine flame.

WHY SMOOTHING MATTERS:
Raw hand-tracking data jitters a little frame to frame, even when your
hand is perfectly still. If the ship snapped directly to the fingertip
position every frame, it would visibly shake. Instead, we move the ship
a FRACTION of the way toward the target each frame (exponential
smoothing) -- close enough to feel responsive, smooth enough to hide
jitter.
"""

import math
import random
import colorsys
from collections import deque

import pygame

import settings
import weapons
import ships


VICTORY_EFFECT_TYPES = [
    "golden_aura", "lightning_arcs", "rainbow_trail",
    "shockwave_pulse", "star_rays", "phoenix_flames", "orbiting_rings",
]


class Player:
    def __init__(self, ship_type="guardian"):
        ship_cfg = ships.SHIP_TYPES.get(ship_type, ships.SHIP_TYPES["guardian"])
        self.ship_type = ship_type
        self.ship_label = ship_cfg["label"]
        self.ship_color = ship_cfg["color"]
        self.wing_color = ship_cfg["wing_color"]
        self.fire_rate_mult = ship_cfg["fire_rate_mult"]
        self.damage_mult = ship_cfg["damage_mult"]

        self.x = settings.SCREEN_WIDTH / 2
        self.y = settings.SCREEN_HEIGHT - 120

        self.width = 46
        self.height = 56

        self.smoothing_rate = 12.0 * ship_cfg["speed_mult"]

        self.engine_phase = 0.0

        self.max_health = int(settings.PLAYER_START_HEALTH * ship_cfg["health_mult"])
        self.health = self.max_health
        self.invincible_timer = 0.0
        self.game_over = False

        # --- Shooting (Step 7-8) ---
        self.weapon_name = weapons.WEAPON_ORDER[0]
        self.shoot_cooldown = weapons.get_cooldown(self.weapon_name) / self.fire_rate_mult
        self.shot_timer = 0.0          # counts down to 0; can shoot when <= 0
        self.muzzle_flash_timer = 0.0  # counts down; muzzle flash drawn while > 0

        # --- Shield (fist gesture) ---
        self.shield_duration = settings.SHIELD_DURATION_SECONDS
        self.shield_cooldown = settings.SHIELD_COOLDOWN_SECONDS
        self.shield_timer = 0.0            # > 0 while shield is actively up
        self.shield_cooldown_timer = 0.0   # > 0 while shield is unavailable

        # --- Boost (open palm gesture, held) ---
        # STEP 10: Extreme speed now runs off a real energy meter instead of
        # being free forever -- hold the boost, it drains; let go, it
        # slowly recharges. Drain it all the way and it "overheats" and
        # locks out until it recovers a bit, like a stamina bar.
        self.boosting = False
        self.boost_multiplier = 3.6
        self.boost_energy_max = 100.0
        self.boost_energy = self.boost_energy_max
        self.boost_drain_per_sec = 48.0
        self.boost_regen_per_sec = 20.0
        self.boost_lockout_recovery_frac = 0.3  # must refill to 30% to boost again
        self.boost_locked_out = False

        # --- Damage feedback (Step 10) ---
        self.damage_flash_timer = 0.0
        self.damage_flash_duration = 0.4
        self.hit_shake_timer = 0.0
        self.hit_shake_duration = 0.25

        # --- Post-boss victory effect ---
        # A different celebratory effect gets picked at random each time a
        # boss goes down (see trigger_victory_effect()) so it doesn't feel
        # like the same fireworks every single fight.
        self.victory_effect = None
        self.position_history = deque(maxlen=30)  # used by the rainbow trail effect

    def trigger_victory_effect(self, duration=2.6):
        """Call this once, right when a boss is defeated. Picks a random
        celebratory effect and starts it running around the ship."""
        effect_type = random.choice(VICTORY_EFFECT_TYPES)
        data = {}

        if effect_type == "lightning_arcs":
            data["bolts"] = [
                {
                    "angle": random.uniform(0, math.tau),
                    "length": random.uniform(46, 86),
                    "flicker_seed": random.uniform(0, 10),
                    "jitter": [random.uniform(-1, 1) for _ in range(4)],
                }
                for _ in range(6)
            ]
        elif effect_type == "star_rays":
            data["ray_count"] = random.choice([8, 10, 12])
            data["spin_dir"] = random.choice([-1, 1])
        elif effect_type == "orbiting_rings":
            palette = [settings.NEON_BLUE, settings.NEON_PURPLE, settings.GOLD]
            data["rings"] = [
                {
                    "radius": 36 + i * 18,
                    "speed": random.uniform(1.6, 3.2) * random.choice([-1, 1]),
                    "color": palette[i % len(palette)],
                    "tilt": 0.4 + i * 0.12,
                }
                for i in range(3)
            ]
        elif effect_type == "phoenix_flames":
            data["particles"] = []
        elif effect_type == "rainbow_trail":
            self.position_history.clear()

        self.victory_effect = {"type": effect_type, "timer": 0.0, "duration": duration, "data": data}

    def update(self, dt, target_x, target_y, keyboard_dx=0.0, keyboard_dy=0.0, boost_requested=False):
        """target_x/target_y: where the player's index fingertip currently
        maps to on screen, or None if no hand is currently detected.
        keyboard_dx/keyboard_dy: direct movement speed from arrow-key/WASD
        backup controls -- when either is non-zero, keyboard takes priority
        over finger tracking for this frame.
        boost_requested: True while the boost gesture/key is being held --
        actual boosting only happens if the energy meter allows it (see
        below), so this is a request, not a guarantee."""

        # A fully-drained meter "overheats" and locks out until it climbs
        # back up past the recovery threshold -- prevents holding boost
        # permanently and forces a real cooldown, like Temple Run's meter.
        if self.boost_locked_out and self.boost_energy >= self.boost_energy_max * self.boost_lockout_recovery_frac:
            self.boost_locked_out = False

        self.boosting = bool(boost_requested) and not self.boost_locked_out and self.boost_energy > 0.0
        speed_mult = self.boost_multiplier if self.boosting else 1.0

        if self.boosting:
            self.boost_energy = max(0.0, self.boost_energy - self.boost_drain_per_sec * dt)
            if self.boost_energy <= 0.0:
                self.boosting = False
                self.boost_locked_out = True
        else:
            self.boost_energy = min(self.boost_energy_max, self.boost_energy + self.boost_regen_per_sec * dt)

        if keyboard_dx != 0.0 or keyboard_dy != 0.0:
            self.x += keyboard_dx * speed_mult * dt
            self.y += keyboard_dy * speed_mult * dt
        elif target_x is not None and target_y is not None:
            # Framerate-independent exponential smoothing: no matter the
            # FPS, the ship converges to the target at the same real-world
            # speed. (At low FPS it would look choppier, but never "faster".)
            alpha = 1 - math.exp(-self.smoothing_rate * speed_mult * dt)
            self.x += (target_x - self.x) * alpha
            self.y += (target_y - self.y) * alpha

        # Keep the ship fully on screen
        half_w, half_h = self.width / 2, self.height / 2
        self.x = max(half_w, min(settings.SCREEN_WIDTH - half_w, self.x))
        self.y = max(half_h, min(settings.SCREEN_HEIGHT - half_h, self.y))

        self.engine_phase += dt * 18

        # Tick down shooting timers regardless of whether we fired this frame
        self.shot_timer = max(0.0, self.shot_timer - dt)
        self.muzzle_flash_timer = max(0.0, self.muzzle_flash_timer - dt)
        self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self.shield_timer = max(0.0, self.shield_timer - dt)
        self.shield_cooldown_timer = max(0.0, self.shield_cooldown_timer - dt)
        self.damage_flash_timer = max(0.0, self.damage_flash_timer - dt)
        self.hit_shake_timer = max(0.0, self.hit_shake_timer - dt)

        self._update_victory_effect(dt)

    def _update_victory_effect(self, dt):
        if self.victory_effect is None:
            return

        self.victory_effect["timer"] += dt
        kind = self.victory_effect["type"]
        data = self.victory_effect["data"]

        if kind == "rainbow_trail":
            self.position_history.append((self.x, self.y))
        elif kind == "phoenix_flames":
            for _ in range(3):
                angle = random.uniform(0, math.tau)
                speed = random.uniform(20, 70)
                data["particles"].append({
                    "x": self.x + random.uniform(-6, 6),
                    "y": self.y + random.uniform(-4, 4),
                    "vx": math.cos(angle) * speed * 0.4,
                    "vy": math.sin(angle) * speed - 40,
                    "life": random.uniform(0.35, 0.7),
                    "age": 0.0,
                    "size": random.uniform(3, 7),
                })
            for p in data["particles"]:
                p["age"] += dt
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
            data["particles"] = [p for p in data["particles"] if p["age"] < p["life"]]

        if self.victory_effect["timer"] >= self.victory_effect["duration"]:
            self.victory_effect = None

    def can_shoot(self):
        return self.shot_timer <= 0.0

    def can_activate_shield(self):
        return self.shield_timer <= 0.0 and self.shield_cooldown_timer <= 0.0

    def activate_shield(self):
        self.shield_timer = self.shield_duration
        self.shield_cooldown_timer = self.shield_duration + self.shield_cooldown

    @property
    def is_shielded(self):
        return self.shield_timer > 0.0

    @property
    def health_fraction(self):
        return self.health / self.max_health if self.max_health else 0.0

    @property
    def boost_fraction(self):
        return self.boost_energy / self.boost_energy_max if self.boost_energy_max else 0.0

    def get_rect(self):
        return pygame.Rect(
            int(self.x - self.width / 2), int(self.y - self.height / 2),
            self.width, self.height
        )

    def take_damage(self, amount):
        if self.invincible_timer > 0 or self.is_shielded:
            return
        self.health -= amount
        self.damage_flash_timer = self.damage_flash_duration
        self.hit_shake_timer = self.hit_shake_duration
        if self.health <= 0:
            self.health = 0
            self.game_over = True
        else:
            self.invincible_timer = 1.0

    def set_weapon(self, weapon_name):
        if weapon_name in weapons.WEAPON_TYPES:
            self.weapon_name = weapon_name
            self.shoot_cooldown = weapons.get_cooldown(weapon_name) / self.fire_rate_mult

    def cycle_weapon(self, direction=1):
        """direction=1 -> next weapon, direction=-1 -> previous weapon."""
        current_index = weapons.WEAPON_ORDER.index(self.weapon_name)
        new_index = (current_index + direction) % len(weapons.WEAPON_ORDER)
        self.set_weapon(weapons.WEAPON_ORDER[new_index])

    def get_nose_position(self):
        """Where bullets should spawn from -- the tip of the ship."""
        return (self.x, self.y - self.height / 2)

    def trigger_shot(self):
        """Call this exactly when a bullet is fired: resets the cooldown
        and starts the muzzle flash animation."""
        self.shot_timer = self.shoot_cooldown
        self.muzzle_flash_timer = 0.08  # seconds the flash stays visible

    def draw(self, surface):
        # --- Hit shake (Step 10) ---
        # A brief, decaying random jitter so getting hit has real physical
        # weight instead of just a number ticking down.
        shake_x = shake_y = 0.0
        if self.hit_shake_timer > 0:
            shake_mag = 7 * (self.hit_shake_timer / self.hit_shake_duration)
            shake_x = random.uniform(-shake_mag, shake_mag)
            shake_y = random.uniform(-shake_mag, shake_mag)

        cx, cy = int(self.x + shake_x), int(self.y + shake_y)
        hw, hh = self.width / 2, self.height / 2

        # Rainbow trail (if active) renders behind everything else, like an
        # afterimage the ship is leaving in its wake.
        if self.victory_effect and self.victory_effect["type"] == "rainbow_trail":
            self._draw_rainbow_trail(surface)

        # --- Engine flame (drawn first, so the ship body covers its top) ---
        flicker = 0.6 + 0.4 * abs(math.sin(self.engine_phase)) + random.uniform(-0.05, 0.05)
        boost_factor = 2.4 if self.boosting else 1.0
        flame_length = 22 * flicker * boost_factor
        flame_points = [
            (cx - 8, cy + hh - 4),
            (cx + 8, cy + hh - 4),
            (cx, cy + hh - 4 + flame_length),
        ]
        pygame.draw.polygon(surface, settings.GOLD, flame_points)
        inner_flame_points = [
            (cx - 4, cy + hh - 4),
            (cx + 4, cy + hh - 4),
            (cx, cy + hh - 4 + flame_length * 0.6),
        ]
        pygame.draw.polygon(surface, settings.WHITE, inner_flame_points)

        # --- Ship body: a simple triangular fuselage with two wings ---
        body_points = [
            (cx, cy - hh),          # nose
            (cx - hw * 0.35, cy + hh * 0.6),
            (cx + hw * 0.35, cy + hh * 0.6),
        ]
        wing_left = [
            (cx - hw * 0.3, cy),
            (cx - hw, cy + hh * 0.7),
            (cx - hw * 0.25, cy + hh * 0.75),
        ]
        wing_right = [
            (cx + hw * 0.3, cy),
            (cx + hw, cy + hh * 0.7),
            (cx + hw * 0.25, cy + hh * 0.75),
        ]

        # --- Boost afterimage trail (Step 9) ---
        # A few fading, offset copies of the hull stretched out behind the
        # ship so an "extreme speed" boost actually reads as extreme speed,
        # not just a slightly-faster glide.
        if self.boosting:
            trail_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            for i in range(1, 5):
                offset_y = i * 16
                alpha = max(0, 100 - i * 22)
                ghost_points = [(px, py + offset_y) for px, py in body_points]
                pygame.draw.polygon(trail_surf, (*self.ship_color, alpha), ghost_points)
            surface.blit(trail_surf, (0, 0))

            # Streak lines shooting past the wingtips -- classic "warp speed" cue
            streak_color = (*settings.WHITE, 120)
            streak_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            for sx in (cx - hw * 0.6, cx, cx + hw * 0.6):
                pygame.draw.line(
                    streak_surf, streak_color,
                    (sx, cy + hh), (sx, cy + hh + 46 * flicker), width=2
                )
            surface.blit(streak_surf, (0, 0))

        pygame.draw.polygon(surface, self.wing_color, wing_left)
        pygame.draw.polygon(surface, self.wing_color, wing_right)
        pygame.draw.polygon(surface, self.ship_color, body_points)
        pygame.draw.polygon(surface, settings.WHITE, body_points, width=2)

        # --- Damage flicker (Step 10) ---
        # Hard red strobe over the hull right after taking a hit -- blinks
        # a few times over damage_flash_duration rather than a flat tint,
        # which reads much more like "just got hit" than a static overlay.
        if self.damage_flash_timer > 0:
            blink_on = int(self.damage_flash_timer * 18) % 2 == 0
            if blink_on:
                flash_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                pygame.draw.polygon(flash_surf, (255, 40, 40, 165), body_points)
                pygame.draw.polygon(flash_surf, (255, 40, 40, 165), wing_left)
                pygame.draw.polygon(flash_surf, (255, 40, 40, 165), wing_right)
                surface.blit(flash_surf, (0, 0))

        # Cockpit glow
        pygame.draw.circle(surface, settings.NEON_GREEN, (cx, cy - hh * 0.15), 5)

        # --- Shield bubble (Step: fist gesture) ---
        if self.is_shielded:
            pulse = 0.7 + 0.3 * abs(math.sin(self.engine_phase * 0.6))
            shield_radius = int(max(hw, hh) * 1.5)
            shield_surf = pygame.Surface((shield_radius * 2 + 8, shield_radius * 2 + 8), pygame.SRCALPHA)
            alpha = int(90 * pulse)
            pygame.draw.circle(shield_surf, (*settings.NEON_BLUE, alpha),
                                (shield_radius + 4, shield_radius + 4), shield_radius)
            pygame.draw.circle(shield_surf, (*settings.WHITE, min(255, alpha + 60)),
                                (shield_radius + 4, shield_radius + 4), shield_radius, width=2)
            surface.blit(shield_surf, (cx - shield_radius - 4, cy - shield_radius - 4))

        # --- Muzzle flash -- color and size match whichever weapon is
        # equipped, so a weapon swap is visible even without checking the
        # HUD badge (plasma gets a fat slow flash, rapid a tiny quick one,
        # everything else in between). ---
        if self.muzzle_flash_timer > 0:
            weapon_color = weapons.get_color(self.weapon_name)
            size_mult = {"plasma": 1.6, "spread": 1.25, "rapid": 0.65}.get(self.weapon_name, 1.0)
            flash_progress = self.muzzle_flash_timer / 0.08  # 1.0 -> 0.0
            nose_x, nose_y = self.get_nose_position()
            flash_radius = max(2, int((4 + 10 * flash_progress) * size_mult))
            flash_surf = pygame.Surface((flash_radius * 4, flash_radius * 4), pygame.SRCALPHA)
            alpha = int(220 * flash_progress)
            pygame.draw.circle(
                flash_surf, (*settings.WHITE, alpha),
                (flash_radius * 2, flash_radius * 2), flash_radius
            )
            pygame.draw.circle(
                flash_surf, (*weapon_color, alpha),
                (flash_radius * 2, flash_radius * 2), flash_radius, width=2
            )
            surface.blit(
                flash_surf,
                (int(nose_x) - flash_radius * 2, int(nose_y) - flash_radius * 2)
            )

        if self.victory_effect and self.victory_effect["type"] != "rainbow_trail":
            self._draw_victory_effect(surface, cx, cy)

    # ------------------------------------------------------------------
    # Post-boss victory effects -- a different one each time, purely
    # cosmetic, doesn't touch gameplay stats at all.
    # ------------------------------------------------------------------

    def _draw_rainbow_trail(self, surface):
        pts = list(self.position_history)
        n = len(pts)
        for i, (px, py) in enumerate(pts):
            hue = (self.victory_effect["timer"] * 0.5 + i * 0.04) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
            fade = i / max(1, n - 1)  # older points fade out
            alpha = int(160 * fade)
            size = 3 + int(6 * fade)
            pad = size + 2
            ghost_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
            pygame.draw.circle(ghost_surf, (int(r * 255), int(g * 255), int(b * 255), alpha), (pad, pad), size)
            surface.blit(ghost_surf, (px - pad, py - pad))

    def _draw_victory_effect(self, surface, cx, cy):
        effect = self.victory_effect
        kind = effect["type"]
        data = effect["data"]
        t = effect["timer"]
        duration = effect["duration"]
        fade = 1.0 - min(1.0, t / duration)  # overall fade-out across the whole effect

        if kind == "golden_aura":
            for i in range(3):
                ring_t = (t * 1.2 + i * 0.33) % 1.0
                r = int(28 + ring_t * 66)
                alpha = int(200 * (1 - ring_t) * fade)
                if alpha > 1:
                    pad = r + 4
                    ring_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
                    pygame.draw.circle(ring_surf, (*settings.GOLD, alpha), (pad, pad), r, width=3)
                    surface.blit(ring_surf, (cx - pad, cy - pad))
            for i in range(8):
                a = t * 2.4 + i * (math.tau / 8)
                r = 42
                sx, sy = cx + math.cos(a) * r, cy + math.sin(a) * r
                spark_r = int(3 * fade) + 1
                spark_surf = pygame.Surface((spark_r * 4, spark_r * 4), pygame.SRCALPHA)
                pygame.draw.circle(spark_surf, (*settings.GOLD, int(255 * fade)), (spark_r * 2, spark_r * 2), spark_r)
                surface.blit(spark_surf, (sx - spark_r * 2, sy - spark_r * 2))

        elif kind == "lightning_arcs":
            for bolt in data["bolts"]:
                flicker = 0.5 + 0.5 * abs(math.sin(t * 22 + bolt["flicker_seed"]))
                if flicker < 0.55:
                    continue
                angle = bolt["angle"] + math.sin(t * 3 + bolt["flicker_seed"]) * 0.15
                length = bolt["length"]
                segments = 4
                points = [(cx, cy)]
                for s in range(1, segments + 1):
                    frac = s / segments
                    base_x = cx + math.cos(angle) * length * frac
                    base_y = cy + math.sin(angle) * length * frac
                    jitter = bolt["jitter"][(s - 1) % len(bolt["jitter"])] * 10 * (1 - frac * 0.5)
                    perp = angle + math.pi / 2
                    base_x += math.cos(perp) * jitter
                    base_y += math.sin(perp) * jitter
                    points.append((base_x, base_y))
                alpha = int(255 * fade * flicker)
                bolt_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                pygame.draw.lines(bolt_surf, (*settings.NEON_BLUE, alpha), False, points, width=2)
                pygame.draw.lines(bolt_surf, (*settings.WHITE, min(255, alpha + 40)), False, points, width=1)
                surface.blit(bolt_surf, (0, 0))

        elif kind == "shockwave_pulse":
            pulse_period = 0.5
            phase = (t % pulse_period) / pulse_period
            r = int(20 + phase * 90)
            alpha = int(220 * (1 - phase) * fade)
            if alpha > 1:
                pad = r + 4
                ring_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (*settings.NEON_BLUE, alpha), (pad, pad), r, width=4)
                pygame.draw.circle(ring_surf, (*settings.WHITE, min(255, alpha + 30)), (pad, pad), r, width=1)
                surface.blit(ring_surf, (cx - pad, cy - pad))

        elif kind == "star_rays":
            ray_count = data["ray_count"]
            spin = t * data["spin_dir"] * 1.6
            ray_len = 50 + 10 * abs(math.sin(t * 5))
            ray_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            for i in range(ray_count):
                angle = spin + (math.tau / ray_count) * i
                tip = (cx + math.cos(angle) * ray_len, cy + math.sin(angle) * ray_len)
                perp = angle + math.pi / 2
                base_w = 4
                p1 = (cx + math.cos(perp) * base_w, cy + math.sin(perp) * base_w)
                p2 = (cx - math.cos(perp) * base_w, cy - math.sin(perp) * base_w)
                alpha = int(180 * fade)
                pygame.draw.polygon(ray_surf, (*settings.GOLD, alpha), [p1, p2, tip])
            surface.blit(ray_surf, (0, 0))
            core_r = int(6 + 3 * abs(math.sin(t * 6)))
            pygame.draw.circle(surface, settings.WHITE, (cx, cy), core_r)

        elif kind == "phoenix_flames":
            flame_colors = [(255, 210, 60), (255, 140, 40), (255, 70, 40)]
            for p in data["particles"]:
                age_frac = p["age"] / p["life"]
                color = flame_colors[min(len(flame_colors) - 1, int(age_frac * len(flame_colors)))]
                alpha = int(220 * (1 - age_frac) * fade)
                size = max(1, p["size"] * (1 - age_frac * 0.5))
                pad = int(size) + 2
                flame_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
                pygame.draw.circle(flame_surf, (*color, alpha), (pad, pad), size)
                surface.blit(flame_surf, (p["x"] - pad, p["y"] - pad))

        elif kind == "orbiting_rings":
            for ring in data["rings"]:
                angle_off = t * ring["speed"]
                rect = pygame.Rect(0, 0, ring["radius"] * 2, ring["radius"] * ring["tilt"] * 2)
                rect.center = (cx, cy)
                alpha = int(200 * fade)
                ring_surf = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
                sub_rect = pygame.Rect(4, 4, rect.width, rect.height)
                pygame.draw.ellipse(ring_surf, (*ring["color"], int(alpha * 0.35)), sub_rect, width=2)
                # Bright moving arc riding the ellipse for a sense of rotation
                start_a = angle_off
                pygame.draw.arc(ring_surf, (*ring["color"], alpha), sub_rect, start_a, start_a + 1.4, width=3)
                surface.blit(ring_surf, (rect.x - 4, rect.y - 4))