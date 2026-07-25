"""
zones.py
--------
Groups levels into themed "zones" so the game doesn't feel like one flat
difficulty ramp. Every ZONE_LEVEL_SPAN levels (aligned with the boss
cadence in main.py) the player enters a new zone: a re-tinted background
and a different mix of enemy types. After looping through the whole
roster once, it starts over -- but main.py scales enemy stats by level
regardless, so a repeat zone still feels tougher than last time.
"""

ZONE_LEVEL_SPAN = 3  # levels per zone -- matches BOSS_LEVEL_INTERVAL in main.py

ZONES = [
    {
        "name": "NEBULA BELT",
        "space_color": (5, 5, 20),
        "star_tint": (255, 255, 255),
        "planet_colors": [(150, 60, 220), (0, 200, 255), (200, 100, 60)],
        "enemy_weights": {
            "drone": 3, "fighter": 2, "tank": 1,
            "interceptor": 1, "kamikaze": 1, "stealth": 1,
        },
    },
    {
        "name": "ASTEROID GRAVEYARD",
        "space_color": (12, 8, 6),
        "star_tint": (255, 235, 210),
        "planet_colors": [(150, 100, 60), (120, 90, 70), (170, 130, 90)],
        "enemy_weights": {
            "drone": 1, "fighter": 2, "tank": 3,
            "interceptor": 1, "kamikaze": 2, "stealth": 1,
        },
    },
    {
        "name": "ICE SECTOR",
        "space_color": (4, 10, 20),
        "star_tint": (210, 240, 255),
        "planet_colors": [(120, 220, 255), (180, 230, 255), (90, 160, 220)],
        "enemy_weights": {
            "drone": 1, "fighter": 1, "tank": 1,
            "interceptor": 3, "kamikaze": 1, "stealth": 3,
        },
    },
    {
        "name": "THE CORE",
        "space_color": (18, 4, 4),
        "star_tint": (255, 200, 190),
        "planet_colors": [(255, 80, 80), (220, 60, 40), (255, 140, 60)],
        "enemy_weights": {
            "drone": 1, "fighter": 2, "tank": 2,
            "interceptor": 2, "kamikaze": 3, "stealth": 2,
        },
    },
]


def zone_for_level(level):
    """Returns (zone_dict, zone_index, loop_count) for the given level.
    loop_count is how many full passes through the roster we've made --
    useful later if you want repeat zones to escalate further."""
    index = ((level - 1) // ZONE_LEVEL_SPAN) % len(ZONES)
    loop = ((level - 1) // ZONE_LEVEL_SPAN) // len(ZONES)
    return ZONES[index], index, loop