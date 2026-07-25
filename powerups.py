"""
powerups.py
-----------
Permanent-for-the-current-run upgrades offered after a boss fight. These
never touch progress.json / credits -- like score and level, they reset
whenever a new run starts. Keeping this logic separate from player.py
means screens.py (which needs the labels/descriptions to draw the choice
cards) doesn't have to import the whole Player class.
"""

POWERUPS = {
    "rapid_fire": {
        "label": "RAPID FIRE MODULE",
        "description": "+25% fire rate",
    },
    "vitality": {
        "label": "VITALITY CORE",
        "description": "+25 max health, fully healed",
    },
    "armor_plating": {
        "label": "ARMOR PLATING",
        "description": "-15% damage taken (stacks)",
    },
    "quick_shield": {
        "label": "SHIELD CAPACITOR",
        "description": "-30% shield cooldown",
    },
    "overcharge": {
        "label": "WEAPON OVERCHARGE",
        "description": "+20% bullet damage",
    },
}
POWERUP_ORDER = list(POWERUPS.keys())


def apply_powerup(player, powerup_id):
    """Applies the named powerup's effect directly to a live Player
    instance. Called once, right when the player picks a reward card."""
    if powerup_id == "rapid_fire":
        player.fire_rate_mult *= 1.25
        player.shoot_cooldown /= 1.25
    elif powerup_id == "vitality":
        player.max_health += 25
        player.health = player.max_health
    elif powerup_id == "armor_plating":
        player.damage_reduction = min(0.6, player.damage_reduction + 0.15)
    elif powerup_id == "quick_shield":
        player.shield_cooldown *= 0.7
    elif powerup_id == "overcharge":
        player.damage_mult *= 1.2