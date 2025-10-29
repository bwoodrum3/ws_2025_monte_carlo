import numpy as np
import pandas as pd
import random

# -------------------------
# Probability + baserunning
# -------------------------

def get_matchup_row(df, batter_hand, pitcher_hand):
    """Return the correct row for a given batter/pitcher handedness matchup."""
    if batter_hand == "S":
        batter_hand = "L" if pitcher_hand == "R" else "R"
    subset = df.loc[(df["bats"] == batter_hand) & (df["pit_hand"] == pitcher_hand)]
    if subset.empty:
        subset = df.loc[df["bats"] == batter_hand]
        if subset.empty:
            subset = df
    return subset.iloc[0]


def simulate_pa(batter, pitcher, hitter_probs, pitcher_probs):
    """Simulate one PA with a 60/40 hitter/pitcher weighting."""
    h_row = get_matchup_row(hitter_probs, batter.hand, pitcher.hand)
    p_row = get_matchup_row(pitcher_probs, batter.hand, pitcher.hand)

    outcomes = ["single", "double", "triple", "hr", "walk", "so", "out", "roe"]
    valid_outcomes = [o for o in outcomes if o in h_row and o in p_row]
    probs = np.array([0.6 * h_row[o] + 0.4 * p_row[o] for o in valid_outcomes], dtype=float)
    probs /= probs.sum()
    return np.random.choice(valid_outcomes, p=probs)

# -------------------------
# Pitcher usage rules
# -------------------------

def should_pull_pitcher(pitcher, bf, runs_allowed, runners_on,
                        starter=True, bf_cap=None, emergency=False, outs_this_inning=0):
    # --- Starters ---
    if starter:
        if runs_allowed >= 4 and bf < 12:
            return True
        if bf >= 15 and runs_allowed >= 3:
            return True
        cap = getattr(pitcher, "stamina_cap", random.randint(18, 23))
        if runs_allowed <= 2 and bf >= cap and random.random() < 0.15:
            cap = random.randint(24, 27)
        if bf >= 27:
            return True
        if bf >= cap:
            return True
        if bf >= 19:
            fatigue_chance = 0.04 + 0.01 * (bf - 19)
            if random.random() < fatigue_chance:
                return True
        return False

    # --- Relievers ---
    if not starter:
        if bf < 3 and not emergency:
            return False
        if bf_cap is None:
            bf_cap = random.randint(4, 9)
        if runs_allowed >= 2:
            return True
        if sum(runners_on) >= 2 and bf >= 3:
            return True
        if bf >= bf_cap:
            return True
        if bf >= bf_cap - 1 and random.random() < 0.2:
            return False
        return False


# -------------------------
# Main simulation
# -------------------------

