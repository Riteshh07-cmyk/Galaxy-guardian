"""
upgrades.py
-----------
UPGRADE: permanent, credit-purchased ship upgrades ("the Armory").

Unlike powerups.py (temporary, chosen once per run after a boss fight),
these are permanent -- bought with the same credits earned from runs,
stored in progress.json under progress_data["upgrades"], and applied
every time a new Player is created (see player.py).

Each upgrade has a small number of levels. Cost grows per level so early
levels are cheap and later ones are a real credit sink -- exactly what a
huge stockpiled credit balance from grinding runs should be spent on.
"""

UPGRADE_DEFS = {
    "hull": {
        "label": "HULL PLATING",
        "description": "+8% max health per level",
        "max_level": 5,
        "base_cost": 400,
        "cost_growth": 1.6,
    },
    "damage": {
        "label": "WEAPON DAMAGE",
        "description": "+6% bullet damage per level",
        "max_level": 5,
        "base_cost": 500,
        "cost_growth": 1.6,
    },
    "firerate": {
        "label": "FIRE RATE",
        "description": "+6% fire rate per level",
        "max_level": 5,
        "base_cost": 500,
        "cost_growth": 1.6,
    },
    "shield": {
        "label": "SHIELD CAPACITOR",
        "description": "-6% shield cooldown per level",
        "max_level": 5,
        "base_cost": 450,
        "cost_growth": 1.6,
    },
}
UPGRADE_ORDER = ["hull", "damage", "firerate", "shield"]


def cost_for_level(upgrade_id, next_level):
    """Cost to go from (next_level - 1) -> next_level, i.e. the price of
    buying that level right now (1-indexed: buying your first level in
    an upgrade passes next_level=1)."""
    cfg = UPGRADE_DEFS[upgrade_id]
    return int(cfg["base_cost"] * (cfg["cost_growth"] ** (next_level - 1)))


def get_level(progress_data, upgrade_id):
    return progress_data.get("upgrades", {}).get(upgrade_id, 0)


def is_maxed(progress_data, upgrade_id):
    return get_level(progress_data, upgrade_id) >= UPGRADE_DEFS[upgrade_id]["max_level"]


def buy_upgrade(progress_data, upgrade_id):
    """Attempts to buy the next level of the given upgrade. Returns
    (progress_data, success). Saving to disk is the caller's job (screens
    already save progress_data after most actions, same pattern as
    unlock_or_select_ship)."""
    upgrades = progress_data.setdefault("upgrades", {})
    current_level = upgrades.get(upgrade_id, 0)
    cfg = UPGRADE_DEFS[upgrade_id]

    if current_level >= cfg["max_level"]:
        return progress_data, False

    cost = cost_for_level(upgrade_id, current_level + 1)
    if progress_data["credits"] < cost:
        return progress_data, False

    progress_data["credits"] -= cost
    upgrades[upgrade_id] = current_level + 1
    return progress_data, True


def apply_upgrades_to_player(player, progress_data):
    """Called once, right after a Player is constructed. Applies every
    purchased upgrade level as a permanent multiplier on top of whatever
    the selected ship already grants."""
    upgrades = progress_data.get("upgrades", {})

    hull_level = upgrades.get("hull", 0)
    if hull_level:
        mult = 1.0 + 0.08 * hull_level
        player.max_health = int(player.max_health * mult)
        player.health = player.max_health

    damage_level = upgrades.get("damage", 0)
    if damage_level:
        player.damage_mult *= 1.0 + 0.06 * damage_level

    firerate_level = upgrades.get("firerate", 0)
    if firerate_level:
        rate_mult = 1.0 + 0.06 * firerate_level
        player.fire_rate_mult *= rate_mult
        player.shoot_cooldown /= rate_mult

    shield_level = upgrades.get("shield", 0)
    if shield_level:
        player.shield_cooldown *= (1.0 - 0.06 * shield_level)