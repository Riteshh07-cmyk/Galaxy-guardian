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
        self.hp_display = float(self.health)  # eases toward `health` -- makes the HUD bar drain smoothly instead of jumping
        self.invincible_timer = 0.0
        self.damage_flash_timer = 0.0  # > 0 briefly right after taking a hit -- drives ship flash/blink + impact ring
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
        self.shield_activate_flash = 0.0   # > 0 briefly right when shield goes up -- drives an expanding "pop" ring

        # --- Boost (open palm gesture triggers it, then it runs on its own
        # timer -- like the shield, not a "hold to go fast" control) ---
        self.boosting = False
        self.boost_multiplier = settings.BOOST_SPEED_MULTIPLIER
        self.boost_duration = settings.BOOST_DURATION_SECONDS
        self.boost_cooldown = settings.BOOST_COOLDOWN_SECONDS
        self.boost_timer = 0.0            # > 0 while boost is actively running
        self.boost_cooldown_timer = 0.0   # > 0 while boost is unavailable

    def update(self, dt, target_x, target_y, keyboard_dx=0.0, keyboard_dy=0.0):
        """target_x/target_y: where the player's index fingertip currently
        maps to on screen, or None if no hand is currently detected.
        keyboard_dx/keyboard_dy: direct movement speed from arrow-key/WASD
        backup controls -- when either is non-zero, keyboard takes priority
        over finger tracking for this frame.
        Boost is no longer a "hold to activate" flag passed in here -- call
        activate_boost() once (e.g. on the open_palm gesture) and it runs
        for boost_duration seconds on its own, same pattern as the shield."""
        self.boosting = self.boost_timer > 0.0
        speed_mult = self.boost_multiplier if self.boosting else 1.0

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
        self.shield_activate_flash = max(0.0, self.shield_activate_flash - dt)
        self.boost_timer = max(0.0, self.boost_timer - dt)
        self.boost_cooldown_timer = max(0.0, self.boost_cooldown_timer - dt)
        self.damage_flash_timer = max(0.0, self.damage_flash_timer - dt)
        self.hp_display += (self.health - self.hp_display) * min(1.0, 6.0 * dt)

    def can_shoot(self):
        return self.shot_timer <= 0.0

    def can_activate_shield(self):
        return self.shield_timer <= 0.0 and self.shield_cooldown_timer <= 0.0

    def activate_shield(self):
        self.shield_timer = self.shield_duration
        self.shield_cooldown_timer = self.shield_duration + self.shield_cooldown
        self.shield_activate_flash = 0.4

    @property
    def is_shielded(self):
        return self.shield_timer > 0.0

    def can_activate_boost(self):
        return self.boost_timer <= 0.0 and self.boost_cooldown_timer <= 0.0

    def activate_boost(self):
        self.boost_timer = self.boost_duration
        self.boost_cooldown_timer = self.boost_duration + self.boost_cooldown

    @property
    def is_boosting(self):
        return self.boost_timer > 0.0

    def get_rect(self):
        return pygame.Rect(
            int(self.x - self.width / 2), int(self.y - self.height / 2),
            self.width, self.height
        )

    def take_damage(self, amount):
        # Boosting acts like a temporary shield too -- ramming through
        # enemies at that speed shouldn't hurt the ship. main.py is the
        # one that actually destroys the rammed enemy; this just makes
        # sure the player doesn't also take damage from the same hit.
        if self.invincible_timer > 0 or self.is_shielded or self.is_boosting:
            return False
        self.health -= amount
        self.damage_flash_timer = 0.3
        if self.health <= 0:
            self.health = 0
            self.game_over = True
        else:
            self.invincible_timer = 1.0
        return True

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
        boost_factor = 1.7 if self.boosting else 1.0
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

        # --- Ship body: a simple triangular fuselage with two wings.
        # While the post-hit invincibility window is running, blink the
        # body on/off and tint it red -- the classic "you just got hit"
        # arcade shooter cue. ---
        blink_visible = True
        body_color = self.ship_color
        wing_color = self.wing_color
        if self.invincible_timer > 0:
            blink_visible = (int(self.invincible_timer * 14) % 2 == 0)
            body_color = settings.DANGER_RED
            wing_color = (140, 30, 30)

        if blink_visible:
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

            pygame.draw.polygon(surface, wing_color, wing_left)
            pygame.draw.polygon(surface, wing_color, wing_right)
            pygame.draw.polygon(surface, body_color, body_points)
            pygame.draw.polygon(surface, settings.WHITE, body_points, width=2)

            # Cockpit glow
            pygame.draw.circle(surface, settings.NEON_GREEN, (cx, cy - hh * 0.15), 5)

        # --- Hit impact ring: a quick red shockwave the instant damage
        # actually lands, independent of the blink above so it still
        # reads even in the same frame the ship starts flickering. ---
        if self.damage_flash_timer > 0:
            progress = 1.0 - (self.damage_flash_timer / 0.3)  # 0.0 -> 1.0
            ring_radius = int(max(hw, hh) * (1.0 + progress * 2.0))
            ring_alpha = int(230 * (1.0 - progress))
            if ring_alpha > 0 and ring_radius > 0:
                ring_surf = pygame.Surface((ring_radius * 2 + 8, ring_radius * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (*settings.DANGER_RED, ring_alpha),
                                    (ring_radius + 4, ring_radius + 4), ring_radius, width=3)
                surface.blit(ring_surf, (cx - ring_radius - 4, cy - ring_radius - 4))

        # --- Boost speed-aura: a stretched, streaking glow while the timed
        # boost power-up is active. Visually distinct from the round fist
        # shield bubble so the player can tell the two apart at a glance. ---
        if self.is_boosting:
            pulse = 0.75 + 0.25 * abs(math.sin(self.engine_phase * 1.4))
            aura_w = int(self.width * 1.6)
            aura_h = int(self.height * 2.2)
            aura_surf = pygame.Surface((aura_w + 12, aura_h + 12), pygame.SRCALPHA)
            aura_alpha = int(70 * pulse)
            aura_rect = pygame.Rect(6, 6, aura_w, aura_h)
            pygame.draw.ellipse(aura_surf, (*settings.GOLD, aura_alpha), aura_rect)
            pygame.draw.ellipse(aura_surf, (*settings.WHITE, min(255, aura_alpha + 50)), aura_rect, width=2)
            surface.blit(aura_surf, (cx - aura_w // 2 - 6, cy - aura_h // 2 - 6))

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

        # --- Shield activation "pop" ring: expands outward and fades
        # right at the moment the fist gesture triggers the shield, so
        # activation reads as an event instead of the bubble just
        # appearing. Purely cosmetic, runs independently of shield_timer
        # so it still plays even in the same frame the shield goes up. ---
        if self.shield_activate_flash > 0:
            progress = 1.0 - (self.shield_activate_flash / 0.4)  # 0.0 -> 1.0
            ring_radius = int(max(hw, hh) * (1.0 + progress * 2.2))
            ring_alpha = int(220 * (1.0 - progress))
            if ring_alpha > 0 and ring_radius > 0:
                ring_surf = pygame.Surface((ring_radius * 2 + 8, ring_radius * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (*settings.NEON_BLUE, ring_alpha),
                                    (ring_radius + 4, ring_radius + 4), ring_radius, width=3)
                surface.blit(ring_surf, (cx - ring_radius - 4, cy - ring_radius - 4))

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