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
            "SHOOT       -  Pinch thumb + index finger",
            "SHIELD      -  Closed fist",
            "BOMB        -  Open both hands",
            "PAUSE       -  Palm facing camera",
            "SWITCH WPN  -  Number keys 1-6 (testing)",
            "MENU/BACK   -  ESC",
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