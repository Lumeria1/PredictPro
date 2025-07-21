from enum import IntEnum
from .api_football import infer_season, get_last5_team_fixtures, get_last_n_team_fixtures, get_last5_team_fixtures, get_last5_home_fixtures, get_last5_away_fixtures, get_standings, get_fixture_events, parse_minute, check_team_first_half_performance, get_lineups_for_fixture, RELEGATION_CUTOFFS, TOP4_THRESHOLD
from .config import settings
from datetime import datetime
from typing import Dict, List, Any
from enum import IntEnum
from datetime import timedelta
import sys

class SignalID(IntEnum):
    FORM = 1
    OVER15 = 2
    BTTS = 3
    HOME_AWAY_STRENGTH = 4
    LEAGUE_STAKES = 5
    BOUNCE_BACK = 6
    MOMENTUM_PRESSURE = 7
    FIRST_HALF_GOAL_TIMING = 8
    FIRST_HALF_OVER05 = 9
    FAST_STARTERS = 10
    HOME_PRESSURE_START = 11
    LINEUP = 12

    # define additional signals here

# Each handler returns (status: str, value: float|None, note: str)
#FORM_SIGNAL = 1
def compute_form_signal(fixture, db_session):
    # determine season param
    ko = fixture.kickoff
    season = infer_season(fixture.league_api_id, ko)
    if not season:
        print("❌  Could not infer season from kickoff date")
        sys.exit(1)

    # Fetch last 5 fixtures (regardless of venue) for each team
    home5 = get_last5_team_fixtures(fixture.home_team_api_id, fixture.league_api_id, season)
    away5 = get_last5_team_fixtures(fixture.away_team_api_id, fixture.league_api_id, season)

    print(f"\n🚩 Season: {season}")
    print(f"▶️  Home team last 5 fixtures ({len(home5)}):")
    for f in home5:
        d = f["fixture"]["date"]
        g = f["goals"]
        print(f"   • {d} → {g['home']}-{g['away']}")
    print(f"\n▶️  Away team last 5 fixtures ({len(away5)}):")
    for f in away5:
        d = f["fixture"]["date"]
        g = f["goals"]
        print(f"   • {d} → {g['home']}-{g['away']}")

        # count home team wins in their last 5 matches
    home_wins = 0
    for f in home5:
        # Identify team goals and opponent goals regardless of side
        if f["teams"]["home"]["id"] == fixture.home_team_api_id:
            team_goals = f["goals"]["home"]
            opp_goals  = f["goals"]["away"]
        else:
            team_goals = f["goals"]["away"]
            opp_goals  = f["goals"]["home"]
        if team_goals > opp_goals:
            home_wins += 1

    # count away team losses in their last 5 matches
    away_losses = 0
    for f in away5:
        # Identify team goals and opponent goals regardless of side
        if f["teams"]["home"]["id"] == fixture.away_team_api_id:
            team_goals = f["goals"]["home"]
            opp_goals  = f["goals"]["away"]
        else:
            team_goals = f["goals"]["away"]
            opp_goals  = f["goals"]["home"]
        if team_goals < opp_goals:
            away_losses += 1

    # determine status/value/note
    value = home_wins - away_losses
    status = "Y" if home_wins >= 3 or away_losses >= 3 else "N"
    note = f"Home wins: {home_wins}/{len(home5)}, Away losses: {away_losses}/{len(away5)}"
    print(f"\n🏁 Form signal → Status={status}, Value={value}, Note='{note}'\n")
    return status, value, note


#OVER15_SIGNAL = 2
def compute_over15_signal(fixture, db_session):
    # 1) infer season
    ko = fixture.kickoff
    season = infer_season(fixture.league_api_id, ko)
    if not season:
        print("❌  Could not infer season from kickoff date")
        sys.exit(1)

    # 2) fetch last 5 valid fixtures for each team
    home5 = get_last5_team_fixtures(fixture.home_team_api_id, fixture.league_api_id, season)
    away5 = get_last5_team_fixtures(fixture.away_team_api_id, fixture.league_api_id, season)

    print(f"\n🚩 Season: {season}")
    print(f"▶️  Last 5 HOME fixtures ({len(home5)}):")
    for f in home5:
        dt = f["fixture"]["date"]
        g  = f["goals"]
        print(f"   • {dt} → {g['home']}-{g['away']}")

    print(f"\n▶️  Last 5 AWAY fixtures ({len(away5)}):")
    for f in away5:
        dt = f["fixture"]["date"]
        g  = f["goals"]
        print(f"   • {dt} → {g['home']}-{g['away']}")

    # 3) combine exactly 10 played fixtures
    combined = home5 + away5
    print(f"\n🔗 Combined fixtures count: {len(combined)}")

    if len(combined) < 10:
        print("⚠️  Insufficient played fixtures to compute Over 1.5 signal.")
        return

    # 4) compute Over 1.5 rate
    over_count = sum(
        1 for f in combined
        if (f["goals"]["home"] + f["goals"]["away"]) >= 2
    )
    rate   = over_count / len(combined)
    if rate >= 0.80:
        status = "Y"
    elif rate < 0.60:
        status = "N"
    else:
        status = "-"

    note = f"{over_count}/{len(combined)} games ≥2 goals ({rate:.0%})"
    print(f"\n🏁 Over 1.5 signal → Status={status}, Rate={rate:.2f}, Note='{note}'\n")
    return status, rate, note

