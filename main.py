"""
main.py
-------
STEP 8 GOAL: Multiple weapon types with different bullet patterns.

New in this step:
  - weapons.py defines 6 weapon types: normal, double, triple, spread,
    rapid, plasma -- each with its own cooldown, bullet pattern, speed,
    and color.
  - Press number keys 1-6 to switch weapons (TEMPORARY test controls --
    later this will be driven by progressive unlocks/power-ups instead
    of manual key presses).
  - The current weapon's name is shown in the HUD while playing.

Everything else (pinch to fire, cooldown, muzzle flash) works exactly
like Step 7 -- just now it fires whatever weapon is currently selected.
"""

import sys
import random
import pygame

import settings
from background import Starfield
from menu import MainMenu
from camera import CameraManager
from gesture import HandTracker, GestureRecognizer, SwipeDetector
from player import Player
from bullet import Bullet
import weapons
from enemy import spawn_random_enemy
from explosion import Explosion
from hazard import spawn_hazard
from boss import Boss
import pickups
import powerups
from hud import HUD, draw_screen_flash
from audio import AudioManager
import particles
import highscore
import progress
import ships
from screens import ControlsScreen, HighScoresScreen, SettingsScreen, HangarScreen, PauseScreen, GameOverScreen, PowerupScreen
from utils import cv2_frame_to_pygame_surface

ENEMY_SPAWN_INTERVAL = 1.4
LEVEL_SCORE_STEP = 500
BOSS_LEVEL_INTERVAL = 6   # a boss fight kicks off every 6 levels (6, 12, 18, ...)
KEYBOARD_MOVE_SPEED = 420
HAZARD_SPAWN_INTERVAL = 0.30      # how often boost hazards spawn while boosting
SCREEN_FLASH_HIT_DURATION = 0.16
SCREEN_FLASH_BLOCK_DURATION = 0.10


STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_CONTROLS = "controls"
STATE_HIGH_SCORES = "high_scores"
STATE_SETTINGS = "settings"
STATE_HANGAR = "hangar"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "game_over"
STATE_POWERUP_SELECT = "powerup_select"

PREVIEW_WIDTH = 240
PREVIEW_HEIGHT = 180
PREVIEW_MARGIN = 16

WEAPON_KEYS = {
    pygame.K_1: "normal",
    pygame.K_2: "double",
    pygame.K_3: "triple",
    pygame.K_4: "spread",
    pygame.K_5: "rapid",
    pygame.K_6: "plasma",
}


