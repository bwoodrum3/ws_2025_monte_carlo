class Player:
    """Generic player class for hitters (batter data)."""

    def __init__(self, name, hand, probs=None, contact=0.0, power=0.0, speed=0.0):
        self.name = name          # full_name from DB/CSV
        self.hand = hand          # 'L', 'R', or 'S'
        self.probs = probs or {}  # dict of outcome probabilities

        # Optional advanced attributes
        self.contact = contact
        self.power = power
        self.speed = speed

    def __repr__(self):
        return (
            f"Player({self.name}, {self.hand}, "
            f"contact={self.contact:.1f}, power={self.power:.1f}, speed={self.speed:.1f})"
        )


class Pitcher:
    def __init__(self, name, hand, dra_minus=100, dra_minus_L=None, dra_minus_R=None, probs=None):
        self.name = name
        self.hand = hand

        # Probabilities (optional, e.g., for matchup-based simulation)
        self.probs = probs or {}

        # Performance metrics (lower is better)
        self.dra_minus = dra_minus
        self.dra_minus_L = dra_minus_L if dra_minus_L is not None else dra_minus
        self.dra_minus_R = dra_minus_R if dra_minus_R is not None else dra_minus

        # Track in-game stats
        self.ip = 0
        self.er = 0
        self.r = 0
        self.k = 0
        self.bb = 0
        self.hr = 0
        self.batters_faced = 0  # fatigue or substitution tracking

    def fatigue(self):
        """Optional: can expand to affect substitution logic"""
        return False  # handled externally in game.py

    def __repr__(self):
        return (
            f"Pitcher({self.name}, {self.hand}, "
            f"DRA-={self.dra_minus}, L={self.dra_minus_L}, R={self.dra_minus_R})"
        )