#BTTS_SIGNAL = 3
def compute_btts_signal(fixture, db_session):
    # 1) infer season
    ko = fixture.kickoff
    season = infer_season(fixture.league_api_id, ko)
    if not season:
        print("❌  Could not infer season from kickoff date")
        sys.exit(1)

    # 2) fetch last 5 valid fixtures for each team
    home5 = get_last5_team_fixtures(fixture.home_team_api_id, fixture.league_api_id, season)
    away5 = get_last5_team_fixtures(fixture.away_team_api_id, fixture.league_api_id, season)

    print(f"\n🚩 Season: {season}")
    print(f"▶️  Last 5 HOME fixtures ({len(home5)}):")
    for f in home5:
        dt = f["fixture"]["date"]
        g  = f["goals"]
        print(f"   • {dt} → {g['home']}-{g['away']}")

    print(f"\n▶️  Last 5 AWAY fixtures ({len(away5)}):")
    for f in away5:
        dt = f["fixture"]["date"]
        g  = f["goals"]
        print(f"   • {dt} → {g['home']}-{g['away']}")

    # 3) combine exactly 10 played fixtures
    combined = home5 + away5
    print(f"\n🔗 Combined fixtures count: {len(combined)}")

    if len(combined) < 10:
        print("⚠️  Insufficient played fixtures to compute BTTS signal.")
        return

    # 4) compute BTTS rate
    btts_count = sum(
        1 for f in combined
        if f["goals"]["home"] > 0 and f["goals"]["away"] > 0
    )
    rate = btts_count / len(combined)
    if rate >= 0.70:
        status = "Y"
    elif rate < 0.50:
        status = "N"
    else:
        status = "-"

    note = f"{btts_count}/{len(combined)} games with both teams scoring ({rate:.0%})"
    print(f"\n🏁 BTTS signal → Status={status}, Rate={rate:.2f}, Note='{note}'\n")
    return status, rate, note

# HOME_AWAY_STRENGTH_SIGNAL = 4
def compute_home_away_strength_signal(fixture, db_session):
    # 1) infer season
    ko = fixture.kickoff
    season = infer_season(fixture.league_api_id, ko)
    if not season:
        print("❌  Could not infer season from kickoff date")
        sys.exit(1)

    # 2) fetch last 5 HOME fixtures for home team, and last 5 AWAY fixtures for away team
    home5 = get_last5_home_fixtures(fixture.home_team_api_id, fixture.league_api_id, season)
    away5 = get_last5_away_fixtures(fixture.away_team_api_id, fixture.league_api_id, season)

    print(f"\n🚩 Season: {season}")
    print(f"▶️  Last 5 HOME fixtures for Home ({len(home5)}):")
    for f in home5:
        dt = f["fixture"]["date"]
        g  = f["goals"]
        print(f"   • {dt} → {g['home']}-{g['away']}")

    print(f"\n▶️  Last 5 AWAY fixtures for Away ({len(away5)}):")
    for f in away5:
        dt = f["fixture"]["date"]
        g  = f["goals"]
        print(f"   • {dt} → {g['home']}-{g['away']}")

    # 3) count home wins in last 5 home matches, and away wins in last 5 away matches
    home_wins = sum(
        1 for f in home5
        if f["goals"]["home"] > f["goals"]["away"]
    )
    away_wins = sum(
        1 for f in away5
        if f["goals"]["away"] > f["goals"]["home"]
    )

    print(f"\n🔗 Home wins in last 5 @HOME: {home_wins}")
    print(f"🔗 Away wins in last 5 @AWAY: {away_wins}")

    # 4) apply Home/Away Strength rules:
    #    ✔️ Green if: home_wins >= 3 AND away_wins <= 1
    #    ✘ White X if: home_wins < 3 AND away_wins >= 3
    #    ➖ Neutral otherwise
    if home_wins >= 3 and away_wins <= 1:
        status = "Y"
    elif home_wins < 3 and away_wins >= 3:
        status = "N"
    else:
        status = "-"

    note = f"{home_wins}/{len(home5)}, {away_wins}/{len(away5)}"
    value = home_wins - away_wins
    if status == "Y":
        note += " → Home strong, Away weak"
    elif status == "N":
        note += " → Home weak, Away strong"
    else:
        note += " → Neutral strength"
    print(f"\n🏁 Home/Away Strength signal → Status={status}, Note='{note}'\n")
    return status, value, note

