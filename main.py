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
from gesture import HandTracker, GestureRecognizer
from player import Player
from bullet import Bullet
import weapons
from enemy import spawn_random_enemy
from audio import AudioManager
import highscore
import progress
import ships
from screens import ControlsScreen, HighScoresScreen, SettingsScreen, HangarScreen
from utils import cv2_frame_to_pygame_surface

ENEMY_SPAWN_INTERVAL = 1.4
LEVEL_SCORE_STEP = 500


STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_CONTROLS = "controls"
STATE_HIGH_SCORES = "high_scores"
STATE_SETTINGS = "settings"
STATE_HANGAR = "hangar"

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
    audio_manager = AudioManager()
    high_scores_data = highscore.load_high_scores()

    camera = CameraManager()
    camera.start()
    hand_tracker = HandTracker(max_num_hands=2)
    gesture_recognizer = GestureRecognizer()

    state = STATE_MENU
    running = True
    debug_mode = True  # press F3 to toggle -- shows crosshair + coordinate readout
    bullets = []
    enemies = []
    enemy_spawn_timer = ENEMY_SPAWN_INTERVAL
    score = 0
    level = 1
    level_up_timer = 0.0

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

        # =====================================================================
        # 1. EVENTS
        # =====================================================================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state == STATE_PLAYING:
                        state = STATE_MENU
                        bullets = []
                        enemies = []
                        enemy_spawn_timer = ENEMY_SPAWN_INTERVAL
                    elif state in (STATE_CONTROLS, STATE_HIGH_SCORES, STATE_SETTINGS, STATE_HANGAR):
                        state = STATE_MENU
                    else:
                        running = False
                elif event.key == pygame.K_F3:
                    debug_mode = not debug_mode
                elif state == STATE_PLAYING and event.key in WEAPON_KEYS:
                    player.set_weapon(WEAPON_KEYS[event.key])

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if state == STATE_MENU:
                    action = main_menu.handle_click(mouse_pos)
                    if action == "play":
                        state = STATE_PLAYING
                        player = Player(progress_data["selected_ship"])
                        bullets = []
                        enemies = []
                        enemy_spawn_timer = ENEMY_SPAWN_INTERVAL
                        score = 0
                        level = 1
                        level_up_timer = 0.0
                    elif action == "exit":
                        running = False
                    elif action == "controls":
                        state = STATE_CONTROLS
                    elif action == "high_scores":
                        high_scores_data = highscore.load_high_scores()
                        state = STATE_HIGH_SCORES
                    elif action == "settings":
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
                    if settings_screen.handle_click(mouse_pos) == "back":
                        state = STATE_MENU
                elif state == STATE_HANGAR:
                    action, progress_data = hangar_screen.handle_click(mouse_pos, progress_data)
                    if action == "back":
                        state = STATE_MENU

            if state == STATE_SETTINGS:
                settings_screen.handle_event(event, audio_manager)

        # =====================================================================
        # 2. UPDATE -- figure out what's happening this frame
        # =====================================================================
        starfield.update(dt)
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
            if index_fingertip_norm is not None:
                target_x = index_fingertip_norm[0] * settings.SCREEN_WIDTH
                target_y = index_fingertip_norm[1] * settings.SCREEN_HEIGHT
            else:
                target_x, target_y = None, None
            player.update(dt, target_x, target_y)

            # --- Shooting: pinch fires, gated by the cooldown ---
            if current_gesture == "pinch" and player.can_shoot():
                nose_x, nose_y = player.get_nose_position()
                new_bullets = weapons.spawn_bullets(player.weapon_name, nose_x, nose_y)
                for b in new_bullets:
                    b.damage = max(1, round(b.damage * player.damage_mult))
                bullets.extend(new_bullets)
                player.trigger_shot()

            for bullet in bullets:
                bullet.update(dt)
            bullets = [b for b in bullets if b.alive]

            new_level = 1 + score // LEVEL_SCORE_STEP
            if new_level > level:
                level = new_level
                level_up_timer = 2.0
            level_up_timer = max(0.0, level_up_timer - dt)

            effective_spawn_interval = max(0.5, ENEMY_SPAWN_INTERVAL - 0.05 * (level - 1))
            enemy_spawn_timer -= dt
            if enemy_spawn_timer <= 0:
                enemies.append(spawn_random_enemy(level))
                enemy_spawn_timer = effective_spawn_interval

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
                            score += enemy.score_value
                        break
            bullets = [b for b in bullets if b.alive]

            for enemy in enemies:
                if enemy.get_rect().colliderect(player.get_rect()) and player.invincible_timer <= 0:
                    player.take_damage(enemy.collision_damage)
                    enemy.alive = False
            enemies = [e for e in enemies if e.alive]

            if player.game_over:
                high_scores_data = highscore.save_high_score("PLAYER", score)
                progress_data = progress.add_credits(progress_data, score // 5)
                state = STATE_MENU
                bullets = []
                enemies = []
                enemy_spawn_timer = ENEMY_SPAWN_INTERVAL
                score = 0
                level = 1
                level_up_timer = 0.0
                player = Player(progress_data["selected_ship"])

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
            settings_screen.draw(screen, audio_manager)
        elif state == STATE_HANGAR:
            hangar_screen.draw(screen, progress_data)
        elif state == STATE_PLAYING:
            for enemy in enemies:
                enemy.draw(screen)
            for bullet in bullets:
                bullet.draw(screen)
            player.draw(screen)
            hint_surf = small_font.render(
                "Index finger: fly  |  Pinch: shoot  |  1-6: weapon  |  ESC: Menu", True, settings.WHITE
            )
            hint_rect = hint_surf.get_rect(midtop=(settings.SCREEN_WIDTH // 2, 12))
            screen.blit(hint_surf, hint_rect)

            hud_surf = debug_font.render(
                f"HP: {player.health}/{player.max_health}   SCORE: {score}   LEVEL: {level}   "
                f"CR: {progress_data['credits']}   WEAPON: {weapons.get_label(player.weapon_name)}",
                True, settings.GOLD
            )
            screen.blit(hud_surf, (10, 68))

            if level_up_timer > 0:
                banner_font = pygame.font.SysFont("consolas", 48, bold=True)
                alpha = min(255, int(255 * (level_up_timer / 0.5))) if level_up_timer < 0.5 else 255
                banner_surf = banner_font.render(f"LEVEL {level}!", True, settings.GOLD)
                banner_surf.set_alpha(alpha)
                banner_rect = banner_surf.get_rect(center=(settings.SCREEN_WIDTH // 2, 160))
                screen.blit(banner_surf, banner_rect)

            # DEBUG: numeric readout so we can see exactly what the game
            # thinks the target position is vs where the ship actually is.
            if debug_mode and index_fingertip_norm is not None:
                target_debug = (
                    f"target=({index_fingertip_norm[0]*settings.SCREEN_WIDTH:.0f},"
                    f"{index_fingertip_norm[1]*settings.SCREEN_HEIGHT:.0f})  "
                    f"ship=({player.x:.0f},{player.y:.0f})"
                )
                debug_surf = small_font.render(target_debug, True, settings.NEON_GREEN)
                screen.blit(debug_surf, (10, 40))

        # --- Camera preview box (always visible) ---
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
        screen.blit(fps_text, (10, 10))

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