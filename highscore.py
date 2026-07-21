import json
import os
import datetime

HS_PATH = "highscores.json"


def load_high_scores():
    if not os.path.isfile(HS_PATH):
        return []
    try:
        with open(HS_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[highscore] failed to load: {e}")
        return []


def save_high_score(name, score, difficulty="Normal"):
    scores = load_high_scores()
    scores.append({
        "name": name,
        "score": score,
        "difficulty": difficulty,
        "date": datetime.date.today().isoformat(),
    })
    scores.sort(key=lambda e: e["score"], reverse=True)
    scores = scores[:10]
    try:
        with open(HS_PATH, "w") as f:
            json.dump(scores, f, indent=2)
    except Exception as e:
        print(f"[highscore] failed to save: {e}")
    return scores