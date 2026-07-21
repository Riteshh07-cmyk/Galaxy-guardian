import json
import os

PROGRESS_PATH = "progress.json"

DEFAULT_PROGRESS = {
    "credits": 0,
    "unlocked_ships": ["guardian"],
    "selected_ship": "guardian",
}


def load_progress():
    if not os.path.isfile(PROGRESS_PATH):
        return dict(DEFAULT_PROGRESS)
    try:
        with open(PROGRESS_PATH, "r") as f:
            data = json.load(f)
        for key, val in DEFAULT_PROGRESS.items():
            data.setdefault(key, val)
        return data
    except Exception as e:
        print(f"[progress] failed to load: {e}")
        return dict(DEFAULT_PROGRESS)


def save_progress(data):
    try:
        with open(PROGRESS_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[progress] failed to save: {e}")


def add_credits(data, amount):
    data["credits"] += amount
    save_progress(data)
    return data


def unlock_or_select_ship(data, ship_id, cost):
    if ship_id in data["unlocked_ships"]:
        data["selected_ship"] = ship_id
        save_progress(data)
        return data, True
    if data["credits"] >= cost:
        data["credits"] -= cost
        data["unlocked_ships"].append(ship_id)
        data["selected_ship"] = ship_id
        save_progress(data)
        return data, True
    return data, False