# MOTIVATIONS: LEAGUE STAKES = 5
def compute_league_stakes_signal(fixture, db_session):
    # 1) infer season
    ko = fixture.kickoff
    season = infer_season(fixture.league_api_id, ko)
    if not season:
        print("❌ Could not infer season from kickoff date")
        sys.exit(1)

    # 2) fetch standings and find home/away entries
    standings = get_standings(fixture.league_api_id, season)
    # If standings are empty, we cannot determine stakes
    if not standings:
        print("⚠️ Could not fetch standings; defaulting to Neutral (–)")
        print("\n🏁 League Stakes signal → Status=-, Note='Standings unavailable'\n")
        return
    

    # Build a map: team_id -> {rank, played}
    pos_map: Dict[int, Dict[str, int]] = {}
    for entry in standings:
        team_id = entry.get("team", {}).get("id")
        rank    = entry.get("rank")
        played  = entry.get("all", {}).get("played", 0)
        pos_map[team_id] = {"rank": rank, "played": played}

    home_data = pos_map.get(fixture.home_team_api_id)
    away_data = pos_map.get(fixture.away_team_api_id)

    if not home_data or not away_data:
        print("⚠️ One of the teams is not found in standings; defaulting to Neutral (–)")
        print("\n🏁 League Stakes signal → Status=-, Note='Team missing from table'\n")
        return

    # 3) Check if too early: each team must have played ≥5
    if home_data["played"] < 5 or away_data["played"] < 5:
        print("⚠️ Too early in season (teams have < 5 matches played)")
        print("\n🏁 League Stakes signal → Status=-, Note='Too early to gauge stakes'\n")
        return

    # 4) Determine relegation cutoff for this league
    num_teams = len(standings)
    releg_n = RELEGATION_CUTOFFS.get(fixture.league_api_id, 3)  # default to bottom 3
    # Positions in relegation zone: ranks > (num_teams - releg_n)
    relegation_zone = set(range(num_teams - releg_n + 1, num_teams + 1)) if releg_n > 0 else set()

    # 5) Check Green conditions (top‐4 or relegation battle)
    home_rank = home_data["rank"]
    away_rank = away_data["rank"]

    home_in_top4 = home_rank <= TOP4_THRESHOLD
    away_in_top4 = away_rank <= TOP4_THRESHOLD
    home_in_releg = home_rank in relegation_zone
    away_in_releg = away_rank in relegation_zone

    if home_in_top4 or away_in_top4 or home_in_releg or away_in_releg:
        status = "Y"
        note = (
            f"Home rank={home_rank}, Away rank={away_rank} → "
            "At least one in top-4 or relegation zone"
        )
    else:
        # 6) Check Red condition: “Mid‐table with nothing to play for”
        # This means neither team in top4 nor in relegation zone
        status = "N"
        note = f"Home rank={home_rank}, Away rank={away_rank} → Both in mid‐table"
    
    value = home_rank - away_rank

    print(f"\n🏁 League Stakes signal → Status={status}, Note='{note}'\n")
    return status, value, note

