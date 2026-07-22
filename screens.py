import random

import pygame

import settings
import ships
import progress
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
            "SHOOT       -  Pinch (touch thumb + index tip together)",
            "SHIELD      -  Closed fist",
            "BOOST       -  Open palm: ramming speed for a few seconds",
            "               (invincible, destroys enemies on contact)",
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
        self.slider_rect = pygame.Rect(settings.SCREEN_WIDTH // 2 - 150, 260, 300, 10)
        self.dragging = False

    def _knob_rect(self, volume):
        x = self.slider_rect.x + int(volume * self.slider_rect.width)
        return pygame.Rect(x - 8, self.slider_rect.y - 6, 16, 22)

    def handle_event(self, event, audio_manager):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if (self.slider_rect.collidepoint(event.pos) or
                    self._knob_rect(audio_manager.volume).collidepoint(event.pos)):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            rel = (event.pos[0] - self.slider_rect.x) / self.slider_rect.width
            audio_manager.set_volume(rel)

    def draw(self, surface, audio_manager):
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
    def __init__(self):
        self.title_font = pygame.font.SysFont("consolas", 48, bold=True)
        cx = settings.SCREEN_WIDTH // 2
        self.buttons = [
            Button("RESUME", (cx, 300), "resume", width=240, height=54),
            Button("RESTART", (cx, 366), "restart", width=240, height=54),
            Button("SETTINGS", (cx, 432), "settings", width=240, height=54),
            Button("MAIN MENU", (cx, 498), "main_menu", width=240, height=54),
        ]

    def update(self, dt, mouse_pos):
        for b in self.buttons:
            b.update(dt, mouse_pos)

    def handle_click(self, mouse_pos):
        for b in self.buttons:
            if b.rect.collidepoint(mouse_pos):
                return b.action
        return None

    def draw(self, surface):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((5, 5, 20, 190))
        surface.blit(overlay, (0, 0))

        title = self.title_font.render("PAUSED", True, settings.NEON_BLUE)
        surface.blit(title, title.get_rect(center=(settings.SCREEN_WIDTH // 2, 190)))

        for b in self.buttons:
            b.draw(surface)


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