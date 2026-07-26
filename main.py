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
from hud import HUD, draw_screen_flash
from audio import AudioManager
import highscore
import progress
import ships
from screens import ControlsScreen, HighScoresScreen, SettingsScreen, HangarScreen, PauseScreen, GameOverScreen
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

    screen = pygame.display.set_mode(
        (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
    )
    clock = pygame.time.Clock()
    debug_font = pygame.font.SysFont("consolas", 20)
    small_font = pygame.font.SysFont("consolas", 16)
    gesture_font = pygame.font.SysFont("consolas", 22, bold=True)

    starfield = Starfield()
    main_menu = MainMenu()
    progress_data = progress.load_progress()
    player = Player(progress_data["selected_ship"])
    controls_screen = ControlsScreen()
    high_scores_screen = HighScoresScreen()
    settings_screen = SettingsScreen()
    hangar_screen = HangarScreen()
    pause_screen = PauseScreen()
    game_over_screen = GameOverScreen()
    hud = HUD()
    audio_manager = AudioManager()
    high_scores_data = highscore.load_high_scores()
    settings_return_state = STATE_MENU
    game_over_stats = {}

    camera = CameraManager()
    camera.start()
    hand_tracker = HandTracker(max_num_hands=2)
    gesture_recognizer = GestureRecognizer()
    swipe_detector = SwipeDetector()

    def make_new_run():
        fresh_player = Player(progress_data["selected_ship"])
        return fresh_player, [], [], [], [], ENEMY_SPAWN_INTERVAL, 0, 1, 0.0, None, [], 0, 0.0

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
        mouse_pos = pygame.mouse.get_pos()
        screen_flash_timer = max(0.0, screen_flash_timer - dt)
        hud.update(dt)

        # =====================================================================
        # 1. EVENTS
        # =====================================================================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

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
                    else:
                        running = False
                elif event.key == pygame.K_p:
                    if state == STATE_PLAYING:
                        state = STATE_PAUSED
                    elif state == STATE_PAUSED:
                        state = STATE_PLAYING
                elif event.key == pygame.K_F3:
                    debug_mode = not debug_mode
                elif state == STATE_PLAYING and event.key in WEAPON_KEYS:
                    player.set_weapon(WEAPON_KEYS[event.key])

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if state == STATE_MENU:
                    action = main_menu.handle_click(mouse_pos)
                    if action == "play":
                        state = STATE_PLAYING
                        player, bullets, enemies, hazards, explosions, enemy_spawn_timer, score, level, level_up_timer, boss, boss_bullets, boss_spawn_index, boss_intro_timer = make_new_run()
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
                elif state == STATE_HANGAR:
                    action, progress_data = hangar_screen.handle_click(mouse_pos, progress_data)
                    if action == "back":
                        state = STATE_MENU
                elif state == STATE_PAUSED:
                    action, progress_data = pause_screen.handle_click(mouse_pos, progress_data)
                    if action == "resume":
                        state = STATE_PLAYING
                    elif action == "restart":
                        player, bullets, enemies, hazards, explosions, enemy_spawn_timer, score, level, level_up_timer, boss, boss_bullets, boss_spawn_index, boss_intro_timer = make_new_run()
                        state = STATE_PLAYING
                    elif action == "settings":
                        settings_return_state = STATE_PAUSED
                        state = STATE_SETTINGS
                    elif action == "main_menu":
                        state = STATE_MENU
                elif state == STATE_GAME_OVER:
                    action = game_over_screen.handle_click(mouse_pos)
                    if action == "restart":
                        player, bullets, enemies, hazards, explosions, enemy_spawn_timer, score, level, level_up_timer, boss, boss_bullets, boss_spawn_index, boss_intro_timer = make_new_run()
                        state = STATE_PLAYING
                    elif action == "main_menu":
                        state = STATE_MENU

            if state == STATE_SETTINGS:
                settings_screen.handle_event(event, audio_manager)
            elif state == STATE_PAUSED:
                pause_screen.handle_event(event, audio_manager)

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
            player.update(dt, target_x, target_y, kb_dx, kb_dy, boost_requested)

            # --- Shooting: pinch gesture OR Space, gated by cooldown ---
            if (current_gesture == "pinch" or keys_held[pygame.K_SPACE]) and player.can_shoot():
                nose_x, nose_y = player.get_nose_position()
                new_bullets = weapons.spawn_bullets(player.weapon_name, nose_x, nose_y)
                for b in new_bullets:
                    b.damage = max(1, round(b.damage * player.damage_mult))
                bullets.extend(new_bullets)
                player.trigger_shot()

            # --- Shield: fist gesture ---
            if current_gesture == "fist" and player.can_activate_shield():
                player.activate_shield()

            # --- Weapon switch: fast horizontal swipe ---
            swipe_x = index_fingertip_norm[0] if index_fingertip_norm is not None else None
            swipe_direction = swipe_detector.update(dt, swipe_x)
            if swipe_direction == "right":
                player.cycle_weapon(1)
            elif swipe_direction == "left":
                player.cycle_weapon(-1)

            for bullet in bullets:
                bullet.update(dt)
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
                hazard.update(dt)
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
                    elif was_shielded:
                        screen_flash_timer = screen_flash_start = SCREEN_FLASH_BLOCK_DURATION
                        screen_flash_color = settings.NEON_BLUE
            hazards = [h for h in hazards if h.alive]

            # --- Boss update + bullets ---
            if boss is not None:
                fired = boss.update(dt, player.x, player.y)
                boss_bullets.extend(fired)

            for bb in boss_bullets:
                bb.update(dt)
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
                    elif was_shielded:
                        screen_flash_timer = screen_flash_start = SCREEN_FLASH_BLOCK_DURATION
                        screen_flash_color = settings.NEON_BLUE
            boss_bullets = [b for b in boss_bullets if b.alive]

            for enemy in enemies:
                enemy.update(dt, player.x, player.y)
            enemies = [e for e in enemies if e.alive and not e.is_offscreen()]

            for bullet in bullets:
                for enemy in enemies:
                    if not enemy.alive:
                        continue
                    if bullet.get_rect().colliderect(enemy.get_rect()):
                        enemy.take_damage(bullet.damage)
                        bullet.alive = False
                        if not enemy.alive:
                            score += int(enemy.score_value * diff_cfg["score_mult"])
                            explosions.append(Explosion(enemy.x, enemy.y, color=enemy.color))
                        break
            bullets = [b for b in bullets if b.alive]

            if boss is not None:
                for bullet in bullets:
                    if bullet.alive and bullet.get_rect().colliderect(boss.get_rect()):
                        boss.take_damage(bullet.damage)
                        bullet.alive = False
                bullets = [b for b in bullets if b.alive]

                if not boss.alive:
                    score += int(boss.score_value * diff_cfg["score_mult"])
                    explosions.append(Explosion(boss.x, boss.y, color=boss.core_color, big=True))
                    boss_bullets.clear()
                    boss = None
                    player.trigger_victory_effect()

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
                    elif was_shielded:
                        screen_flash_timer = screen_flash_start = SCREEN_FLASH_BLOCK_DURATION
                        screen_flash_color = settings.NEON_BLUE
            enemies = [e for e in enemies if e.alive]

            for explosion in explosions:
                explosion.update(dt)
            explosions = [e for e in explosions if e.alive]

            if player.game_over:
                credits_earned = score // 5
                high_scores_data = highscore.save_high_score("PLAYER", score)
                progress_data = progress.add_credits(progress_data, credits_earned)
                game_over_stats = {"score": score, "level": level, "credits_earned": credits_earned}
                state = STATE_GAME_OVER

        # =====================================================================
        # 3. DRAW
        # =====================================================================
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
        elif state in (STATE_PLAYING, STATE_PAUSED):
            for enemy in enemies:
                enemy.draw(screen)
            for hazard in hazards:
                hazard.draw(screen)
            if boss is not None:
                boss.draw(screen)
            for bullet in bullets:
                bullet.draw(screen)
            for bullet in boss_bullets:
                bullet.draw(screen)
            for explosion in explosions:
                explosion.draw(screen)
            player.draw(screen)
            hint_surf = small_font.render(
                "Pinch: shoot | Fist: shield | Palm: EXTREME BOOST | Swipe: weapon | P: pause",
                True, settings.WHITE
            )
            hint_rect = hint_surf.get_rect(midtop=(settings.SCREEN_WIDTH // 2, 12))
            screen.blit(hint_surf, hint_rect)

            hud.draw(screen, player, score, level, progress_data["credits"])

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

        pygame.display.flip()

    # =========================================================================
    # CLEANUP
    # =========================================================================
    camera.stop()
    hand_tracker.close()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()