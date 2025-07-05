#!/usr/bin/env python3
"""
signal5_test.py

Standalone test harness for Signal 5: Home/Away Strength.
Fill in HOME_ID, AWAY_ID, LEAGUE_ID, KICKOFF below,
then simply run:

    python signal5_test.py
"""

import sys
import requests
from datetime import datetime

# ─── USER CONFIG ───────────────────────────────────────────────────────────────
API_KEY   = "b47854ddeca91f45d4d56db66fd9209b"
API_BASE  = "https://v3.football.api-sports.io/"
HOME_ID   = 468     # e.g. Brown Adrogue 
AWAY_ID   = 481     # e.g. Villa Dalmine 
LEAGUE_ID = 131     # e.g. Argentina Primera B 
KICKOFF   = "2025-05-31T19:30:00"  # ISO datetime of the fixture

# Competitions that run on a single calendar year:
CALENDAR_SEASON_LEAGUES = {
    103,   # Norway Eliteserien
    113,   # Sweden Allsvenskan
    71,    # Brazil Serie A
    131,   # Argentina Primera Division
    129,   # Argentina Primera Nacional
    293,   # South Korea K League 2
    # … add other calendar-year competitions here
}


HEADERS = {"x-apisports-key": API_KEY}


def infer_season(league_id: int, kickoff_dt: datetime) -> int:
    """
    Return kickoff.year for calendar‐year leagues; otherwise
    return the campaign start year (if kickoff.month<8 use year-1).
    """
    if league_id in CALENDAR_SEASON_LEAGUES:
        return kickoff_dt.year
    return kickoff_dt.year - 1 if kickoff_dt.month < 8 else kickoff_dt.year


def get_last_n_team_fixtures(team_id: int, league_id: int, season: int, n: int) -> list[dict]:
    """
    Fetch up to the last n fixtures (home OR away) for the given team.
    """
    resp = requests.get(
        f"{API_BASE}fixtures",
        headers=HEADERS,
        params={
            "team":   team_id,
            "league": league_id,
            "season": season,
            "last":   n,
        }
    )
    if resp.status_code == 403:
        print("❗  API-Football: 403 Forbidden – free-tier limit reached.")
        return []
    resp.raise_for_status()
    return resp.json().get("response", []) or []


def get_last5_home_fixtures(team_id: int, league_id: int, season: int) -> list[dict]:
    """
    Fetch up to the last 15 fixtures, filter out unplayed fixtures,
    then keep only those where this team was HOME, and return the most recent 5 played.
    """
    fixtures = get_last_n_team_fixtures(team_id, league_id, season, n=15)
    # Exclude fixtures with missing scores (unplayed), AND ensure they count as HOME
    played_home = [
        f for f in fixtures
        if f.get("goals", {}).get("home") is not None
        and f.get("goals", {}).get("away") is not None
        and f.get("teams", {}).get("home", {}).get("id") == team_id
    ]
    return played_home[:5]


def get_last5_away_fixtures(team_id: int, league_id: int, season: int) -> list[dict]:
    """
    Fetch up to the last 15 fixtures, filter out unplayed fixtures,
    then keep only those where this team was AWAY, and return the most recent 5 played.
    """
    fixtures = get_last_n_team_fixtures(team_id, league_id, season, n=15)
    # Exclude fixtures with missing scores (unplayed), AND ensure they count as AWAY
    played_away = [
        f for f in fixtures
        if f.get("goals", {}).get("home") is not None
        and f.get("goals", {}).get("away") is not None
        and f.get("teams", {}).get("away", {}).get("id") == team_id
    ]
    return played_away[:5]


class Fixture:
    def __init__(self, home, away, league, kickoff_dt):
        self.home_team_api_id = home
        self.away_team_api_id = away
        self.league_api_id    = league
        self.kickoff          = kickoff_dt


def compute_home_away_strength_signal(fx: Fixture):
    # 1) infer season
    ko = fx.kickoff
    season = infer_season(fx.league_api_id, ko)
    if not season:
        print("❌  Could not infer season from kickoff date")
        sys.exit(1)

    # 2) fetch last 5 HOME fixtures for home team, and last 5 AWAY fixtures for away team
    home5 = get_last5_home_fixtures(fx.home_team_api_id, fx.league_api_id, season)
    away5 = get_last5_away_fixtures(fx.away_team_api_id, fx.league_api_id, season)

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
    if status == "Y":
        note += " → Home strong, Away weak"
    elif status == "N":
        note += " → Home weak, Away strong"
    else:
        note += " → Neutral strength"
    print(f"\n🏁 Home/Away Strength signal → Status={status}, Note='{note}'\n")


def main():
    try:
        kickoff_dt = datetime.fromisoformat(KICKOFF)
    except ValueError:
        print("❌  KICKOFF must be ISO-8601, e.g. 2025-05-27T19:30:00")
        sys.exit(1)

    fx = Fixture(HOME_ID, AWAY_ID, LEAGUE_ID, kickoff_dt)
    compute_home_away_strength_signal(fx)


if __name__ == "__main__":
    main()
