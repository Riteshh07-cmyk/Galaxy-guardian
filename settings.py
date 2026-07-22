"""
settings.py
-----------
Every "magic number" in the game lives here: screen size, colors, FPS,
file paths, gameplay tuning values, etc.

Why this matters: instead of hunting through 10 files to change the
window size or a color, you change it once, here, and everything
that imports settings.py picks it up automatically.
"""

# ---------------------------------------------------------------------------
# WINDOW / DISPLAY
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
GAME_TITLE = "Galaxy Guardian"
FPS = 60

# ---------------------------------------------------------------------------
# COLORS (R, G, B)
# ---------------------------------------------------------------------------
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_SPACE = (5, 5, 20)        # background base color
NEON_BLUE = (0, 200, 255)
NEON_PURPLE = (150, 60, 220)
NEON_GREEN = (0, 255, 140)
DANGER_RED = (255, 60, 60)
GOLD = (255, 210, 60)

# ---------------------------------------------------------------------------
# FOLDER PATHS
# ---------------------------------------------------------------------------
ASSET_DIR = "assets"
PLAYER_ASSET_DIR = f"{ASSET_DIR}/player"
ENEMY_ASSET_DIR = f"{ASSET_DIR}/enemy"
BOSS_ASSET_DIR = f"{ASSET_DIR}/boss"
BACKGROUND_ASSET_DIR = f"{ASSET_DIR}/background"
EFFECTS_ASSET_DIR = f"{ASSET_DIR}/effects"
SOUND_ASSET_DIR = f"{ASSET_DIR}/sounds"
FONT_ASSET_DIR = f"{ASSET_DIR}/fonts"
UI_ASSET_DIR = f"{ASSET_DIR}/ui"

MUSIC_MENU_PATH = f"{SOUND_ASSET_DIR}/menu_theme.wav"
MUSIC_ACTION_PATH = f"{SOUND_ASSET_DIR}/action_theme.wav"
DEFAULT_MUSIC_VOLUME = 0.6

DIFFICULTY_LEVELS = {
    "easy":      {"label": "EASY",      "spawn_mult": 1.35, "speed_mult": 0.80, "score_mult": 0.8},
    "normal":    {"label": "NORMAL",    "spawn_mult": 1.00, "speed_mult": 1.00, "score_mult": 1.0},
    "hard":      {"label": "HARD",      "spawn_mult": 0.75, "speed_mult": 1.20, "score_mult": 1.3},
    "nightmare": {"label": "NIGHTMARE", "spawn_mult": 0.55, "speed_mult": 1.50, "score_mult": 1.6},
}
DIFFICULTY_ORDER = ["easy", "normal", "hard", "nightmare"]

# ---------------------------------------------------------------------------
# CAMERA / GESTURE (used starting Step 3)
# ---------------------------------------------------------------------------
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# ---------------------------------------------------------------------------
# GAMEPLAY (placeholders we will use in later steps)
# ---------------------------------------------------------------------------
PLAYER_START_HEALTH = 100
PLAYER_START_LIVES = 3
SHOOT_COOLDOWN_SECONDS = 0.2
SHIELD_DURATION_SECONDS = 5
SHIELD_COOLDOWN_SECONDS = 10
BOOST_DURATION_SECONDS = 3
BOOST_COOLDOWN_SECONDS = 6
BOOST_SPEED_MULTIPLIER = 2.6      # ship movement speed while boosting
BOOST_BG_SPEED_MULTIPLIER = 3.5   # starfield/background scroll speed while boosting