# ⚾ Monte Carlo Baseball Game Simulator

## Overview
This project is a full-season–style **Monte Carlo simulation** for modeling baseball game outcomes between two rosters — in this example, the *Toronto Blue Jays* and *Los Angeles Dodgers*.  
Each game is simulated plate appearance–by–plate appearance using **probabilistic outcomes** derived from hitter and pitcher matchup data.

The system blends **player-specific rates** with **context-aware bullpen and fatigue logic** to produce realistic outcomes across thousands of simulated games.

---

## 🎯 Core Features

### 1. Probabilistic Matchup Model
Each plate appearance (PA) outcome is drawn from combined hitter and pitcher probabilities:

- A **60/40 weighted average** between the hitter’s and pitcher’s outcome probabilities.  
- Matchups are **handedness-aware**, using batter and pitcher handedness (`bats`, `pit_hand`) to select the correct probability row.

Supported outcomes:  
`single`, `double`, `triple`, `hr`, `walk`, `so`, `out`, and `roe` (reached on error).

---

### 2. Pitcher Usage Model
Pitching behavior is governed by realistic stamina, fatigue, and decision-making rules.

#### 🧢 Starters
- Expected to face roughly **18–23 batters** before fatigue.  
- If pitching efficiently (≤ 2 earned runs), ~10–15% of starters can extend to **24–27 batters**.  
- Pulled early if:
  - 4+ runs allowed before 12 batters.  
  - 3+ runs allowed after 15 batters.  
- Gradual fatigue chance grows after ~19 batters faced.  
- Automatically removed once exceeding **27 batters faced**.

> 💡 *Result:* Starters behave like modern MLB usage — capable of 5–7 innings on good days, but vulnerable to quick hooks if struggling.

#### 🔥 Relievers
- Must face **at least 3 batters** unless ending an inning.  
- Assigned a random **usage cap (4–9 batters)**, representing different roles (short vs long relief).  
- Removed if:
  - 2+ earned runs allowed, or  
  - 2+ runners on base with ≥3 batters faced, or  
  - They hit their fatigue cap.  
- ~20% chance to face one extra batter beyond the cap (manager discretion).  
- May start a new inning, but won’t typically cross multiple innings without necessity.

> 💡 *Result:* Bullpen arms cycle dynamically, producing realistic reliever turnover, emergency call-ins, and bullpen exhaustion.

---

### 3. Game Simulation Loop
Each game progresses through 9+ innings:

- Offense and defense alternate through `sim_half()` until a winner emerges.  
- Extra innings automatically extend until one team leads after a complete frame.  
- Every PA outcome updates the inning score, player boxscore, and pitcher stats.

At the end of each game, five outputs are returned:

```python
score, hit_df, pit_df, log_df, box_df
```

| Return | Description |
|:-------|:-------------|
| `score` | Final game score (dict by team) |
| `hit_df` | Batter-level boxscore |
| `pit_df` | Pitcher-level boxscore |
| `log_df` | Pitching change log |
| `box_df` | Inning-by-inning summary with `team`, `inning_1..18`, `R`, `H`, `E` (E includes ROE events) |

---

### 4. Monte Carlo Loop
You can simulate thousands of games efficiently:

```python
n_sims = 2000
for i in range(n_sims):
    score, hit_df, pit_df, log_df, box_df = simulate_game(...)
```

Each run stores:

- `hitting_boxscores` → all batter boxscores  
- `pitching_boxscores` → all pitcher lines  
- `inning_boxscores` → inning-by-inning team scores (with `team` and ROE counted in `E`)  
- `results_df` → summary of winners and final scores  

---

### 5. Export and Analysis
After all simulations, results are merged into unified datasets:

- `simulation_results_summary.csv`  
- `all_inning_boxscores.csv`  
- `all_inning_boxscores.xlsx`  

Boxscore files include both top and bottom halves (with `team` column) and support filtering by:

- Highest-scoring games  
- 3-HR hitter performances  
- Specific player conditions (e.g., Ohtani + Freeman no-hit wins)  
- Strikeout milestones (e.g., 18+ K games)

---

## 🧮 Example Analysis (Post-Sim)

```python
# Highest combined scores
results_df.assign(combined_runs = results_df["Blue Jays"] + results_df["Dodgers"]) \
    .sort_values("combined_runs", ascending=False).head()

# 3-HR performances (per-game hit_df with HR >= 3)
three_homer_games = [
    (gid, df[df["HR"] >= 3])
    for gid, df in hitting_boxscores.items()
    if not df[df["HR"] >= 3].empty
]

# Ohtani & Freeman's team wins while both never reach base
def did_not_reach_base(df, player):
    if player not in df["Player"].values: 
        return True
    row = df[df["Player"] == player].iloc[0]
    return (row.get("H",0) + row.get("BB",0)) == 0

candidate_games = []
for gid, df in hitting_boxscores.items():
    away = results_df.loc[results_df["game_id"] == gid, "Blue Jays"].values[0]
    home = results_df.loc[results_df["game_id"] == gid, "Dodgers"].values[0]
    winner = "Dodgers" if home > away else "Blue Jays"
    if winner == "Dodgers":
        if did_not_reach_base(df[df["Team"]=="Dodgers"], "Shohei Ohtani") and \
           did_not_reach_base(df[df["Team"]=="Dodgers"], "Freddie Freeman"):
            candidate_games.append(gid)

# 18+ strikeout starts
eighteen_k_starts = [
    (gid, pdf[(pdf["K"] >= 18) & (pdf["IP"] >= 6)]) 
    for gid, pdf in pitching_boxscores.items()
    if not pdf[(pdf["K"] >= 18) & (pdf["IP"] >= 6)].empty
]
```

Or visualize run-differential distributions:

```python
import seaborn as sns
sns.histplot(results_df["Blue Jays"] - results_df["Dodgers"], bins=30)
```

---

## ⚙️ Output Example

**all_inning_boxscores.csv**

| game_id | team | inning_1 | inning_2 | inning_3 | inning_4 | inning_5 | inning_6 | inning_7 | inning_8 | inning_9 | inning_10 | inning_11 | R | H | E |
|:---------|:-----|:----------|:----------|:----------|:----------|:----------|:----------|:----------|:----------|:----------|:-----------|:-----------|:--:|:--:|:--:|
| Game_1 | Blue Jays | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 6 | 0 |
| Game_1 | Dodgers   | 0 | 1 | 0 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 4 | 7 | 0 |

> **Note:** `E` includes **ROE** events credited to the defense (i.e., reached on error results).

---

## 🧱 Project Structure
```
ws_2025_monte_carlo/
│
├── sim/
│   ├── __init__.py
│   ├── game.py            # full simulation logic (starter/reliever usage, ROE→E, inning box)
│   ├── player.py          # Player and Pitcher classes
│   ├── team.py            # Lineup, bullpen, reserves management
│   ├── load_data.py       # Data ingestion from CSV/SQL
│
├── data/
│   ├── hitter_probs.csv
│   ├── pitcher_probs.csv
│
├── run_simulations.py     # Main simulation loop
├── analyze_sim_results.py # Post-run analysis
└── README.md
```

---

## 📈 Typical Runtime

| Simulation Count | Est. Runtime (modern laptop) |
|:-----------------|:------------------------------|
| 500 games | ≈ 1–2 min |
| 2,000 games | ≈ 4–6 min |
| 10,000 games | ≈ 20+ min |

---

## 🧩 Future Enhancements
- Dynamic **manager AI** with bullpen-preservation logic  
- Weather / park effects and neutralization factors  
- Full **season standings and WAR600** tracking  
- Player-fatigue carry-over between games  