def simulate_game(team1, team2, hitter_probs, pitcher_probs, verbose=False):
    """Simulate a 9-inning game with inning boxscore output."""
    away, home = team1, team2
    score = {away.name: 0, home.name: 0}
    starters = {away.name: away.get_pitcher().name, home.name: home.get_pitcher().name}

    for t in [away, home]:
        if t.starter in t.bullpen:
            t.bullpen.remove(t.starter)

    # Box + bullpen state
    hit_box, pit_box, outs_map, bf_map, runs_map = (
        {away.name: {}, home.name: {}},
        {away.name: {}, home.name: {}},
        {away.name: {}, home.name: {}},
        {away.name: {}, home.name: {}},
        {away.name: {}, home.name: {}},
    )
    pitch_log = []
    reliever_cap = {away.name: {}, home.name: {}}
    appearance_bf = {away.name: {}, home.name: {}}
    used_pitchers = {away.name: [], home.name: []}
    emergency_mode = {away.name: False, home.name: False}

    # NEW — inning-by-inning log + errors tracker
    inning_log = {away.name: [], home.name: []}
    team_errors = {away.name: 0, home.name: 0}

    # ------------------
    # Helper functions
    # ------------------
    def ensure_pitcher(team, name):
        pit_box[team].setdefault(name, {"IP": 0, "R": 0, "ER": 0, "K": 0, "BB": 0, "HR": 0})
        outs_map[team].setdefault(name, 0)
        bf_map[team].setdefault(name, 0)
        runs_map[team].setdefault(name, 0)
        appearance_bf[team].setdefault(name, 0)
        if name not in used_pitchers[team]:
            used_pitchers[team].append(name)

    def start_log(team, name, half, inn):
        pitch_log.append({"Team": team, "Pitcher": name, "Half": half, "Inning_Start": inn, "Inning_End": None})

    def end_log(team, name, half, inn):
        for row in reversed(pitch_log):
            if row["Team"] == team and row["Pitcher"] == name and row["Half"] == half and row["Inning_End"] is None:
                row["Inning_End"] = inn
                break

    def record_run(player_name, team):
        hit_box[team].setdefault(player_name,
                                 {"PA": 0, "AB": 0, "H": 0, "2B": 0, "3B": 0, "HR": 0, "BB": 0, "R": 0, "RBI": 0})
        hit_box[team][player_name]["R"] += 1

    def avg_dra_vs_next_three(def_team, off_team, cur_idx, candidate):
        n = len(off_team.lineup)
        next3 = [off_team.lineup[(cur_idx + i) % n] for i in (1, 2, 3)]
        vals = []
        for nb in next3:
            h_hand = nb.hand
            match = pitcher_probs[
                (pitcher_probs["full_name"] == candidate.name)
                & (pitcher_probs["bats"] == h_hand)
            ]
            if not match.empty and "dra_minus" in match.columns:
                vals.append(float(match.iloc[0]["dra_minus"]))
            else:
                vals.append(getattr(candidate, "dra_minus", 100.0))
        return float(np.mean(vals)) if vals else 100.0

    def pick_next_reliever(def_team, off_team, cur_batter, inning=1):
        try:
            cur_idx = off_team.lineup.index(cur_batter)
        except ValueError:
            cur_idx = 0
        cur_pitcher = def_team.get_pitcher()
        bullpen_candidates = [p for p in def_team.bullpen if p is not cur_pitcher]
        if bullpen_candidates:
            scores = {c: avg_dra_vs_next_three(def_team, off_team, cur_idx, c) for c in bullpen_candidates}
            best = min(scores, key=scores.get)
            def_team.bullpen.remove(best)
            def_team.set_pitcher(best)
            reliever_cap[def_team.name][best.name] = random.randint(3, 5)
            appearance_bf[def_team.name][best.name] = 0
            return best, scores[best], False
        reserves = getattr(def_team, "reserves", [])
        if reserves and (inning >= 10 or emergency_mode[def_team.name]):
            reserve_candidates = [p for p in reserves if p not in def_team.bullpen]
            if reserve_candidates:
                scores = {c: avg_dra_vs_next_three(def_team, off_team, cur_idx, c) for c in reserve_candidates}
                best = min(scores, key=scores.get)
                def_team.reserves.remove(best)
                def_team.set_pitcher(best)
                reliever_cap[def_team.name][best.name] = random.randint(3, 5)
                appearance_bf[def_team.name][best.name] = 0
                if verbose:
                    print(f"🚨 Emergency reserve activation for {def_team.name}: {best.name}")
                return best, scores[best], True
        emergency_mode[def_team.name] = True
        if verbose:
            print(f"⚠️ No pitchers available for {def_team.name}, keeping {cur_pitcher.name}.")
        return cur_pitcher, None, True

    # ------------------
    # Half-inning simulation
    # ------------------
    def sim_half(offense, defense, half, inn):
        outs, runs = 0, 0
        bases = [None, None, None]
        p = defense.get_pitcher()
        ensure_pitcher(defense.name, p.name)
        start_log(defense.name, p.name, half, inn)
        if verbose: print(f"\n{half} {inn}: {offense.name} batting vs {defense.name}")

        while outs < 3:
            batter = offense.next_batter()
            result = simulate_pa(batter, p, hitter_probs, pitcher_probs)
            ensure_pitcher(defense.name, p.name)
            h = hit_box[offense.name].setdefault(
                batter.name, {"PA": 0, "AB": 0, "H": 0, "2B": 0, "3B": 0, "HR": 0, "BB": 0, "R": 0, "RBI": 0})
            h["PA"] += 1
            bf_map[defense.name][p.name] += 1
            appearance_bf[defense.name][p.name] += 1

            if result in ["out", "so"]:
                outs += 1
                h["AB"] += 1
                outs_map[defense.name][p.name] += 1
                if result == "so":
                    pit_box[defense.name][p.name]["K"] += 1

            elif result == "walk":
                h["BB"] += 1
                pit_box[defense.name][p.name]["BB"] += 1
                if all(bases):
                    scorer = bases[2]
                    if scorer:
                        record_run(scorer.name, offense.name)
                    runs += 1
                    pit_box[defense.name][p.name]["R"] += 1
                    pit_box[defense.name][p.name]["ER"] += 1
                    runs_map[defense.name][p.name] = runs_map[defense.name].get(p.name, 0) + 1
                bases = [batter if not bases[0] else bases[0],
                         bases[0] if not bases[1] else bases[1],
                         bases[1] if not bases[2] else bases[2]]

            elif result == "roe":
                # Reached on error
                team_errors[defense.name] += 1
                if all(bases):
                    scorer = bases[2]
                    if scorer:
                        record_run(scorer.name, offense.name)
                    runs += 1
                bases = [batter if not bases[0] else bases[0],
                         bases[0] if not bases[1] else bases[1],
                         bases[1] if not bases[2] else bases[2]]

            else:
                move = {"single": 1, "double": 2, "triple": 3, "hr": 4}[result]
                scoring = []
                for i in reversed(range(3)):
                    if bases[i]:
                        target = i + move
                        if target >= 3:
                            scoring.append(bases[i])
                            bases[i] = None
                        else:
                            bases[target] = bases[i]
                            bases[i] = None
                if move < 4:
                    bases[move - 1] = batter
                else:
                    scoring.append(batter)
                for r in scoring:
                    record_run(r.name, offense.name)
                    runs += 1
                    h["RBI"] += 1
                    pit_box[defense.name][p.name]["R"] += 1
                    pit_box[defense.name][p.name]["ER"] += 1
                    runs_map[defense.name][p.name] = runs_map[defense.name].get(p.name, 0) + 1
                if result != "hr":
                    h["AB"] += 1
                    h["H"] += 1
                if result == "double":
                    h["2B"] += 1
                if result == "triple":
                    h["3B"] += 1
                if result == "hr":
                    h["AB"] += 1
                    h["H"] += 1
                    h["HR"] += 1
                    pit_box[defense.name][p.name]["HR"] += 1

            starter = (p.name == starters[defense.name])
            bf_cur = appearance_bf[defense.name][p.name]
            cap = reliever_cap[defense.name].get(p.name, None)
            runner_flags = [1 if b else 0 for b in bases]

            if should_pull_pitcher(
                p, bf_cur, runs_map[defense.name].get(p.name, 0),
                runner_flags, starter, cap,
                emergency_mode[defense.name],
                outs_this_inning=outs,
            ):
                outs_for_p = outs_map[defense.name][p.name]
                pit_box[defense.name][p.name]["IP"] += outs_for_p / 3.0
                outs_map[defense.name][p.name] = 0
                end_log(defense.name, p.name, half, inn)
                newp, dra, emerg = pick_next_reliever(defense, offense, batter, inning=inn)
                if emerg:
                    start_log(defense.name, p.name, half, inn)
                    continue
                p = defense.get_pitcher()
                if verbose:
                    print(f"🧮 Manager selects {p.name} (Avg DRA-: {dra:.1f})")
                ensure_pitcher(defense.name, p.name)
                start_log(defense.name, p.name, half, inn)

        outs_for_final = outs_map[defense.name][p.name]
        pit_box[defense.name][p.name]["IP"] += outs_for_final / 3.0
        outs_map[defense.name][p.name] = 0
        end_log(defense.name, p.name, half, inn)
        return runs

    # ------------------
    # Inning loop
    # ------------------
    inn = 1
    while True:
        away_runs = sim_half(away, home, "Top", inn)
        inning_log[away.name].append(away_runs)
        score[away.name] += away_runs
        if verbose: print(f"End of Top {inn}: {score}")

        if inn >= 9 and score[home.name] > score[away.name]:
            break

        home_runs = sim_half(home, away, "Bottom", inn)
        inning_log[home.name].append(home_runs)
        score[home.name] += home_runs
        if verbose: print(f"End of {inn}: {score}")

        if inn >= 9 and score[home.name] != score[away.name]:
            break
        inn += 1

    # ------------------
    # Summary output + boxscore
    # ------------------
    hit_rows = [{"Team": t, "Player": p, **s} for t, team in hit_box.items() for p, s in team.items()]
    pit_rows = [{"Team": t, "Pitcher": p, **s} for t, team in pit_box.items() for p, s in team.items()]
    log_df = pd.DataFrame(pitch_log)
    hit_df = pd.DataFrame(hit_rows)[["Team", "Player", "PA", "AB", "H", "2B", "3B", "HR", "BB", "RBI", "R"]] if hit_rows else pd.DataFrame()
    pit_df = pd.DataFrame(pit_rows)[["Team", "Pitcher", "IP", "R", "ER", "K", "BB", "HR"]] if pit_rows else pd.DataFrame()

    # --- Build inning-by-inning boxscore ---
    max_innings = max(len(inning_log[away.name]), len(inning_log[home.name]))
    columns = [f"inning_{i}" for i in range(1, max_innings + 1)]

    def pad_innings(runs_list):
        return runs_list + [""] * (max_innings - len(runs_list))

    away_row = pad_innings(inning_log[away.name]) + [
        score[away.name],
        int(hit_df[hit_df["Team"] == away.name]["H"].sum()) if not hit_df.empty else 0,
        team_errors[home.name]  # away team’s errors = home defense
    ]
    home_row = pad_innings(inning_log[home.name]) + [
        score[home.name],
        int(hit_df[hit_df["Team"] == home.name]["H"].sum()) if not hit_df.empty else 0,
        team_errors[away.name]  # home team’s errors = away defense
    ]

    box_df = pd.DataFrame(
        [away_row, home_row],
        columns=columns + ["r", "h", "e"]
    )
    box_df.insert(0, "team", [away.name, home.name])
    box_df.insert(0, "game_id", [f"game_{random.randint(1000,9999)}"] * 2)

    if verbose:
        print("\n📊 Inning Boxscore:")
        print(box_df)

    return score, hit_df, pit_df, log_df, box_df
