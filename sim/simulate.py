import pandas as pd
import copy
from .game import simulate_game
from .team import Team

def run_simulations(n_sims, team1, team2, hitter_probs, pitcher_probs, verbose=False):
    """Run n_sims games and return results as a DataFrame."""
    results = []

    for i in range(n_sims):
        # Make deep copies so lineups, bullpen, and stats reset
        t1 = copy.deepcopy(team1)
        t2 = copy.deepcopy(team2)

        # Reset the bullpen index and lineup
        t1.lineup_idx = 0
        t2.lineup_idx = 0
        t1.runs = 0
        t2.runs = 0

        # Explicitly reset bullpen stamina (if added later)
        for p in t1.bullpen:
            p.batters_faced = 0
        for p in t2.bullpen:
            p.batters_faced = 0

        # Run a fresh game
        score = simulate_game(t1, t2, hitter_probs, pitcher_probs, verbose=verbose)
        results.append(score)

    df = pd.DataFrame(results)
    df["winner"] = df.apply(lambda x: team1.name if x[team1.name] > x[team2.name] else team2.name, axis=1)
    return df
