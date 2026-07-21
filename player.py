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

import pygame

import settings
import weapons
import ships


class Player:
    def __init__(self, ship_type="guardian"):
        ship_cfg = ships.SHIP_TYPES.get(ship_type, ships.SHIP_TYPES["guardian"])
        self.ship_type = ship_type
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
        self.lives = settings.PLAYER_START_LIVES
        self.invincible_timer = 0.0
        self.game_over = False

        # --- Shooting (Step 7-8) ---
        self.weapon_name = weapons.WEAPON_ORDER[0]
        self.shoot_cooldown = weapons.get_cooldown(self.weapon_name) / self.fire_rate_mult
        self.shot_timer = 0.0          # counts down to 0; can shoot when <= 0
        self.muzzle_flash_timer = 0.0  # counts down; muzzle flash drawn while > 0

    def update(self, dt, target_x, target_y):
        """target_x/target_y: where the player's index fingertip currently
        maps to on screen, or None if no hand is currently detected
        (in which case the ship just stays where it is)."""
        if target_x is not None and target_y is not None:
            # Framerate-independent exponential smoothing: no matter the
            # FPS, the ship converges to the target at the same real-world
            # speed. (At low FPS it would look choppier, but never "faster".)
            alpha = 1 - math.exp(-self.smoothing_rate * dt)
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

    def can_shoot(self):
        return self.shot_timer <= 0.0

    def get_rect(self):
        return pygame.Rect(
            int(self.x - self.width / 2), int(self.y - self.height / 2),
            self.width, self.height
        )

    def take_damage(self, amount):
        if self.invincible_timer > 0:
            return
        self.health -= amount
        if self.health <= 0:
            self.lives -= 1
            if self.lives < 0:
                self.lives = 0
                self.game_over = True
            else:
                self.health = self.max_health
                self.invincible_timer = 3.0
                self.x = settings.SCREEN_WIDTH / 2
                self.y = settings.SCREEN_HEIGHT - 120
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
        cx, cy = int(self.x), int(self.y)
        hw, hh = self.width / 2, self.height / 2

        # --- Engine flame (drawn first, so the ship body covers its top) ---
        flicker = 0.6 + 0.4 * abs(math.sin(self.engine_phase)) + random.uniform(-0.05, 0.05)
        flame_length = 22 * flicker
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

        pygame.draw.polygon(surface, self.wing_color, wing_left)
        pygame.draw.polygon(surface, self.wing_color, wing_right)
        pygame.draw.polygon(surface, self.ship_color, body_points)
        pygame.draw.polygon(surface, settings.WHITE, body_points, width=2)

        # Cockpit glow
        pygame.draw.circle(surface, settings.NEON_GREEN, (cx, cy - hh * 0.15), 5)

        # --- Muzzle flash (Step 7) ---
        if self.muzzle_flash_timer > 0:
            flash_progress = self.muzzle_flash_timer / 0.08  # 1.0 -> 0.0
            nose_x, nose_y = self.get_nose_position()
            flash_radius = int(4 + 10 * flash_progress)
            flash_surf = pygame.Surface((flash_radius * 4, flash_radius * 4), pygame.SRCALPHA)
            alpha = int(220 * flash_progress)
            pygame.draw.circle(
                flash_surf, (*settings.WHITE, alpha),
                (flash_radius * 2, flash_radius * 2), flash_radius
            )
            pygame.draw.circle(
                flash_surf, (*settings.NEON_GREEN, alpha),
                (flash_radius * 2, flash_radius * 2), flash_radius, width=2
            )
            surface.blit(
                flash_surf,
                (int(nose_x) - flash_radius * 2, int(nose_y) - flash_radius * 2)
            )