# MOTIVATIONS: BOUNCE BACK = 6
def compute_bounce_back_signal(fixture, db_session):
    # 1) infer season
    ko = fixture.kickoff
    season = infer_season(fixture.league_api_id, ko)
    if not season:
        print("❌ Could not infer season from kickoff date")
        sys.exit(1)

    # 2) fetch last 1 fixture for the home team
    last1 = get_last_n_team_fixtures(fixture.home_team_api_id, fixture.league_api_id, season, n=1)
    if not last1:
        print("⚠️ No previous fixture found; defaulting to Neutral (–)")
        print("\n🏁 Bounce-Back signal → Status=-, Note='No prior fixture'\n")
        return

    f = last1[0]
    # Ensure the last fixture was played (non-null goals)
    goals = f.get("goals", {})
    if goals.get("home") is None or goals.get("away") is None:
        print("⚠️ Last fixture unplayed; defaulting to Neutral (–)")
        print("\n🏁 Bounce-Back signal → Status=-, Note='Last fixture not played'\n")
        return

    # 3) Determine if last fixture was a loss by ≥2 for the home team
    home_id_prev = f["teams"]["home"]["id"]
    away_id_prev = f["teams"]["away"]["id"]
    home_goals   = goals["home"]
    away_goals   = goals["away"]

    # Find how the home team performed in that match
    if home_id_prev == fixture.home_team_api_id:
        # Home team played at home last time
        margin = home_goals - away_goals
    else:
        # Home team played away last time
        margin = away_goals - home_goals

    # 4) Determine upcoming fixture venue for home team (we know fx.home_team_api_id is at home)
    # (By definition of this harness, we're evaluating the fixture where home_team_api_id is at home.)

    # 5) Check Green: home team lost last match by ≥2 and now is at home
    if margin <= -2:
        status = "Y"
        value = margin
        note = f"Home team lost last time by {abs(margin)} and now at home → Bounce-Back!"
        print(f"\n🏁 Bounce-Back signal → Status={status}, Note='{note}'\n")
        

    # 6) Check Red: home team won last match by ≥2
    if margin >= 2:
        status = "N"
        value = margin
        note = f"Home team won last time by {margin} (easy win) → No bounce-back needed"
        print(f"\n🏁 Bounce-Back signal → Status={status}, Note='{note}'\n")
        

    # 7) Otherwise, Neutral
    status = "-"
    note = f"Last result margin={margin}, not qualifying for Bounce-Back or Red"
    value = margin  # Not used, but keeping for consistency
    # value = margin  # Not used, but keeping for consistency
    print(f"\n🏁 Bounce-Back signal → Status={status}, Note='{note}'\n")
    return status, value, note

# MOTIVATIONS: HOME PRESSURE START = 7
def compute_momentum_pressure_signal(fixture, db_session):
    """
    Signal 8: Motivation – Momentum/Pressure

    - Green ("Y") if:
        * Home team's first home match this season ("home-opener")
        * OR home team is on a 3+ match unbeaten run (win/draw, last 3 matches, any venue)
    - Neutral ("-") if less than 3 played matches
    - Otherwise Neutral ("-")
    """
    # 1) Infer season
    ko = fixture.kickoff
    season = infer_season(fixture.league_api_id, ko)
    if not season:
        return "-", 0, "Could not infer season from kickoff date"

    # 2) Check for Home-Opener: No previous home matches played
    last_fixtures = get_last_n_team_fixtures(fixture.home_team_api_id, fixture.league_api_id, season, n=20)
    prior_home = []
    for f in last_fixtures:
        goals = f.get("goals", {})
        if goals.get("home") is None or goals.get("away") is None:
            continue
        if f["teams"]["home"]["id"] != fixture.home_team_api_id:
            continue
        # Compare fixture date to kickoff
        api_dt = datetime.fromisoformat(f["fixture"]["date"])
        fixture_dt = api_dt.replace(tzinfo=None)
        if fixture_dt < fixture.kickoff.replace(tzinfo=None):
            prior_home.append(f)
    if not prior_home:
        status = "Y"
        note = "Home-opener: No previous home matches this season"
        value = 1
        return status, value, note

    # 3) Check for Unbeaten Run ≥ 3 for Home Team
    last5 = get_last_n_team_fixtures(fixture.home_team_api_id, fixture.league_api_id, season, n=5)
    played_fixtures = [
        f for f in last5
        if f.get("goals", {}).get("home") is not None
           and f.get("goals", {}).get("away") is not None
    ]
    if len(played_fixtures) < 3:
        status = "-"
        note = "Less than 3 played matches → cannot assess unbeaten run"
        value = 0
        return status, value, note

    unbeaten_count = 0
    # API returns fixtures in date descending order (most recent first)
    for f in played_fixtures[:3]:
        goals = f.get("goals", {})
        home_id_prev = f["teams"]["home"]["id"]
        away_id_prev = f["teams"]["away"]["id"]
        home_goals   = goals["home"]
        away_goals   = goals["away"]

        # Determine result from home team's perspective
        if home_id_prev == fixture.home_team_api_id:
            if home_goals >= away_goals:
                unbeaten_count += 1
        else:
            if away_goals >= home_goals:
                unbeaten_count += 1

    if unbeaten_count >= 3:
        status = "Y"
        note = "Home team is on a 3-match unbeaten run"
        value = unbeaten_count
        return status, value, note

    # 4) Otherwise: Neutral
    status = "-"
    note = "No unbeaten run ≥3 and not a home-opener → Neutral"
    value = 0
    return status, value, note


