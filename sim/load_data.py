import pandas as pd
from sim.player import Player, Pitcher


def load_hitters(csv_path: str):
    """Load hitter probabilities from CSV and return Player objects."""
    df = pd.read_csv(csv_path)
    players = []

    for _, row in df.iterrows():
        probs = {
            "out": row["out_rate_pred"],
            "so": row["so_rate_pred"],
            "bb": row["bb_rate_pred"],
            "hbp": row["hbp_rate_pred"],
            "roe": row["roe_rate_pred"],
            "single": row["single_rate_pred"],
            "double": row["double_rate_pred"],
            "triple": row["triple_rate_pred"],
            "hr": row["hr_rate_pred"],
        }

        # normalize to ensure they sum to 1.0
        total = sum(probs.values())
        probs = {k: v / total for k, v in probs.items()}

        player = Player(
            name=row["full_name"],
            hand=row["bats"],   # hitter batting hand
            probs=probs,
        )

        # NEW: add team info for later filtering
        player.team = row.get("team", None)

        players.append(player)

    return players


def load_pitchers(csv_path: str):
    """Load pitcher probabilities from CSV and return Pitcher objects."""
    df = pd.read_csv(csv_path)
    pitchers = []

    for _, row in df.iterrows():
        probs = {
            "out": row["out_rate_pred"],
            "so": row["so_rate_pred"],
            "bb": row["bb_rate_pred"],
            "hbp": row["hbp_rate_pred"],
            "roe": row["roe_rate_pred"],
            "single": row["single_rate_pred"],
            "double": row["double_rate_pred"],
            "triple": row["triple_rate_pred"],
            "hr": row["hr_rate_pred"],
        }

        # normalize
        total = sum(probs.values())
        probs = {k: v / total for k, v in probs.items()}

        pitcher = Pitcher(
            name=row["full_name"],
            hand=row["pit_hand"],  # pitcher throwing hand
            probs=probs,
        )

        # NEW: attach team abbreviation (e.g., TOR / LAD)
        pitcher.team = row.get("team", None)

        pitchers.append(pitcher)

    return pitchers
