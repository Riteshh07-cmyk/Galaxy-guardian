"""
weapons.py
----------
STEP 8: Weapon types and bullet spawn patterns.

Each weapon is just a config (cooldown, color, bullet speed) plus a
"pattern function" that decides how many bullets to create and at what
angles when you fire once. This keeps bullet.py completely generic --
it doesn't know or care which weapon made it.

Progressive unlocking (per the original design doc) will hook into this
later via player.set_weapon(name) -- for now, all weapons are available
immediately so we can test and tune them. Number keys 1-6 switch weapons
for testing purposes.
"""

import math

import settings
from bullet import Bullet


BASE_BULLET_SPEED = 780.0


def _straight_pattern(x, y, count, spacing, color, speed=BASE_BULLET_SPEED,
                       width=5, height=18, damage=1):
    """Fires `count` bullets side-by-side, all traveling straight up."""
    bullets = []
    total_width = spacing * (count - 1)
    start_x = x - total_width / 2
    for i in range(count):
        bx = start_x + i * spacing
        bullets.append(Bullet(bx, y, vx=0, vy=-speed, width=width, height=height,
                               color=color, damage=damage))
    return bullets


def _spread_pattern(x, y, count, spread_degrees, color, speed=BASE_BULLET_SPEED,
                     width=5, height=16, damage=1):
    """Fires `count` bullets fanned out across a total angle of spread_degrees,
    centered straight up (angle 0)."""
    bullets = []
    if count == 1:
        angles = [0.0]
    else:
        half = spread_degrees / 2
        angles = [
            -half + (spread_degrees * i / (count - 1))
            for i in range(count)
        ]
    for angle_deg in angles:
        angle_rad = math.radians(angle_deg)
        vx = speed * math.sin(angle_rad)
        vy = -speed * math.cos(angle_rad)
        bullets.append(Bullet(x, y, vx=vx, vy=vy, width=width, height=height,
                               color=color, damage=damage))
    return bullets


# ---------------------------------------------------------------------------
# WEAPON DEFINITIONS
# ---------------------------------------------------------------------------
# cooldown: seconds between shots (lower = faster fire rate)
# spawn_fn: called as spawn_fn(nose_x, nose_y) -> list[Bullet]

WEAPON_TYPES = {
    "normal": {
        "label": "NORMAL LASER",
        "cooldown": 0.20,
        "spawn_fn": lambda x, y: _straight_pattern(x, y, count=1, spacing=0, color=settings.NEON_GREEN),
    },
    "double": {
        "label": "DOUBLE LASER",
        "cooldown": 0.22,
        "spawn_fn": lambda x, y: _straight_pattern(x, y, count=2, spacing=16, color=settings.NEON_BLUE),
    },
    "triple": {
        "label": "TRIPLE LASER",
        "cooldown": 0.26,
        "spawn_fn": lambda x, y: _straight_pattern(x, y, count=3, spacing=14, color=settings.NEON_PURPLE),
    },
    "spread": {
        "label": "SPREAD SHOT",
        "cooldown": 0.32,
        "spawn_fn": lambda x, y: _spread_pattern(x, y, count=5, spread_degrees=50, color=settings.GOLD),
    },
    "rapid": {
        "label": "RAPID FIRE",
        "cooldown": 0.08,
        "spawn_fn": lambda x, y: _straight_pattern(
            x, y, count=1, spacing=0, color=(255, 240, 120), speed=900, width=3, height=14, damage=1
        ),
    },
    "plasma": {
        "label": "PLASMA BEAM",
        "cooldown": 0.40,
        "spawn_fn": lambda x, y: _straight_pattern(
            x, y, count=1, spacing=0, color=(255, 60, 200), speed=560, width=14, height=30, damage=3
        ),
    },
}

# Order used when cycling weapons with number keys / future gesture switching
WEAPON_ORDER = ["normal", "double", "triple", "spread", "rapid", "plasma"]


def spawn_bullets(weapon_name, nose_x, nose_y):
    """Fires the given weapon once from position (nose_x, nose_y),
    returning the list of Bullet objects it created."""
    weapon = WEAPON_TYPES.get(weapon_name, WEAPON_TYPES["normal"])
    return weapon["spawn_fn"](nose_x, nose_y)


def get_cooldown(weapon_name):
    weapon = WEAPON_TYPES.get(weapon_name, WEAPON_TYPES["normal"])
    return weapon["cooldown"]


def get_label(weapon_name):
    weapon = WEAPON_TYPES.get(weapon_name, WEAPON_TYPES["normal"])
    return weapon["label"]