# FIRST HALF GOAL TIMING SIGNAL = 8
def compute_1h_goal_timing_signal(fixture, db_session):
    # 1) Infer season
    ko = fixture.kickoff
    season = infer_season(fixture.league_api_id, ko)
    if not season:
        print("❌ Could not infer season from kickoff date")
        sys.exit(1)

    # 2) Fetch last 5 fixtures for home + last 5 for away
    home5 = get_last_n_team_fixtures(fixture.home_team_api_id, fixture.league_api_id, season, n=5)
    away5 = get_last_n_team_fixtures(fixture.away_team_api_id, fixture.league_api_id, season, n=5)

    print(f"\n🚩 Season: {season}")
    print(f"▶️ Home team last {len(home5)} fixtures:")
    for f in home5:
        print(f"   • {f['fixture']['date']}  {f['teams']['home']['id']} vs {f['teams']['away']['id']}  Score: {f['goals']['home']}-{f['goals']['away']}  ID={f['fixture']['id']}")
    print(f"\n▶️ Away team last {len(away5)} fixtures:")
    for f in away5:
        print(f"   • {f['fixture']['date']}  {f['teams']['home']['id']} vs {f['teams']['away']['id']}  Score: {f['goals']['home']}-{f['goals']['away']}  ID={f['fixture']['id']}")

    if len(home5) < 5 or len(away5) < 5:
        print("⚠️ Insufficient fixtures (need 5 each).")
        print("\n🏁 1H Goal Timing signal → Status=-, Note='Insufficient data'\n")
        return

    combined = home5 + away5
    print(f"\n🔗 Combined fixtures count: {len(combined)}")

    # 3) Count how many of these 10 had at least one goal in minute 1–30
    positive_count = 0
    missing = []
    for f in combined:
        fid = f["fixture"]["id"]
        events = get_fixture_events(fid)
        if not events:
            missing.append(fid)
            continue

        found_1h_goal = False
        for event in events:
            if event.get("type") == "Goal":
                elapsed = event.get("time", {}).get("elapsed")
                # Only count if elapsed is an integer between 1 and 30
                if isinstance(elapsed, int) and 1 <= elapsed <= 30:
                    found_1h_goal = True
                    break
        if found_1h_goal:
            positive_count += 1


    if missing:
        print(f"⚠️ Missing events for fixture IDs: {missing}")
        print("   → Counting them as ‘no goal in first 30 mins’ for now.")

    print(f"\n📊 Fixtures with 1H goal ≤30min: {positive_count}/{len(combined)}")

    # 4) Determine status
    # Green if ≥7, Red if ≤4, Neutral otherwise
    if positive_count >= 7:
        status = "Y"
        note = f"{positive_count}/10 had a 1H goal by 30′ → Green"
        value = positive_count  # Not used, but keeping for consistency
    elif positive_count <= 4:
        status = "N"
        note = f"{positive_count}/10 had a 1H goal by 30′ → Red"
        value = positive_count
    else:
        status = "-"
        note = f"{positive_count}/10 had a 1H goal by 30′ → Neutral"
        value = positive_count
    # Print the final status
    print(f"\n🏁 1H Goal Timing signal → Status={status}, Note='{note}'\n")
    return status, value, note 

# FIRST HALF OVER 0.5 SIGNAL = 9
def compute_1h_over05_signal(fixture, db_session):
    # 1) Infer season
    ko = fixture.kickoff
    season = infer_season(fixture.league_api_id, ko)
    if not season:
        print("❌ Could not infer season from kickoff date")
        sys.exit(1)

    # 2) Fetch last 5 fixtures for home + last 5 for away
    home5 = get_last_n_team_fixtures(fixture.home_team_api_id, fixture.league_api_id, season, n=5)
    away5 = get_last_n_team_fixtures(fixture.away_team_api_id, fixture.league_api_id, season, n=5)

    print(f"\n🚩 Season: {season}")
    print(f"▶️ Home team last {len(home5)} fixtures:")
    for f in home5:
        print(f"   • {f['fixture']['date']}  {f['teams']['home']['id']} vs {f['teams']['away']['id']}  Score: {f['goals']['home']}-{f['goals']['away']}  ID={f['fixture']['id']}")
    print(f"\n▶️ Away team last {len(away5)} fixtures:")
    for f in away5:
        print(f"   • {f['fixture']['date']}  {f['teams']['home']['id']} vs {f['teams']['away']['id']}  Score: {f['goals']['home']}-{f['goals']['away']}  ID={f['fixture']['id']}")

    if len(home5) < 5 or len(away5) < 5:
        print("⚠️ Insufficient fixtures (need 5 each).")
        print("\n🏁 1H Over 0.5 signal → Status=-, Note='Insufficient data'\n")
        return

    combined = home5 + away5
    print(f"\n🔗 Combined fixtures count: {len(combined)}")

    # 3) Count how many of these 10 had at least one goal in minutes 1–45
    positive_count = 0
    missing = []
    for f in combined:
        fid = f["fixture"]["id"]
        events = get_fixture_events(fid)
        if not events:
            missing.append(fid)
            continue

        found_1h_goal = False
        for event in events:
            if event.get("type") == "Goal":
                elapsed = event.get("time", {}).get("elapsed")
                # elapsed is an integer like 10, 45, 45+1 (but API always returns an int)
                if isinstance(elapsed, int) and 1 <= elapsed <= 45:
                    found_1h_goal = True
                    break
        if found_1h_goal:
            positive_count += 1

    if missing:
        print(f"⚠️ Missing events for fixture IDs: {missing}")
        print("   → Counting them as ‘no first‐half goal’ for now.")

    print(f"\n📊 Fixtures with 1H goal ≤45min: {positive_count}/{len(combined)}")

    # 4) Determine status
    # Green if ≥8, Red if ≤5, Neutral otherwise
    if positive_count >= 8:
        status = "Y"
        note = f"{positive_count}/10 had a 1H goal → Green"
        value = positive_count
    elif positive_count <= 5:
        status = "N"
        note = f"{positive_count}/10 had a 1H goal → Red"
        value = positive_count
    else:
        status = "-"
        note = f"{positive_count}/10 had a 1H goal → Neutral"
        value = positive_count
    # Print the final status
    print(f"\n🏁 1H Over 0.5 signal → Status={status}, Note='{note}'\n")
    return status, value, note

