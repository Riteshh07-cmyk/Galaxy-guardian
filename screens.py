import math
import random

import pygame

import settings
import ships
import progress
import powerups
from menu import Button


class BackScreenBase:
    def __init__(self, title):
        self.title_font = pygame.font.SysFont("consolas", 42, bold=True)
        self.body_font = pygame.font.SysFont("consolas", 20)
        self.title = title
        self.back_button = Button("BACK", (140, settings.SCREEN_HEIGHT - 60), "back", width=160, height=50)

    def update(self, dt, mouse_pos):
        self.back_button.update(dt, mouse_pos)

    def handle_click(self, mouse_pos):
        if self.back_button.rect.collidepoint(mouse_pos):
            return "back"
        return None

    def draw_frame(self, surface):
        t = self.title_font.render(self.title, True, settings.NEON_BLUE)
        surface.blit(t, t.get_rect(center=(settings.SCREEN_WIDTH // 2, 80)))
        self.back_button.draw(surface)


class ControlsScreen(BackScreenBase):
    def __init__(self):
        super().__init__("CONTROLS")
        self.lines = [
            "MOVE        -  Move your index finger",
            "SHOOT       -  Pinch (thumb + index tip together)",
            "SHIELD      -  Closed fist",
            "EXTREME BOOST -  Open palm (hold)",
            "CHANGE WPN  -  Fast horizontal swipe",
            "",
            "KEYBOARD BACKUP:",
            "  Arrow Keys / WASD  -  Move",
            "  Space              -  Shoot",
            "  P                  -  Pause",
            "  ESC                -  Menu",
        ]

    def draw(self, surface):
        self.draw_frame(surface)
        y = 190
        for line in self.lines:
            s = self.body_font.render(line, True, settings.WHITE)
            surface.blit(s, (settings.SCREEN_WIDTH // 2 - 240, y))
            y += 42


class HighScoresScreen(BackScreenBase):
    def __init__(self):
        super().__init__("HIGH SCORES")

    def draw(self, surface, scores):
        self.draw_frame(surface)
        y = 180
        if not scores:
            s = self.body_font.render("No scores yet -- go play!", True, settings.WHITE)
            surface.blit(s, s.get_rect(center=(settings.SCREEN_WIDTH // 2, y)))
            return
        header = self.body_font.render(f"{'#':<4}{'NAME':<12}{'SCORE':<10}{'DIFF':<10}DATE", True, settings.NEON_GREEN)
        surface.blit(header, (settings.SCREEN_WIDTH // 2 - 260, y))
        y += 36
        for i, entry in enumerate(scores[:10]):
            line = f"{i + 1:<4}{entry['name']:<12}{entry['score']:<10}{entry['difficulty']:<10}{entry['date']}"
            s = self.body_font.render(line, True, settings.WHITE)
            surface.blit(s, (settings.SCREEN_WIDTH // 2 - 260, y))
            y += 34


class SettingsScreen(BackScreenBase):
    def __init__(self):
        super().__init__("SETTINGS")
        self.slider_rect = pygame.Rect(settings.SCREEN_WIDTH // 2 - 150, 220, 300, 10)
        self.dragging = False
        self._pre_mute_volume = settings.DEFAULT_MUSIC_VOLUME

        self.mute_button = Button("MUTE", (self.slider_rect.right + 110, self.slider_rect.centery),
                                   "mute", width=110, height=36)

        # --- Difficulty selector -- picks from settings.DIFFICULTY_LEVELS,
        # which was already defined but never actually wired up anywhere. ---
        self.difficulty_buttons = []
        cx = settings.SCREEN_WIDTH // 2
        self.diff_y = 360
        gap = 190
        count = len(settings.DIFFICULTY_ORDER)
        start_x = cx - gap * (count - 1) / 2
        for i, diff_key in enumerate(settings.DIFFICULTY_ORDER):
            label = settings.DIFFICULTY_LEVELS[diff_key]["label"]
            btn = Button(label, (start_x + i * gap, self.diff_y), diff_key, width=170, height=52)
            self.difficulty_buttons.append(btn)

        # --- Extra toggles ---
        toggle_y = 480
        self.debug_toggle_button = Button("DEBUG OVERLAY", (cx - 160, toggle_y), "toggle_debug", width=260, height=44)
        self.camera_toggle_button = Button("CAMERA PREVIEW", (cx + 160, toggle_y), "toggle_camera", width=260, height=44)
        self.fullscreen_toggle_button = Button("DISPLAY MODE", (cx, toggle_y + 56), "toggle_fullscreen", width=260, height=44)

    def _knob_rect(self, volume):
        x = self.slider_rect.x + int(volume * self.slider_rect.width)
        return pygame.Rect(x - 8, self.slider_rect.y - 6, 16, 22)

    def handle_event(self, event, audio_manager):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if (self.slider_rect.collidepoint(event.pos) or
                    self._knob_rect(audio_manager.volume).collidepoint(event.pos)):
                self.dragging = True
            elif self.mute_button.rect.collidepoint(event.pos):
                if audio_manager.volume > 0:
                    self._pre_mute_volume = audio_manager.volume
                    audio_manager.set_volume(0.0)
                else:
                    audio_manager.set_volume(self._pre_mute_volume or 0.6)
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            rel = (event.pos[0] - self.slider_rect.x) / self.slider_rect.width
            audio_manager.set_volume(rel)

    def update(self, dt, mouse_pos):
        super().update(dt, mouse_pos)
        self.mute_button.update(dt, mouse_pos)
        for btn in self.difficulty_buttons:
            btn.update(dt, mouse_pos)
        self.debug_toggle_button.update(dt, mouse_pos)
        self.camera_toggle_button.update(dt, mouse_pos)
        self.fullscreen_toggle_button.update(dt, mouse_pos)

    def handle_click(self, mouse_pos, progress_data, debug_mode, camera_preview_visible):
        if self.back_button.rect.collidepoint(mouse_pos):
            return "back", progress_data, debug_mode, camera_preview_visible
        for btn in self.difficulty_buttons:
            if btn.rect.collidepoint(mouse_pos):
                progress_data["difficulty"] = btn.action
                progress.save_progress(progress_data)
                return None, progress_data, debug_mode, camera_preview_visible
        if self.debug_toggle_button.rect.collidepoint(mouse_pos):
            debug_mode = not debug_mode
            return None, progress_data, debug_mode, camera_preview_visible
        if self.camera_toggle_button.rect.collidepoint(mouse_pos):
            camera_preview_visible = not camera_preview_visible
            return None, progress_data, debug_mode, camera_preview_visible
        if self.fullscreen_toggle_button.rect.collidepoint(mouse_pos):
            progress_data["fullscreen"] = not progress_data.get("fullscreen", False)
            progress.save_progress(progress_data)
            return "toggle_fullscreen", progress_data, debug_mode, camera_preview_visible
        return None, progress_data, debug_mode, camera_preview_visible

    def draw(self, surface, audio_manager, progress_data, debug_mode, camera_preview_visible):
        self.draw_frame(surface)

        label = self.body_font.render("MUSIC VOLUME", True, settings.WHITE)
        surface.blit(label, (self.slider_rect.x, self.slider_rect.y - 34))

        pygame.draw.rect(surface, (60, 60, 60), self.slider_rect, border_radius=4)
        fill_rect = pygame.Rect(
            self.slider_rect.x, self.slider_rect.y,
            int(self.slider_rect.width * audio_manager.volume), self.slider_rect.height
        )
        pygame.draw.rect(surface, settings.NEON_GREEN, fill_rect, border_radius=4)
        pygame.draw.rect(surface, settings.WHITE, self._knob_rect(audio_manager.volume), border_radius=4)

        pct = int(audio_manager.volume * 100)
        pct_s = self.body_font.render(f"{pct}%", True, settings.GOLD)
        surface.blit(pct_s, (self.slider_rect.right + 20, self.slider_rect.y - 6))

        self.mute_button.label = "UNMUTE" if audio_manager.volume <= 0 else "MUTE"
        self.mute_button.draw(surface)

        diff_label = self.body_font.render("DIFFICULTY", True, settings.WHITE)
        surface.blit(diff_label, (settings.SCREEN_WIDTH // 2 - diff_label.get_width() // 2, 300))

        current_diff = progress_data.get("difficulty", "normal")
        for btn in self.difficulty_buttons:
            btn.draw(surface)
            if btn.action == current_diff:
                pygame.draw.rect(surface, settings.NEON_GREEN, btn.rect.inflate(10, 10), width=3, border_radius=14)

        diff_cfg = settings.DIFFICULTY_LEVELS.get(current_diff, settings.DIFFICULTY_LEVELS["normal"])
        hint = f"Slower enemies, gentler spawns" if diff_cfg["speed_mult"] < 1 else \
               f"Faster enemies, denser spawns" if diff_cfg["speed_mult"] > 1 else \
               f"The standard challenge"
        hint_s = pygame.font.SysFont("consolas", 16).render(hint, True, (180, 200, 220))
        hint_y = self.difficulty_buttons[0].rect.bottom + 26 if self.difficulty_buttons else self.diff_y + 60
        surface.blit(hint_s, hint_s.get_rect(center=(settings.SCREEN_WIDTH // 2, hint_y)))

        is_fullscreen = progress_data.get("fullscreen", False)
        self.debug_toggle_button.label = f"DEBUG OVERLAY: {'ON' if debug_mode else 'OFF'}"
        self.camera_toggle_button.label = f"CAMERA PREVIEW: {'ON' if camera_preview_visible else 'OFF'}"
        self.fullscreen_toggle_button.label = f"DISPLAY MODE: {'FULLSCREEN' if is_fullscreen else 'WINDOWED'}"
        self.debug_toggle_button.draw(surface)
        self.camera_toggle_button.draw(surface)
        self.fullscreen_toggle_button.draw(surface)
        for btn, on in (
            (self.debug_toggle_button, debug_mode),
            (self.camera_toggle_button, camera_preview_visible),
            (self.fullscreen_toggle_button, is_fullscreen),
        ):
            border = settings.NEON_GREEN if on else (90, 90, 90)
            pygame.draw.rect(surface, border, btn.rect, width=2, border_radius=12)


class HangarScreen(BackScreenBase):
    def __init__(self):
        super().__init__("HANGAR")
        self.small_font = pygame.font.SysFont("consolas", 14)
        self.status_font = pygame.font.SysFont("consolas", 14, bold=True)
        self.card_rects = {}
        cols = 3
        card_w, card_h = 230, 210
        gap_x, gap_y = 25, 25
        start_x = settings.SCREEN_WIDTH // 2 - (cols * card_w + (cols - 1) * gap_x) // 2
        start_y = 150
        for i, ship_id in enumerate(ships.SHIP_ORDER):
            col = i % cols
            row = i // cols
            x = start_x + col * (card_w + gap_x)
            y = start_y + row * (card_h + gap_y)
            self.card_rects[ship_id] = pygame.Rect(x, y, card_w, card_h)

    def handle_click(self, mouse_pos, progress_data):
        if self.back_button.rect.collidepoint(mouse_pos):
            return "back", progress_data
        for ship_id, rect in self.card_rects.items():
            if rect.collidepoint(mouse_pos):
                cfg = ships.SHIP_TYPES[ship_id]
                progress_data, ok = progress.unlock_or_select_ship(progress_data, ship_id, cfg["cost"])
                return None, progress_data
        return None, progress_data

    def draw(self, surface, progress_data):
        self.draw_frame(surface)
        credit_s = self.body_font.render(f"CREDITS: {progress_data['credits']}", True, settings.GOLD)
        surface.blit(credit_s, (settings.SCREEN_WIDTH - 260, 34))

        for ship_id, rect in self.card_rects.items():
            cfg = ships.SHIP_TYPES[ship_id]
            unlocked = ship_id in progress_data["unlocked_ships"]
            selected = progress_data["selected_ship"] == ship_id

            if selected:
                border_color = settings.NEON_GREEN
            elif unlocked:
                border_color = settings.NEON_BLUE
            else:
                border_color = (90, 90, 90)

            pygame.draw.rect(surface, (15, 15, 35), rect, border_radius=10)
            pygame.draw.rect(surface, border_color, rect, width=3, border_radius=10)

            name_s = self.body_font.render(cfg["label"], True, settings.WHITE)
            surface.blit(name_s, (rect.x + 14, rect.y + 12))

            pygame.draw.polygon(surface, cfg["color"], [
                (rect.centerx, rect.y + 55), (rect.centerx - 22, rect.y + 100), (rect.centerx + 22, rect.y + 100)
            ])
            pygame.draw.polygon(surface, cfg["wing_color"], [
                (rect.centerx - 30, rect.y + 90), (rect.centerx - 10, rect.y + 75), (rect.centerx - 10, rect.y + 100)
            ])
            pygame.draw.polygon(surface, cfg["wing_color"], [
                (rect.centerx + 30, rect.y + 90), (rect.centerx + 10, rect.y + 75), (rect.centerx + 10, rect.y + 100)
            ])

            desc_s = self.small_font.render(cfg["description"], True, (200, 200, 200))
            surface.blit(desc_s, (rect.x + 14, rect.y + 118))

            stats = f"SPD {cfg['speed_mult']:.1f}x  HP {cfg['health_mult']:.1f}x  DMG {cfg['damage_mult']:.1f}x"
            stats_s = self.small_font.render(stats, True, (160, 200, 255))
            surface.blit(stats_s, (rect.x + 14, rect.y + 140))

            if selected:
                status, color = "SELECTED", settings.NEON_GREEN
            elif unlocked:
                status, color = "OWNED - CLICK TO USE", settings.NEON_BLUE
            else:
                status, color = f"LOCKED - {cfg['cost']} CR", settings.DANGER_RED
            status_s = self.status_font.render(status, True, color)
            surface.blit(status_s, (rect.x + 14, rect.bottom - 28))


class PauseScreen:
    """The ESC/P pause overlay. Besides the usual Resume/Restart/Settings/
    Main Menu actions, it embeds a couple of "quick settings" (music
    volume + difficulty) directly in the panel so players don't have to
    leave the pause screen just to nudge those -- the full Settings
    screen (with the extra toggles) is still one click away too."""

    def __init__(self):
        self.title_font = pygame.font.SysFont("consolas", 46, bold=True)
        self.small_label_font = pygame.font.SysFont("consolas", 15, bold=True)
        self.hint_font = pygame.font.SysFont("consolas", 15)

        self.panel_rect = pygame.Rect(0, 0, 760, 540)
        self.panel_rect.center = (settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 + 20)

        cx = self.panel_rect.centerx
        top = self.panel_rect.y

        self.buttons = [
            Button("RESUME", (cx, top + 120), "resume", width=230, height=50),
            Button("RESTART", (cx, top + 176), "restart", width=230, height=50),
            Button("SETTINGS", (cx, top + 232), "settings", width=230, height=50),
            Button("MAIN MENU", (cx, top + 288), "main_menu", width=230, height=50),
        ]

        # --- Embedded quick settings ---
        self.divider_y = top + 328
        self.slider_rect = pygame.Rect(self.panel_rect.x + 70, top + 372, 260, 10)
        self.dragging = False
        self._pre_mute_volume = settings.DEFAULT_MUSIC_VOLUME
        self.mute_button = Button("MUTE", (self.slider_rect.right + 100, self.slider_rect.centery),
                                   "mute", width=100, height=32)

        self.difficulty_buttons = []
        diff_y = top + 430
        gap = 145
        count = len(settings.DIFFICULTY_ORDER)
        start_x = cx - gap * (count - 1) / 2
        for i, diff_key in enumerate(settings.DIFFICULTY_ORDER):
            label = settings.DIFFICULTY_LEVELS[diff_key]["label"]
            btn = Button(label, (start_x + i * gap, diff_y), diff_key, width=130, height=38)
            self.difficulty_buttons.append(btn)
        self.diff_y = diff_y

        # --- Cool animation bits ---
        self.time_elapsed = 0.0
        random.seed(11)
        self.particles = [
            {
                "x": random.uniform(self.panel_rect.x + 10, self.panel_rect.right - 10),
                "y": random.uniform(self.panel_rect.y + 10, self.panel_rect.bottom - 10),
                "vy": random.uniform(-14, -4),
                "phase": random.uniform(0, math.tau),
                "size": random.uniform(1.2, 2.6),
            }
            for _ in range(26)
        ]
        random.seed()

    def _knob_rect(self, volume):
        x = self.slider_rect.x + int(volume * self.slider_rect.width)
        return pygame.Rect(x - 8, self.slider_rect.y - 6, 16, 22)

    def handle_event(self, event, audio_manager):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if (self.slider_rect.collidepoint(event.pos) or
                    self._knob_rect(audio_manager.volume).collidepoint(event.pos)):
                self.dragging = True
            elif self.mute_button.rect.collidepoint(event.pos):
                if audio_manager.volume > 0:
                    self._pre_mute_volume = audio_manager.volume
                    audio_manager.set_volume(0.0)
                else:
                    audio_manager.set_volume(self._pre_mute_volume or 0.6)
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            rel = (event.pos[0] - self.slider_rect.x) / self.slider_rect.width
            audio_manager.set_volume(rel)

    def update(self, dt, mouse_pos):
        self.time_elapsed += dt
        for b in self.buttons:
            b.update(dt, mouse_pos)
        self.mute_button.update(dt, mouse_pos)
        for btn in self.difficulty_buttons:
            btn.update(dt, mouse_pos)

        for p in self.particles:
            p["y"] += p["vy"] * dt
            if p["y"] < self.panel_rect.y:
                p["y"] = self.panel_rect.bottom
                p["x"] = random.uniform(self.panel_rect.x + 10, self.panel_rect.right - 10)

    def handle_click(self, mouse_pos, progress_data):
        for b in self.buttons:
            if b.rect.collidepoint(mouse_pos):
                return b.action, progress_data
        for btn in self.difficulty_buttons:
            if btn.rect.collidepoint(mouse_pos):
                progress_data["difficulty"] = btn.action
                progress.save_progress(progress_data)
                return None, progress_data
        return None, progress_data

    def draw(self, surface, audio_manager, progress_data):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((5, 5, 20, 190))
        surface.blit(overlay, (0, 0))

        # --- Pulsing neon border color, cycling blue -> purple -> green ---
        hue_t = self.time_elapsed * 0.6
        c1, c2 = settings.NEON_BLUE, settings.NEON_PURPLE
        mix = 0.5 + 0.5 * math.sin(hue_t)
        border_color = tuple(int(c1[i] + (c2[i] - c1[i]) * mix) for i in range(3))

        panel_glow = pygame.Surface((self.panel_rect.width + 50, self.panel_rect.height + 50), pygame.SRCALPHA)
        pygame.draw.rect(panel_glow, (*border_color, 45), panel_glow.get_rect(), border_radius=28)
        surface.blit(panel_glow, (self.panel_rect.x - 25, self.panel_rect.y - 25))

        pygame.draw.rect(surface, (10, 10, 28), self.panel_rect, border_radius=22)
        pygame.draw.rect(surface, border_color, self.panel_rect, width=3, border_radius=22)

        # --- Drifting particle motes inside the panel ---
        clip = surface.get_clip()
        surface.set_clip(self.panel_rect)
        for p in self.particles:
            twinkle = 0.4 + 0.6 * abs(math.sin(self.time_elapsed * 3 + p["phase"]))
            alpha = int(160 * twinkle)
            pygame.draw.circle(surface, (*settings.WHITE, alpha), (int(p["x"]), int(p["y"])), p["size"])
        surface.set_clip(clip)

        # --- Bobbing, glowing title ---
        bob = math.sin(self.time_elapsed * 1.8) * 5
        title_pos = (self.panel_rect.centerx, self.panel_rect.y + 62 + bob)
        glow_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for offset in range(6, 0, -2):
            glow_text = self.title_font.render("PAUSED", True, (*border_color, 30))
            glow_rect = glow_text.get_rect(center=title_pos)
            glow_surf.blit(glow_text, (glow_rect.x - offset, glow_rect.y))
            glow_surf.blit(glow_text, (glow_rect.x + offset, glow_rect.y))
        surface.blit(glow_surf, (0, 0))
        title_surf = self.title_font.render("PAUSED", True, settings.WHITE)
        surface.blit(title_surf, title_surf.get_rect(center=title_pos))

        for b in self.buttons:
            b.draw(surface)

        # --- Divider ---
        pygame.draw.line(
            surface, (*border_color, 120) if False else border_color,
            (self.panel_rect.x + 50, self.divider_y), (self.panel_rect.right - 50, self.divider_y), width=1
        )
        quick_label = self.small_label_font.render("QUICK SETTINGS", True, (170, 190, 230))
        surface.blit(quick_label, quick_label.get_rect(center=(self.panel_rect.centerx, self.divider_y + 18)))

        # --- Volume slider ---
        vol_label = self.small_label_font.render("MUSIC VOLUME", True, settings.WHITE)
        surface.blit(vol_label, (self.slider_rect.x, self.slider_rect.y - 22))
        pygame.draw.rect(surface, (60, 60, 60), self.slider_rect, border_radius=4)
        fill_rect = pygame.Rect(
            self.slider_rect.x, self.slider_rect.y,
            int(self.slider_rect.width * audio_manager.volume), self.slider_rect.height
        )
        pygame.draw.rect(surface, settings.NEON_GREEN, fill_rect, border_radius=4)
        pygame.draw.rect(surface, settings.WHITE, self._knob_rect(audio_manager.volume), border_radius=4)
        self.mute_button.label = "UNMUTE" if audio_manager.volume <= 0 else "MUTE"
        self.mute_button.draw(surface)

        # --- Difficulty pills ---
        diff_label = self.small_label_font.render("DIFFICULTY", True, settings.WHITE)
        surface.blit(diff_label, diff_label.get_rect(center=(self.panel_rect.centerx, self.diff_y - 32)))
        current_diff = progress_data.get("difficulty", "normal")
        for btn in self.difficulty_buttons:
            btn.draw(surface)
            if btn.action == current_diff:
                pygame.draw.rect(surface, settings.NEON_GREEN, btn.rect.inflate(8, 8), width=2, border_radius=12)

        hint_s = self.hint_font.render("Press ESC to resume", True, (150, 160, 190))
        surface.blit(hint_s, hint_s.get_rect(center=(self.panel_rect.centerx, self.panel_rect.bottom - 22)))


class PowerupScreen:
    """Shown once, right after a boss dies. Presents 3 randomly-chosen
    upgrade cards (drawn from powerups.POWERUP_ORDER, which repeats fine
    since some effects stack) and applies whichever one gets clicked
    directly onto the live Player instance. main.py owns freezing
    gameplay while this is up -- this class only draws/reports clicks."""

    def __init__(self):
        self.title_font = pygame.font.SysFont("consolas", 34, bold=True)
        self.label_font = pygame.font.SysFont("consolas", 21, bold=True)
        self.desc_font = pygame.font.SysFont("consolas", 15)
        self.hint_font = pygame.font.SysFont("consolas", 15)
        self.time_elapsed = 0.0
        self.choices = []

        card_w, card_h = 260, 290
        gap = 40
        total_w = card_w * 3 + gap * 2
        start_x = settings.SCREEN_WIDTH // 2 - total_w // 2
        y = settings.SCREEN_HEIGHT // 2 - card_h // 2 + 40

        self.card_rects = [
            pygame.Rect(start_x + i * (card_w + gap), y, card_w, card_h)
            for i in range(3)
        ]
        self.hover_amounts = [0.0, 0.0, 0.0]

        random.seed(3)
        self.particles = [
            {
                "x": random.uniform(0, settings.SCREEN_WIDTH),
                "y": random.uniform(0, settings.SCREEN_HEIGHT),
                "vy": random.uniform(-12, -4),
                "phase": random.uniform(0, math.tau),
                "size": random.uniform(1.0, 2.4),
            }
            for _ in range(30)
        ]
        random.seed()

    def set_choices(self, choices):
        """Call this once, right when the reward screen is opened."""
        self.choices = choices
        self.time_elapsed = 0.0  # restart the card entrance animation
        self.hover_amounts = [0.0] * len(choices)

    def update(self, dt, mouse_pos):
        self.time_elapsed += dt
        for i, rect in enumerate(self.card_rects):
            if i >= len(self.hover_amounts):
                break
            hovered = rect.collidepoint(mouse_pos)
            target = 1.0 if hovered else 0.0
            self.hover_amounts[i] += (target - self.hover_amounts[i]) * min(1.0, 8.0 * dt)
        for p in self.particles:
            p["y"] += p["vy"] * dt
            if p["y"] < -10:
                p["y"] = settings.SCREEN_HEIGHT + 10
                p["x"] = random.uniform(0, settings.SCREEN_WIDTH)

    def handle_click(self, mouse_pos):
        """Returns the chosen powerup_id, or None if the click missed."""
        for i, rect in enumerate(self.card_rects):
            if i < len(self.choices) and rect.collidepoint(mouse_pos):
                return self.choices[i]
        return None

    def draw(self, surface):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((5, 5, 20, 205))
        surface.blit(overlay, (0, 0))

        for p in self.particles:
            twinkle = 0.4 + 0.6 * abs(math.sin(self.time_elapsed * 2.5 + p["phase"]))
            alpha = int(150 * twinkle)
            pygame.draw.circle(surface, (*settings.WHITE, alpha), (int(p["x"]), int(p["y"])), p["size"])

        title_bob = math.sin(self.time_elapsed * 1.6) * 4
        title_surf = self.title_font.render("BOSS DEFEATED -- CHOOSE YOUR REWARD", True, settings.GOLD)
        title_rect = title_surf.get_rect(center=(settings.SCREEN_WIDTH // 2, 150 + title_bob))
        glow = pygame.Surface((title_rect.width + 30, title_rect.height + 16), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*settings.GOLD, 35), glow.get_rect(), border_radius=10)
        surface.blit(glow, (title_rect.x - 15, title_rect.y - 8))
        surface.blit(title_surf, title_rect)

        for i, powerup_id in enumerate(self.choices):
            if i >= len(self.card_rects) or powerup_id not in powerups.POWERUPS:
                continue
            rect = self.card_rects[i]
            hover = self.hover_amounts[i] if i < len(self.hover_amounts) else 0.0
            cfg = powerups.POWERUPS[powerup_id]

            # Cards slide up + fade in, staggered by index -- so all 3
            # don't just pop in simultaneously.
            reveal_start = i * 0.12
            eased = min(1.0, max(0.0, (self.time_elapsed - reveal_start) / 0.4))
            eased = 1 - (1 - eased) ** 3
            y_offset = int((1 - eased) * 40)
            alpha = int(255 * eased)
            if alpha <= 0:
                continue

            draw_rect = rect.move(0, y_offset)
            scale = 1.0 + 0.035 * hover
            scaled_rect = draw_rect.inflate(
                int(draw_rect.width * (scale - 1)), int(draw_rect.height * (scale - 1))
            )

            base_color = settings.NEON_BLUE
            hover_color = settings.NEON_GREEN
            border_color = tuple(
                int(base_color[c] + (hover_color[c] - base_color[c]) * hover) for c in range(3)
            )

            if hover > 0.01:
                glow_surf = pygame.Surface((scaled_rect.width + 30, scaled_rect.height + 30), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*hover_color, int(70 * hover)), glow_surf.get_rect(), border_radius=18)
                surface.blit(glow_surf, (scaled_rect.x - 15, scaled_rect.y - 15))

            card_surf = pygame.Surface(scaled_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(card_surf, (15, 15, 35, alpha), card_surf.get_rect(), border_radius=14)
            pygame.draw.rect(card_surf, (*border_color, alpha), card_surf.get_rect(), width=3, border_radius=14)
            surface.blit(card_surf, scaled_rect.topleft)

            # Simple glowing badge icon -- a ringed dot, colored to match
            # the card's hover state, standing in for a per-upgrade icon.
            icon_center = (scaled_rect.centerx, scaled_rect.y + 58)
            icon_glow = pygame.Surface((70, 70), pygame.SRCALPHA)
            pygame.draw.circle(icon_glow, (*border_color, int(60 * (0.5 + 0.5 * abs(math.sin(self.time_elapsed * 3 + i))))), (35, 35), 30)
            surface.blit(icon_glow, (icon_center[0] - 35, icon_center[1] - 35))
            pygame.draw.circle(surface, border_color, icon_center, 24, width=3)
            pygame.draw.circle(surface, settings.WHITE, icon_center, 8)

            label_surf = self.label_font.render(cfg["label"], True, settings.WHITE)
            label_surf.set_alpha(alpha)
            label_rect = label_surf.get_rect(center=(scaled_rect.centerx, scaled_rect.y + 118))
            surface.blit(label_surf, label_rect)

            desc_surf = self.desc_font.render(cfg["description"], True, (200, 210, 230))
            desc_surf.set_alpha(alpha)
            desc_rect = desc_surf.get_rect(center=(scaled_rect.centerx, scaled_rect.y + 150))
            surface.blit(desc_surf, desc_rect)

            pick_surf = self.desc_font.render("CLICK TO SELECT", True, border_color if hover > 0.3 else (110, 120, 150))
            pick_surf.set_alpha(alpha)
            pick_rect = pick_surf.get_rect(center=(scaled_rect.centerx, scaled_rect.bottom - 24))
            surface.blit(pick_surf, pick_rect)

        hint_surf = self.hint_font.render("Click a card to choose your reward", True, (150, 160, 190))
        surface.blit(hint_surf, hint_surf.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT - 40)))


class GameOverScreen:
    def __init__(self):
        self.title_font = pygame.font.SysFont("consolas", 60, bold=True)
        self.label_font = pygame.font.SysFont("consolas", 22, bold=True)
        self.body_font = pygame.font.SysFont("consolas", 20)

        self.panel_rect = pygame.Rect(0, 0, 720, 440)
        self.panel_rect.center = (settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2)

        self.restart_rect = pygame.Rect(0, 0, 210, 60)
        self.menu_rect = pygame.Rect(0, 0, 210, 60)
        self.restart_rect.center = (self.panel_rect.centerx + 120, self.panel_rect.bottom - 70)
        self.menu_rect.center = (self.panel_rect.centerx - 120, self.panel_rect.bottom - 70)

        random.seed(7)  # fixed layout so skulls don't reshuffle every game over
        self.skulls = []
        for _ in range(7):
            sx = random.choice([
                random.randint(40, self.panel_rect.left - 30),
                random.randint(self.panel_rect.right + 30, settings.SCREEN_WIDTH - 40),
            ])
            sy = random.randint(60, settings.SCREEN_HEIGHT - 60)
            ssize = random.randint(40, 80)
            self.skulls.append((sx, sy, ssize))
        random.seed()

        self.mouse_pos = (-1, -1)

    def update(self, dt, mouse_pos):
        self.mouse_pos = mouse_pos

    def handle_click(self, mouse_pos):
        if self.restart_rect.collidepoint(mouse_pos):
            return "restart"
        if self.menu_rect.collidepoint(mouse_pos):
            return "main_menu"
        return None

    def _draw_skull(self, surface, cx, cy, size, color):
        head_rect = pygame.Rect(cx - size // 2, cy - size // 2, size, int(size * 0.8))
        pygame.draw.rect(surface, color, head_rect, border_radius=size // 4)
        eye_size = max(4, size // 5)
        pygame.draw.rect(surface, (8, 10, 30), (cx - size // 3, cy - size // 8, eye_size, eye_size))
        pygame.draw.rect(surface, (8, 10, 30), (cx + size // 3 - eye_size, cy - size // 8, eye_size, eye_size))
        bone_y = cy + size // 2
        pygame.draw.line(surface, color, (cx - size // 2, bone_y), (cx + size // 2, bone_y + size // 3), 4)
        pygame.draw.line(surface, color, (cx + size // 2, bone_y), (cx - size // 2, bone_y + size // 3), 4)

    def draw(self, surface, stats):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((6, 8, 30, 220))
        surface.blit(overlay, (0, 0))

        for sx, sy, ssize in self.skulls:
            self._draw_skull(surface, sx, sy, ssize, (45, 65, 150))

        glow_surf = pygame.Surface((self.panel_rect.width + 40, self.panel_rect.height + 40), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*settings.NEON_BLUE, 55), glow_surf.get_rect(), border_radius=26)
        surface.blit(glow_surf, (self.panel_rect.x - 20, self.panel_rect.y - 20))

        pygame.draw.rect(surface, (10, 16, 48), self.panel_rect, border_radius=18)
        pygame.draw.rect(surface, settings.NEON_BLUE, self.panel_rect, width=3, border_radius=18)

        title_surf = self.title_font.render("GAME OVER", True, (210, 245, 255))
        surface.blit(title_surf, title_surf.get_rect(center=(self.panel_rect.centerx, self.panel_rect.y + 70)))

        lines = [
            f"FINAL SCORE: {stats.get('score', 0)}",
            f"LEVEL REACHED: {stats.get('level', 1)}",
            f"CREDITS EARNED: +{stats.get('credits_earned', 0)}",
        ]
        y = self.panel_rect.y + 150
        for line in lines:
            s = self.body_font.render(line, True, settings.WHITE)
            surface.blit(s, s.get_rect(center=(self.panel_rect.centerx, y)))
            y += 32

        continue_s = self.label_font.render("CONTINUE?", True, settings.DANGER_RED)
        surface.blit(continue_s, continue_s.get_rect(center=(self.panel_rect.centerx, self.panel_rect.bottom - 130)))

        restart_hover = self.restart_rect.collidepoint(self.mouse_pos)
        pygame.draw.rect(surface, (255, 120, 95) if restart_hover else (225, 90, 70), self.restart_rect, border_radius=8)
        r_label = self.label_font.render("RESTART", True, settings.WHITE)
        surface.blit(r_label, r_label.get_rect(center=self.restart_rect.center))

        menu_hover = self.menu_rect.collidepoint(self.mouse_pos)
        pygame.draw.rect(surface, (22, 32, 75) if not menu_hover else (32, 46, 100), self.menu_rect, border_radius=8)
        pygame.draw.rect(surface, settings.NEON_BLUE, self.menu_rect, width=3, border_radius=8)
        m_label = self.label_font.render("MAIN MENU", True, settings.WHITE)
        surface.blit(m_label, m_label.get_rect(center=self.menu_rect.center))