def main():
    pygame.init()
    pygame.display.set_caption(settings.GAME_TITLE)

    progress_data = progress.load_progress()

    screen = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    is_fullscreen = progress_data.get("fullscreen", False)
    if is_fullscreen:
        display_surf = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        display_surf = pygame.display.set_mode(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.RESIZABLE
        )

    def get_scaled_rect(window_size, base_size=(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)):
        win_w, win_h = window_size
        base_w, base_h = base_size
        scale = min(win_w / base_w, win_h / base_h)
        new_w, new_h = int(base_w * scale), int(base_h * scale)
        return pygame.Rect((win_w - new_w) // 2, (win_h - new_h) // 2, new_w, new_h), scale

    clock = pygame.time.Clock()
    debug_font = pygame.font.SysFont("consolas", 20)
    small_font = pygame.font.SysFont("consolas", 16)
    gesture_font = pygame.font.SysFont("consolas", 22, bold=True)

    starfield = Starfield()
    main_menu = MainMenu()
    player = Player(progress_data["selected_ship"])
    controls_screen = ControlsScreen()
    high_scores_screen = HighScoresScreen()
    settings_screen = SettingsScreen()
    hangar_screen = HangarScreen()
    pause_screen = PauseScreen()
    powerup_screen = PowerupScreen()
    game_over_screen = GameOverScreen()
    hud = HUD()
    audio_manager = AudioManager()
    audio_manager.set_volume(progress_data.get("master_volume", settings.DEFAULT_MUSIC_VOLUME))
    impact_particles = particles.ParticleSystem()
    high_scores_data = highscore.load_high_scores()
    settings_return_state = STATE_MENU
    game_over_stats = {}

    camera = CameraManager()
    camera.start()
    hand_tracker = HandTracker(max_num_hands=2)
    gesture_recognizer = GestureRecognizer(
        pinch_threshold=progress_data.get("gesture_sensitivity", 0.45)
    )
    swipe_detector = SwipeDetector()

    def make_new_run():
        fresh_player = Player(progress_data["selected_ship"])
        return fresh_player, [], [], [], [], ENEMY_SPAWN_INTERVAL, 0, 1, 0.0, None, [], 0, 0.0, [], []

    state = STATE_MENU
    running = True
    debug_mode = True  # press F3 to toggle -- shows crosshair + coordinate readout
    camera_preview_visible = True  # toggle in Settings -- hides the webcam feed box
    bullets = []
    enemies = []
    hazards = []
    explosions = []
    enemy_spawn_timer = ENEMY_SPAWN_INTERVAL
    hazard_spawn_timer = 0.0
    score = 0
    level = 1
    level_up_timer = 0.0

    # --- Boss fights (every BOSS_LEVEL_INTERVAL levels) ---
    boss = None
    boss_bullets = []
    boss_spawn_index = 0
    boss_intro_timer = 0.0
    coins = []
    credit_popups = []  # floating "+N" feedback text when a coin is collected

    # --- Game-feel: hit-stop + screen shake, both purely cosmetic ---
    hitstop_timer = 0.0
    world_shake_timer = 0.0
    world_shake_magnitude = 0.0
    was_boosting = False
    world_surf = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))

    # --- Screen flash feedback (Step 10) ---
    screen_flash_timer = 0.0
    screen_flash_start = 0.0
    screen_flash_color = settings.DANGER_RED

    # Remembers where the flying hand's fingertip was last seen (normalized
    # 0.0-1.0 coords). Used to keep tracking the SAME hand across frames
    # when 2 hands are visible, instead of randomly jumping between them.
    last_target_norm = None

    preview_rect = pygame.Rect(
        settings.SCREEN_WIDTH - PREVIEW_WIDTH - PREVIEW_MARGIN,
        settings.SCREEN_HEIGHT - PREVIEW_HEIGHT - PREVIEW_MARGIN - 24,
        PREVIEW_WIDTH,
        PREVIEW_HEIGHT,
    )
    preview_rect.top -= 32

    while running:
        dt = clock.tick(settings.FPS) / 1000.0
        raw_mouse = pygame.mouse.get_pos()
        scaled_rect, _scale = get_scaled_rect(display_surf.get_size())
        mouse_pos = (
            (raw_mouse[0] - scaled_rect.x) / _scale,
            (raw_mouse[1] - scaled_rect.y) / _scale,
        )
        screen_flash_timer = max(0.0, screen_flash_timer - dt)
        hud.update(dt)

        # =====================================================================
        # 1. EVENTS
        # =====================================================================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.WINDOWFOCUSLOST and state == STATE_PLAYING:
                state = STATE_PAUSED

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state == STATE_PLAYING:
                        state = STATE_PAUSED
                    elif state == STATE_PAUSED:
                        state = STATE_PLAYING
                    elif state == STATE_SETTINGS:
                        state = settings_return_state
                    elif state in (STATE_CONTROLS, STATE_HIGH_SCORES, STATE_HANGAR, STATE_GAME_OVER):
                        state = STATE_MENU
                    elif state == STATE_POWERUP_SELECT:
                        pass  # force a deliberate click -- don't let ESC skip or quit here
                    else:
                        running = False
                elif event.key == pygame.K_p:
                    if state == STATE_PLAYING:
                        state = STATE_PAUSED
                    elif state == STATE_PAUSED:
                        state = STATE_PLAYING
                elif event.key == pygame.K_F3:
                    debug_mode = not debug_mode
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        display_surf = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        display_surf = pygame.display.set_mode(
                            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.RESIZABLE
                        )
                    progress_data["fullscreen"] = is_fullscreen
                    progress.save_progress(progress_data)
                elif state == STATE_PLAYING and event.key in WEAPON_KEYS:
                    player.set_weapon(WEAPON_KEYS[event.key])

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if state == STATE_MENU:
                    action = main_menu.handle_click(mouse_pos)
                    if action == "play":
                        state = STATE_PLAYING
                        player, bullets, enemies, hazards, explosions, enemy_spawn_timer, score, level, level_up_timer, boss, boss_bullets, boss_spawn_index, boss_intro_timer, coins, credit_popups = make_new_run()
                        hitstop_timer = 0.0
                        world_shake_timer = 0.0
                        was_boosting = False
                    elif action == "exit":
                        running = False
                    elif action == "controls":
                        state = STATE_CONTROLS
                    elif action == "high_scores":
                        high_scores_data = highscore.load_high_scores()
                        state = STATE_HIGH_SCORES
                    elif action == "settings":
                        settings_return_state = STATE_MENU
                        state = STATE_SETTINGS
                    elif action == "hangar":
                        state = STATE_HANGAR
                elif state == STATE_CONTROLS:
                    if controls_screen.handle_click(mouse_pos) == "back":
                        state = STATE_MENU
                elif state == STATE_HIGH_SCORES:
                    if high_scores_screen.handle_click(mouse_pos) == "back":
                        state = STATE_MENU
                elif state == STATE_SETTINGS:
                    action, progress_data, debug_mode, camera_preview_visible = settings_screen.handle_click(
                        mouse_pos, progress_data, debug_mode, camera_preview_visible
                    )
                    if action == "back":
                        state = settings_return_state
                    elif action == "toggle_fullscreen":
                        is_fullscreen = progress_data.get("fullscreen", False)
                        if is_fullscreen:
                            display_surf = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        else:
                            display_surf = pygame.display.set_mode(
                                (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.RESIZABLE
                            )
                elif state == STATE_HANGAR:
                    action, progress_data = hangar_screen.handle_click(mouse_pos, progress_data)
                    if action == "back":
                        state = STATE_MENU
                elif state == STATE_PAUSED:
                    action, progress_data = pause_screen.handle_click(mouse_pos, progress_data)
                    if action == "resume":
                        state = STATE_PLAYING
                    elif action == "restart":
                        player, bullets, enemies, hazards, explosions, enemy_spawn_timer, score, level, level_up_timer, boss, boss_bullets, boss_spawn_index, boss_intro_timer, coins, credit_popups = make_new_run()
                        hitstop_timer = 0.0
                        world_shake_timer = 0.0
                        was_boosting = False
                        state = STATE_PLAYING
                    elif action == "settings":
                        settings_return_state = STATE_PAUSED
                        state = STATE_SETTINGS
                    elif action == "main_menu":
                        state = STATE_MENU
                elif state == STATE_GAME_OVER:
                    action = game_over_screen.handle_click(mouse_pos)
                    if action == "restart":
                        player, bullets, enemies, hazards, explosions, enemy_spawn_timer, score, level, level_up_timer, boss, boss_bullets, boss_spawn_index, boss_intro_timer, coins, credit_popups = make_new_run()
                        hitstop_timer = 0.0
                        world_shake_timer = 0.0
                        was_boosting = False
                        state = STATE_PLAYING
                    elif action == "main_menu":
                        state = STATE_MENU

                elif state == STATE_POWERUP_SELECT:
                    chosen_powerup = powerup_screen.handle_click(mouse_pos)
                    if chosen_powerup is not None:
                        powerups.apply_powerup(player, chosen_powerup)
                        audio_manager.play_sfx("powerup_select")
                        state = STATE_PLAYING

            if state == STATE_SETTINGS:
                settings_screen.handle_event(event, audio_manager, progress_data)
                gesture_recognizer.set_sensitivity(progress_data.get("gesture_sensitivity", 0.45))
            elif state == STATE_PAUSED:
                pause_screen.handle_event(event, audio_manager)

            if state in (STATE_SETTINGS, STATE_PAUSED) and event.type in (
                pygame.MOUSEBUTTONUP, pygame.MOUSEBUTTONDOWN
            ):
                changed = progress_data.get("master_volume") != audio_manager.volume
                if changed:
                    progress_data["master_volume"] = audio_manager.volume
                if event.type == pygame.MOUSEBUTTONUP and state == STATE_SETTINGS:
                    progress.save_progress(progress_data)
                elif changed:
                    progress.save_progress(progress_data)

        # =====================================================================
        # 2. UPDATE -- figure out what's happening this frame
        # =====================================================================
        starfield_speed_mult = 2.6 if (state == STATE_PLAYING and player.boosting) else 1.0
        starfield.update(dt, starfield_speed_mult)
        if state == STATE_MENU:
            main_menu.update(dt, mouse_pos)
        elif state == STATE_CONTROLS:
            controls_screen.update(dt, mouse_pos)
        elif state == STATE_HIGH_SCORES:
            high_scores_screen.update(dt, mouse_pos)
        elif state == STATE_SETTINGS:
            settings_screen.update(dt, mouse_pos)
        elif state == STATE_HANGAR:
            hangar_screen.update(dt, mouse_pos)
        elif state == STATE_PAUSED:
            pause_screen.update(dt, mouse_pos)
        elif state == STATE_GAME_OVER:
            game_over_screen.update(dt, mouse_pos)
        elif state == STATE_POWERUP_SELECT:
            powerup_screen.update(dt, mouse_pos)

        if state == STATE_PLAYING:
            audio_manager.play_action_music()
        else:
            audio_manager.play_menu_music()

        # --- Camera + gesture processing (runs every frame, both states) ---
        camera_frame_for_display = None   # frame with landmarks drawn on it
        hand_count = 0
        current_gesture = "none"
        index_fingertip_norm = None       # (x, y) 0.0-1.0, or None if no hand

        if camera.connected:
            frame = camera.get_latest_frame()
            if frame is not None:
                results = hand_tracker.process(frame)
                frame_h, frame_w = frame.shape[0], frame.shape[1]

                pixel_positions = hand_tracker.get_landmark_pixel_positions(
                    results, frame_w, frame_h
                )
                normalized_positions = hand_tracker.get_landmark_normalized_positions(results)

                current_gesture = gesture_recognizer.update(pixel_positions)
                hand_count = hand_tracker.get_hand_count(results)

                if len(normalized_positions) > 0:
                    # Landmark 8 = index fingertip.
                    if len(normalized_positions) == 1 or last_target_norm is None:
                        chosen_hand = normalized_positions[0]
                    else:
                        # Multiple hands visible -- keep tracking whichever
                        # one is closest to where we were already tracking,
                        # instead of possibly jumping to a different hand.
                        def dist_sq(hand):
                            fx, fy = hand[8]
                            lx, ly = last_target_norm
                            return (fx - lx) ** 2 + (fy - ly) ** 2
                        chosen_hand = min(normalized_positions, key=dist_sq)

                    index_fingertip_norm = chosen_hand[8]
                    last_target_norm = index_fingertip_norm

                camera_frame_for_display = hand_tracker.draw_landmarks(frame, results)

        # --- Player movement (only while actually playing) ---
        if state == STATE_PLAYING:
            diff_key = progress_data.get("difficulty", "normal")
            diff_cfg = settings.DIFFICULTY_LEVELS.get(diff_key, settings.DIFFICULTY_LEVELS["normal"])

            # --- Hit-stop: a brief slow-motion "punch" on big moments
            # (player hit, boss phase change, boss defeated). Camera/hand
            # tracking above already ran at real dt so input stays
            # responsive; only the game-world entities below feel it. ---
            hitstop_timer = max(0.0, hitstop_timer - dt)
            effective_dt = dt * 0.06 if hitstop_timer > 0 else dt

            if index_fingertip_norm is not None:
                target_x = index_fingertip_norm[0] * settings.SCREEN_WIDTH
                target_y = index_fingertip_norm[1] * settings.SCREEN_HEIGHT
            else:
                target_x, target_y = None, None

            # --- Keyboard backup controls ---
            keys_held = pygame.key.get_pressed()
            kb_dx, kb_dy = 0.0, 0.0
            if keys_held[pygame.K_LEFT] or keys_held[pygame.K_a]:
                kb_dx -= KEYBOARD_MOVE_SPEED
            if keys_held[pygame.K_RIGHT] or keys_held[pygame.K_d]:
                kb_dx += KEYBOARD_MOVE_SPEED
            if keys_held[pygame.K_UP] or keys_held[pygame.K_w]:
                kb_dy -= KEYBOARD_MOVE_SPEED
            if keys_held[pygame.K_DOWN] or keys_held[pygame.K_s]:
                kb_dy += KEYBOARD_MOVE_SPEED

            boost_requested = (current_gesture == "open_palm") or keys_held[pygame.K_LSHIFT] or keys_held[pygame.K_RSHIFT]
            player.update(effective_dt, target_x, target_y, kb_dx, kb_dy, boost_requested)

            if player.boosting and not was_boosting:
                audio_manager.play_sfx("boost_engage")
            was_boosting = player.boosting

            # --- Shooting: pinch gesture OR Space, gated by cooldown ---
            if (current_gesture == "pinch" or keys_held[pygame.K_SPACE]) and player.can_shoot():
                nose_x, nose_y = player.get_nose_position()
                new_bullets = weapons.spawn_bullets(player.weapon_name, nose_x, nose_y)
                for b in new_bullets:
                    b.damage = max(1, round(b.damage * player.damage_mult))
                bullets.extend(new_bullets)
                player.trigger_shot()
                heavy_weapons = ("spread", "plasma")
                audio_manager.play_sfx("shoot_heavy" if player.weapon_name in heavy_weapons else "shoot_light")

            # --- Shield: fist gesture ---
            if current_gesture == "fist" and player.can_activate_shield():
                player.activate_shield()
                audio_manager.play_sfx("shield_activate")

            # --- Weapon switch: fast horizontal swipe ---
            swipe_x = index_fingertip_norm[0] if index_fingertip_norm is not None else None
            swipe_direction = swipe_detector.update(dt, swipe_x)
            if swipe_direction == "right":
                player.cycle_weapon(1)
            elif swipe_direction == "left":
                player.cycle_weapon(-1)

            for bullet in bullets:
                bullet.update(effective_dt)
            bullets = [b for b in bullets if b.alive]

            # Difficulty (level) is frozen solid while a boss fight is in
            # progress -- no creeping up in toughness mid-fight.
            if boss is None:
                new_level = 1 + score // LEVEL_SCORE_STEP
                if new_level > level:
                    level = new_level
                    level_up_timer = 2.0
            level_up_timer = max(0.0, level_up_timer - dt)
            boss_intro_timer = max(0.0, boss_intro_timer - dt)

            # --- Boss trigger: every BOSS_LEVEL_INTERVAL levels ---
            if boss is None and level >= (boss_spawn_index + 1) * BOSS_LEVEL_INTERVAL:
                boss_spawn_index += 1
                boss = Boss(boss_spawn_index)
                boss.max_health = int(boss.max_health * diff_cfg["speed_mult"])
                boss.health = boss.max_health
                boss.speed *= diff_cfg["speed_mult"]
                boss_intro_timer = 2.4
                level_up_timer = 0.0

            effective_spawn_interval = max(
                0.5, (ENEMY_SPAWN_INTERVAL - 0.05 * (level - 1)) * diff_cfg["spawn_mult"]
            )
            if boss is None:
                enemy_spawn_timer -= dt
                if enemy_spawn_timer <= 0:
                    new_enemy = spawn_random_enemy(level)
                    new_enemy.speed *= diff_cfg["speed_mult"]
                    enemies.append(new_enemy)
                    enemy_spawn_timer = effective_spawn_interval

            # --- Boost hazards (Step 10) ---
            # Extreme speed has a price: while boosting, jagged debris
            # streaks in and has to be dodged Temple-Run style, since it
            # can't be shot down. Spawning stops the instant boost ends,
            # though anything already in flight keeps falling.
            if player.boosting:
                hazard_spawn_timer -= dt
                if hazard_spawn_timer <= 0:
                    hazards.append(spawn_hazard())
                    hazard_spawn_timer = HAZARD_SPAWN_INTERVAL
            else:
                hazard_spawn_timer = min(hazard_spawn_timer, HAZARD_SPAWN_INTERVAL * 0.5)

            for hazard in hazards:
                hazard.update(effective_dt)
            hazards = [h for h in hazards if h.alive and not h.is_offscreen()]

            for hazard in hazards:
                if hazard.alive and hazard.get_rect().colliderect(player.get_rect()) and player.invincible_timer <= 0:
                    was_shielded = player.is_shielded
                    pre_health = player.health
                    player.take_damage(hazard.damage)
                    hit_registered = player.health < pre_health
                    explosions.append(Explosion(
                        hazard.x, hazard.y,
                        color=settings.NEON_BLUE if was_shielded else settings.DANGER_RED,
                        big=not was_shielded,
                    ))
                    hazard.alive = False
                    if hit_registered:
                        screen_flash_timer = screen_flash_start = SCREEN_FLASH_HIT_DURATION
                        screen_flash_color = settings.DANGER_RED
                        audio_manager.play_sfx("player_hit")
                        hitstop_timer = max(hitstop_timer, 0.06)
                        world_shake_timer = max(world_shake_timer, 0.18)
                        world_shake_magnitude = 6
                    elif was_shielded:
                        screen_flash_timer = screen_flash_start = SCREEN_FLASH_BLOCK_DURATION
                        screen_flash_color = settings.NEON_BLUE
                        audio_manager.play_sfx("shield_block")
            hazards = [h for h in hazards if h.alive]

            # --- Boss update + bullets ---
            if boss is not None:
                fired = boss.update(effective_dt, player.x, player.y)
                boss_bullets.extend(fired)
                if boss.phase_changed_this_frame:
                    audio_manager.play_sfx("boss_phase")
                    hitstop_timer = max(hitstop_timer, 0.1)
                    world_shake_timer = max(world_shake_timer, 0.25)
                    world_shake_magnitude = 8

            for bb in boss_bullets:
                bb.update(effective_dt)
            boss_bullets = [b for b in boss_bullets if b.alive]

            for bb in boss_bullets:
                if bb.alive and bb.get_rect().colliderect(player.get_rect()) and player.invincible_timer <= 0:
                    was_shielded = player.is_shielded
                    pre_health = player.health
                    player.take_damage(bb.damage)
                    hit_registered = player.health < pre_health
                    explosions.append(Explosion(
                        bb.x, bb.y,
                        color=settings.NEON_BLUE if was_shielded else settings.DANGER_RED,
                        big=not was_shielded,
                    ))
                    bb.alive = False
                    if hit_registered:
                        screen_flash_timer = screen_flash_start = SCREEN_FLASH_HIT_DURATION
                        screen_flash_color = settings.DANGER_RED
                        audio_manager.play_sfx("player_hit")
                        hitstop_timer = max(hitstop_timer, 0.06)
                        world_shake_timer = max(world_shake_timer, 0.18)
                        world_shake_magnitude = 6
                    elif was_shielded:
                        screen_flash_timer = screen_flash_start = SCREEN_FLASH_BLOCK_DURATION
                        screen_flash_color = settings.NEON_BLUE
                        audio_manager.play_sfx("shield_block")
            boss_bullets = [b for b in boss_bullets if b.alive]

            for enemy in enemies:
                enemy.update(effective_dt, player.x, player.y)
            enemies = [e for e in enemies if e.alive and not e.is_offscreen()]

            for bullet in bullets:
                for enemy in enemies:
                    if not enemy.alive:
                        continue
                    if bullet.get_rect().colliderect(enemy.get_rect()):
                        enemy.take_damage(bullet.damage)
                        bullet.alive = False
                        impact_particles.spawn_hit_spark(bullet.x, bullet.y, color=enemy.color)
                        if not enemy.alive:
                            score += int(enemy.score_value * diff_cfg["score_mult"])
                            explosions.append(Explosion(enemy.x, enemy.y, color=enemy.color))
                            audio_manager.play_sfx("explosion")
                            coins.extend(pickups.maybe_drop_coin(enemy.x, enemy.y))
                        break
            bullets = [b for b in bullets if b.alive]

            if boss is not None:
                for bullet in bullets:
                    if bullet.alive and bullet.get_rect().colliderect(boss.get_rect()):
                        boss.take_damage(bullet.damage)
                        bullet.alive = False
                        impact_particles.spawn_hit_spark(bullet.x, bullet.y, color=boss.core_color)
                bullets = [b for b in bullets if b.alive]

                if not boss.alive:
                    score += int(boss.score_value * diff_cfg["score_mult"])
                    explosions.append(Explosion(boss.x, boss.y, color=boss.core_color, big=True))
                    audio_manager.play_sfx("boss_victory")
                    hitstop_timer = max(hitstop_timer, 0.15)
                    world_shake_timer = max(world_shake_timer, 0.35)
                    world_shake_magnitude = 10
                    coins.extend(pickups.spawn_boss_coin_burst(boss.x, boss.y))
                    boss_bullets.clear()
                    boss = None
                    player.trigger_victory_effect()
                    powerup_screen.set_choices(random.sample(powerups.POWERUP_ORDER, k=min(3, len(powerups.POWERUP_ORDER))))
                    state = STATE_POWERUP_SELECT

            for enemy in enemies:
                if enemy.get_rect().colliderect(player.get_rect()) and player.invincible_timer <= 0:
                    was_shielded = player.is_shielded
                    pre_health = player.health
                    player.take_damage(enemy.collision_damage)
                    hit_registered = player.health < pre_health
                    # A shield-blocked hit still deserves an impact spark,
                    # just smaller than a real hull collision.
                    explosions.append(Explosion(
                        enemy.x, enemy.y,
                        color=settings.NEON_BLUE if was_shielded else settings.DANGER_RED,
                        big=not was_shielded,
                    ))
                    enemy.alive = False
                    if hit_registered:
                        screen_flash_timer = screen_flash_start = SCREEN_FLASH_HIT_DURATION
                        screen_flash_color = settings.DANGER_RED
                        audio_manager.play_sfx("player_hit")
                        hitstop_timer = max(hitstop_timer, 0.06)
                        world_shake_timer = max(world_shake_timer, 0.18)
                        world_shake_magnitude = 6
                    elif was_shielded:
                        screen_flash_timer = screen_flash_start = SCREEN_FLASH_BLOCK_DURATION
                        screen_flash_color = settings.NEON_BLUE
                        audio_manager.play_sfx("shield_block")
            enemies = [e for e in enemies if e.alive]

            for explosion in explosions:
                explosion.update(effective_dt)
            explosions = [e for e in explosions if e.alive]

            impact_particles.update(effective_dt)
            world_shake_timer = max(0.0, world_shake_timer - dt)

            # --- Coin pickups: the actual "earn credits during the run"
            # loop, on top of the flat end-of-run score bonus below. ---
            for coin in coins:
                coin.update(dt)
            for coin in coins:
                if coin.alive and coin.get_rect().colliderect(player.get_rect()):
                    coin.alive = False
                    progress_data["credits"] += coin.value
                    progress.save_progress(progress_data)
                    audio_manager.play_sfx("coin")
                    credit_popups.append({"x": coin.x, "y": coin.y, "text": f"+{coin.value}", "age": 0.0})
            coins = [c for c in coins if c.alive]

            for popup in credit_popups:
                popup["age"] += dt
            credit_popups = [p for p in credit_popups if p["age"] < 1.0]

            if player.game_over:
                credits_earned = score // 5
                high_scores_data = highscore.save_high_score("PLAYER", score)
                progress_data = progress.add_credits(progress_data, credits_earned)
                game_over_stats = {"score": score, "level": level, "credits_earned": credits_earned}
                state = STATE_GAME_OVER

        # =====================================================================
        # 3. DRAW
        # =====================================================================
        if state in (STATE_PLAYING, STATE_PAUSED, STATE_POWERUP_SELECT):
            # The "world" (background + everything that can get hit) draws
            # onto its own surface first so a hit-stop/boss-phase/boss-kill
            # moment can shake just the world, not the HUD text on top of it.
            starfield.draw(world_surf)
            for enemy in enemies:
                enemy.draw(world_surf)
            for hazard in hazards:
                hazard.draw(world_surf)
            for coin in coins:
                coin.draw(world_surf)
            if boss is not None:
                boss.draw(world_surf)
            for bullet in bullets:
                bullet.draw(world_surf)
            for bullet in boss_bullets:
                bullet.draw(world_surf)
            for explosion in explosions:
                explosion.draw(world_surf)
            impact_particles.draw(world_surf)
            player.draw(world_surf)
            hint_surf = small_font.render(
                "Pinch: shoot | Fist: shield | Palm: EXTREME BOOST | Swipe: weapon | P: pause",
                True, settings.WHITE
            )
            hint_rect = hint_surf.get_rect(midtop=(settings.SCREEN_WIDTH // 2, 12))
            world_surf.blit(hint_surf, hint_rect)

            if world_shake_timer > 0 and world_shake_magnitude > 0:
                shake_amt = world_shake_magnitude * min(1.0, world_shake_timer / 0.08)
                shake_dx = random.uniform(-shake_amt, shake_amt)
                shake_dy = random.uniform(-shake_amt, shake_amt)
            else:
                shake_dx = shake_dy = 0.0
            screen.blit(world_surf, (shake_dx, shake_dy))

            hud.draw(screen, player, score, level, progress_data["credits"])

            for popup in credit_popups:
                progress_frac = popup["age"] / 1.0
                rise = progress_frac * 34
                alpha = max(0, int(255 * (1 - progress_frac)))
                popup_font = pygame.font.SysFont("consolas", 20, bold=True)
                popup_surf = popup_font.render(popup["text"], True, settings.GOLD)
                popup_surf.set_alpha(alpha)
                screen.blit(popup_surf, popup_surf.get_rect(
                    center=(popup["x"], popup["y"] - rise)
                ))

            if level_up_timer > 0:
                banner_font = pygame.font.SysFont("consolas", 48, bold=True)
                alpha = min(255, int(255 * (level_up_timer / 0.5))) if level_up_timer < 0.5 else 255
                banner_surf = banner_font.render(f"LEVEL {level}!", True, settings.GOLD)
                banner_surf.set_alpha(alpha)
                banner_rect = banner_surf.get_rect(center=(settings.SCREEN_WIDTH // 2, 160))
                screen.blit(banner_surf, banner_rect)

            if boss is not None:
                boss.draw_health_bar(screen, debug_font)

            if boss_intro_timer > 0:
                intro_font = pygame.font.SysFont("consolas", 44, bold=True)
                alpha = min(255, int(255 * (boss_intro_timer / 0.6))) if boss_intro_timer < 0.6 else 255
                intro_label = boss.label if boss is not None else "BOSS"
                intro_surf = intro_font.render(f"BOSS BATTLE -- {intro_label}", True, settings.GOLD)
                intro_surf.set_alpha(alpha)
                intro_rect = intro_surf.get_rect(center=(settings.SCREEN_WIDTH // 2, 210))
                glow = pygame.Surface((intro_rect.width + 30, intro_rect.height + 16), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*settings.NEON_BLUE, 50), glow.get_rect(), border_radius=10)
                glow.set_alpha(alpha)
                screen.blit(glow, (intro_rect.x - 15, intro_rect.y - 8))
                screen.blit(intro_surf, intro_rect)

            # DEBUG: numeric readout so we can see exactly what the game
            # thinks the target position is vs where the ship actually is.
            if debug_mode and index_fingertip_norm is not None:
                target_debug = (
                    f"target=({index_fingertip_norm[0]*settings.SCREEN_WIDTH:.0f},"
                    f"{index_fingertip_norm[1]*settings.SCREEN_HEIGHT:.0f})  "
                    f"ship=({player.x:.0f},{player.y:.0f})"
                )
                debug_surf = small_font.render(target_debug, True, settings.NEON_GREEN)
                debug_rect = debug_surf.get_rect(topright=(settings.SCREEN_WIDTH - 12, 40))
                screen.blit(debug_surf, debug_rect)

            if state == STATE_PAUSED:
                pause_screen.draw(screen, audio_manager, progress_data)

            if state == STATE_POWERUP_SELECT:
                powerup_screen.draw(screen)

        else:
            starfield.draw(screen)

            if state == STATE_MENU:
                main_menu.draw(screen)
            elif state == STATE_CONTROLS:
                controls_screen.draw(screen)
            elif state == STATE_HIGH_SCORES:
                high_scores_screen.draw(screen, high_scores_data)
            elif state == STATE_SETTINGS:
                settings_screen.draw(screen, audio_manager, progress_data, debug_mode, camera_preview_visible)
            elif state == STATE_HANGAR:
                hangar_screen.draw(screen, progress_data)
            elif state == STATE_GAME_OVER:
                game_over_screen.draw(screen, game_over_stats)

        # --- Camera preview box (toggle in Settings) ---
        if camera_preview_visible:
            pygame.draw.rect(screen, (10, 10, 25), preview_rect)
            pygame.draw.rect(screen, settings.NEON_BLUE, preview_rect, width=2)

            if not camera.connected:
                error_lines = ["CAMERA NOT FOUND", "Check webcam connection"]
                for i, line in enumerate(error_lines):
                    err_surf = small_font.render(line, True, settings.DANGER_RED)
                    err_rect = err_surf.get_rect(
                        center=(preview_rect.centerx, preview_rect.centery - 10 + i * 20)
                    )
                    screen.blit(err_surf, err_rect)
            elif camera_frame_for_display is not None:
                cam_surface = cv2_frame_to_pygame_surface(camera_frame_for_display)
                cam_surface = pygame.transform.smoothscale(
                    cam_surface, (PREVIEW_WIDTH, PREVIEW_HEIGHT)
                )
                screen.blit(cam_surface, preview_rect.topleft)

                status_text = f"{hand_count} HAND(S) DETECTED" if hand_count else "NO HAND DETECTED"
                status_color = settings.NEON_GREEN if hand_count else settings.DANGER_RED
                status_surf = small_font.render(status_text, True, status_color)
                status_rect = status_surf.get_rect(
                    midtop=(preview_rect.centerx, preview_rect.bottom + 4)
                )
                screen.blit(status_surf, status_rect)

                if current_gesture != "none":
                    gesture_label = current_gesture.replace("_", " ").upper()
                    gesture_surf = gesture_font.render(gesture_label, True, settings.GOLD)
                    gesture_rect = gesture_surf.get_rect(
                        midbottom=(preview_rect.centerx, preview_rect.top - 4)
                    )
                    screen.blit(gesture_surf, gesture_rect)

                # DEBUG: draw a crosshair on the preview at the EXACT point
                # currently driving ship movement, so it's obvious which
                # hand/point is being tracked at a glance.
                if debug_mode and index_fingertip_norm is not None:
                    marker_x = preview_rect.x + int(index_fingertip_norm[0] * PREVIEW_WIDTH)
                    marker_y = preview_rect.y + int(index_fingertip_norm[1] * PREVIEW_HEIGHT)
                    pygame.draw.circle(screen, settings.DANGER_RED, (marker_x, marker_y), 6, width=2)
                    pygame.draw.line(screen, settings.DANGER_RED, (marker_x - 10, marker_y), (marker_x + 10, marker_y), 1)
                    pygame.draw.line(screen, settings.DANGER_RED, (marker_x, marker_y - 10), (marker_x, marker_y + 10), 1)
            else:
                waiting_surf = small_font.render("Starting camera...", True, settings.WHITE)
                waiting_rect = waiting_surf.get_rect(center=preview_rect.center)
                screen.blit(waiting_surf, waiting_rect)

            label_surf = small_font.render("CAMERA FEED", True, settings.NEON_BLUE)
            screen.blit(label_surf, (preview_rect.x, preview_rect.y - 54))

        fps_text = debug_font.render(f"FPS: {clock.get_fps():.0f}  (F3: debug)", True, settings.NEON_GREEN)
        fps_rect = fps_text.get_rect(topright=(settings.SCREEN_WIDTH - 12, 10))
        screen.blit(fps_text, fps_rect)

        # --- Screen flash (Step 10): brief full-screen tint when hit ---
        if screen_flash_timer > 0 and screen_flash_start > 0:
            flash_alpha = 150 * (screen_flash_timer / screen_flash_start)
            draw_screen_flash(screen, flash_alpha, screen_flash_color)

        display_surf.fill((0, 0, 0))
        _scaled_rect, _ = get_scaled_rect(display_surf.get_size())
        _scaled_surf = pygame.transform.smoothscale(screen, _scaled_rect.size)
        display_surf.blit(_scaled_surf, _scaled_rect.topleft)
        pygame.display.flip()

    # =========================================================================
    # CLEANUP
    # =========================================================================
    camera.stop()
    hand_tracker.close()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        import datetime
        try:
            with open(settings.LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n--- Crash at {datetime.datetime.now().isoformat()} ---\n")
                f.write(traceback.format_exc())
            print(f"[FATAL] Game crashed. Details written to {settings.LOG_PATH}")
        except Exception:
            traceback.print_exc()
        raise