# FAST STARTERS SIGNAL = 10
def compute_fast_starters_signal(fixture, db_session):
    # 1) Infer season
    ko = fixture.kickoff
    season = infer_season(fixture.league_api_id, ko)
    if not season:
        print("❌ Could not infer season from kickoff date")
        sys.exit(1)

    print(f"\n🚩 Season: {season}")
    print(f"🏠 Home Team ID: {fixture.home_team_api_id}")
    print(f"✈️  Away Team ID: {fixture.away_team_api_id}")

    # 2) Fetch last 5 fixtures for the HOME team
    home5 = get_last_n_team_fixtures(fixture.home_team_api_id, fixture.league_api_id, season, n=5)
    print(f"\n▶️  Home team last {len(home5)} fixtures:")
    for i, f in enumerate(home5, 1):
        dt = f["fixture"]["date"]
        g = f["goals"]
        home_team = f["teams"]["home"]["name"]
        away_team = f["teams"]["away"]["name"]
        print(f"   {i}. {dt[:10]} - {home_team} {g['home']}-{g['away']} {away_team} (ID: {f['fixture']['id']})")

    if len(home5) < 5:
        print("⚠️ Insufficient home team fixtures (need 5).")
        print("\n🏁 Fast Starters signal → Status=-, Note='Insufficient data'\n")
        return

    # 3) Fetch last 5 fixtures for the AWAY team
    away5 = get_last_n_team_fixtures(fixture.away_team_api_id, fixture.league_api_id, season, n=5)
    print(f"\n▶️  Away team last {len(away5)} fixtures:")
    for i, f in enumerate(away5, 1):
        dt = f["fixture"]["date"]
        g = f["goals"]
        home_team = f["teams"]["home"]["name"]
        away_team = f["teams"]["away"]["name"]
        print(f"   {i}. {dt[:10]} - {home_team} {g['home']}-{g['away']} {away_team} (ID: {f['fixture']['id']})")

    if len(away5) < 5:
        print("⚠️ Insufficient away team fixtures (need 5).")
        print("\n🏁 Fast Starters signal → Status=-, Note='Insufficient data'\n")
        return

    # 4) Check HOME team's first half performance
    home_scored_count, home_conceded_count, home_missing = check_team_first_half_performance(
        home5, fixture.home_team_api_id, "Home"
    )
    
    if home_missing:
        print(f"\n⚠️ Missing events for home team fixture IDs: {home_missing}")
        print("   → Counting them as 'no 1H activity' by default.")

    print(f"\n📊 Home team 1H performance:")
    print(f"   • Scored in {home_scored_count}/{len(home5)} matches")
    print(f"   • Conceded in {home_conceded_count}/{len(home5)} matches")

    # 5) Check AWAY team's first half performance  
    away_scored_count, away_conceded_count, away_missing = check_team_first_half_performance(
        away5, fixture.away_team_api_id, "Away"
    )
    
    if away_missing:
        print(f"\n⚠️ Missing events for away team fixture IDs: {away_missing}")
        print("   → Counting them as 'no 1H activity' by default.")

    print(f"\n📊 Away team 1H performance:")
    print(f"   • Scored in {away_scored_count}/{len(away5)} matches")
    print(f"   • Conceded in {away_conceded_count}/{len(away5)} matches")

    # 6) Determine overall signal based on both teams' attacking and defensive performance
    print(f"\n🎯 SIGNAL ANALYSIS:")
    print(f"   • Home team 1H goals scored: {home_scored_count}/5")
    print(f"   • Home team 1H goals conceded: {home_conceded_count}/5")
    print(f"   • Away team 1H goals scored: {away_scored_count}/5")
    print(f"   • Away team 1H goals conceded: {away_conceded_count}/5")
    
    # Enhanced signal logic considering both scoring and defensive patterns
    home_attacking_strong = home_scored_count >= 4  # Strong attacking
    home_attacking_weak = home_scored_count <= 1    # Weak attacking
    home_defensive_weak = home_conceded_count >= 4  # Poor defense (good for goals)
    home_defensive_strong = home_conceded_count <= 1 # Strong defense (bad for goals)
    
    away_attacking_strong = away_scored_count >= 4
    away_attacking_weak = away_scored_count <= 1
    away_defensive_weak = away_conceded_count >= 4
    away_defensive_strong = away_conceded_count <= 1
    
    # Signal determination based on goal-scoring probability
    if (home_attacking_strong or away_defensive_weak or home_defensive_weak or away_attacking_strong) and not (home_defensive_strong and away_attacking_weak):
        status = "Y"
        factors = []
        if home_attacking_strong:
            factors.append("Home strong attack")
        if away_defensive_weak:
            factors.append("Away weak defense")
        if home_defensive_weak:
            factors.append("Home weak defense")
        if away_attacking_strong:
            factors.append("Away strong attack")
        note = f"H: {home_scored_count}⚽/{home_conceded_count}🥅, A: {away_scored_count}⚽/{away_conceded_count}🥅 → Fast Start Likely - {', '.join(factors)} (Green)"
        value = home_scored_count + away_scored_count  # Total goals scored in first half
        
    elif (home_attacking_weak and away_defensive_strong) or (home_defensive_strong and away_attacking_weak):
        status = "N"
        factors = []
        if home_attacking_weak:
            factors.append("Home weak attack")
        if away_defensive_strong:
            factors.append("Away strong defense")
        if home_defensive_strong:
            factors.append("Home strong defense")
        if away_attacking_weak:
            factors.append("Away weak attack")
        note = f"H: {home_scored_count}⚽/{home_conceded_count}🥅, A: {away_scored_count}⚽/{away_conceded_count}🥅 → Slow Start Likely - {', '.join(factors)} (Red)"
        value = home_scored_count + away_scored_count
        
    else:
        status = "-"
        note = f"H: {home_scored_count}⚽/{home_conceded_count}🥅, A: {away_scored_count}⚽/{away_conceded_count}🥅 → Mixed Patterns (Neutral)"
        value = home_scored_count + away_scored_count  # Total goals scored in first half

    print(f"\n🏁 Fast Starters signal → Status={status}, Note='{note}'\n")
    return status, value, note  

