import settings

SHIP_TYPES = {
    "guardian": {
        "label": "GUARDIAN", "cost": 0,
        "speed_mult": 1.0, "health_mult": 1.0, "fire_rate_mult": 1.0, "damage_mult": 1.0,
        "color": settings.NEON_BLUE, "wing_color": settings.NEON_PURPLE,
        "description": "Balanced starter ship.",
    },
    "interceptor": {
        "label": "INTERCEPTOR", "cost": 500,
        "speed_mult": 1.6, "health_mult": 0.75, "fire_rate_mult": 1.0, "damage_mult": 1.0,
        "color": (255, 220, 90), "wing_color": (200, 150, 40),
        "description": "Very fast, fragile.",
    },
    "juggernaut": {
        "label": "JUGGERNAUT", "cost": 800,
        "speed_mult": 0.65, "health_mult": 1.8, "fire_rate_mult": 0.85, "damage_mult": 1.2,
        "color": (150, 150, 160), "wing_color": (90, 90, 100),
        "description": "Slow tank, huge health.",
    },
    "phantom": {
        "label": "PHANTOM", "cost": 1200,
        "speed_mult": 1.15, "health_mult": 0.9, "fire_rate_mult": 1.6, "damage_mult": 1.0,
        "color": (150, 80, 220), "wing_color": (90, 40, 140),
        "description": "Rapid-fire specialist.",
    },
    "vindicator": {
        "label": "VINDICATOR", "cost": 1600,
        "speed_mult": 1.0, "health_mult": 1.2, "fire_rate_mult": 1.0, "damage_mult": 1.5,
        "color": (255, 60, 90), "wing_color": (140, 20, 40),
        "description": "Heavy damage dealer.",
    },
}

SHIP_ORDER = ["guardian", "interceptor", "juggernaut", "phantom", "vindicator"]