# HOME PRESSURE START SIGNAL = 11
def compute_home_pressure_signal(fixture, db_session):
    # 1) Infer season
    ko = fixture.kickoff
    season = infer_season(fixture.league_api_id, ko)
    if not season:
        print("❌ Could not infer season from kickoff date")
        sys.exit(1)

    # 2) Fetch last 3 fixtures (home OR away) for the home team
    last3 = get_last_n_team_fixtures(fixture.home_team_api_id, fixture.league_api_id, season, n=3)
    print(f"\n🚩 Season: {season}")
    print(f"▶️ Home team last {len(last3)} fixtures:")
    for f in last3:
        dt = f["fixture"]["date"]
        g  = f["goals"]
        print(f"   • {dt}  {f['teams']['home']['id']} vs {f['teams']['away']['id']}  Score: {g['home']}-{g['away']}  ID={f['fixture']['id']}")

    if len(last3) < 3:
        print("⚠️ Insufficient fixtures (need 3).")
        print("\n🏁 Home Pressure Start signal → Status=-, Note='Insufficient data'\n")
        return

    # 3) Determine results for each of the 3 matches from home team's perspective
    losses = 0
    wins   = 0
    for f in last3:
        goals = f.get("goals", {})
        home_id_prev = f["teams"]["home"]["id"]
        away_id_prev = f["teams"]["away"]["id"]
        home_goals   = goals.get("home", 0)
        away_goals   = goals.get("away", 0)

        if home_id_prev == fixture.home_team_api_id:
            margin = home_goals - away_goals
        else:
            margin = away_goals - home_goals

        if margin < 0:
            losses += 1
        elif margin > 0:
            wins += 1
        # Draws (margin == 0) count toward neither wins nor losses

    # 4) Determine status: 
    #    Green if losses ≥ 2, Red if wins == 3, Neutral otherwise
    if losses >= 2:
        status = "Y"
        note = f"Lost {losses}/3 → High pressure (Green)"
        value = losses
    elif wins == 3:
        status = "N"
        note = f"Won all 3 → No pressure (Red)"
        value = wins
    else:
        status = "-"
        note = f"Wins={wins}, Losses={losses} → Neutral"
        value = 0
    # Print the final status
    print(f"\n🏁 Home Pressure Start signal → Status={status}, Note='{note}'\n")
    return status, value, note  # Returning losses as value for consistency

# LINEUPS SIGNAL = 12
def compute_lineups_signal(fixture, db_session):
    # 1) Infer season (just for context printing)
    ko = fixture.kickoff
    season = infer_season(fixture.league_api_id, ko)
    print(f"\n🚩 Season: {season}")

    # 2) Check current time vs kickoff - 1h
    now = datetime.now()  # naive local time
    kickoff_dt = fixture.kickoff
    cutoff = kickoff_dt - timedelta(hours=1)

    if now < cutoff:
        # More than 1h until kick-off → Neutral
        print("⚠️ More than 1 hour until kickoff → lineups not yet published")
        print("\n🏁 Lineups signal → Status=-, Note='Too early for lineups'\n")
        return

    # 3) Fetch lineups
    lineups = get_lineups_for_fixture(fixture.home_team_api_id)  # pass in fixture id below
    # NOTE: We assume HOME_ID==fx.home_team_api_id is not a fixture ID; so we need
    # the actual fixture ID. In this standalone harness, we use HOME_ID as a placeholder
    # for fixture_id. Replace HOME_ID with the real fixture ID if needed.
    # But typically, the fixture ID is the one you pass; here we assume KICKOFF corresponds
    # exactly to a single fixture. Adjust as necessary.
    #
    # For clarity, in a real scenario, you'd supply FIXTURE_ID.
    #
    # For this test script, we’ll loop over lineups returned and find the one
    # where team.id == HOME_ID, then count startXI.
    #
    # Very often, the API returns: [{ "team": {"id": 8008, …}, "startXI": […] }, …]

    # Find the HOME team’s lineup
    home_lineup = None
    for entry in lineups:
        if entry.get("team", {}).get("id") == fixture.home_team_api_id:
            home_lineup = entry.get("startXI", [])
            break

    if home_lineup is None:
        # Lineups published but no entry for home team → Neutral
        print("⚠️ Lineups published but home team entry missing → cannot decide")
        print("\n🏁 Lineups signal → Status=-, Note='Home lineup not found'\n")
        return

    # 4) Determine status
    count_starters = len(home_lineup)
    if count_starters == 11:
        status = "Y"
        note = "11 starters listed → Full squad (Green)"
        value = count_starters  # Returning count as value for consistency
    elif count_starters < 11:
        status = "N"
        note = f"{count_starters} starters listed → Incomplete (Red)"
        value = count_starters  # Returning count as value for consistency
    else:
        # More than 11 is unexpected, treat as Neutral
        status = "-"
        note = f"{count_starters} starters listed → Unexpected (Neutral)"
        value = count_starters  # Returning count as value for consistency
    # Print the final status
    print(f"\n▶️ Home starting XI count: {count_starters}")
    print(f"\n🏁 Lineups signal → Status={status}, Note='{note}'\n")
    return status, note, value  # Returning count as value for consistency










# Map of signal IDs to their computation functions
# Registry mapping
SIGNAL_HANDLERS = {   
    SignalID.FORM: compute_form_signal,
    SignalID.OVER15: compute_over15_signal,
    SignalID.BTTS: compute_btts_signal,
    SignalID.HOME_AWAY_STRENGTH: compute_home_away_strength_signal,
    SignalID.LEAGUE_STAKES: compute_league_stakes_signal,
    SignalID.BOUNCE_BACK: compute_bounce_back_signal,
    SignalID.MOMENTUM_PRESSURE: compute_momentum_pressure_signal,
    SignalID.FIRST_HALF_GOAL_TIMING: compute_1h_goal_timing_signal,
    SignalID.FIRST_HALF_OVER05: compute_1h_over05_signal,
    SignalID.FAST_STARTERS: compute_fast_starters_signal,
    SignalID.HOME_PRESSURE_START: compute_home_pressure_signal,
    SignalID.LINEUP: compute_lineups_signal,
    # Add more signal handlers as needed


}
