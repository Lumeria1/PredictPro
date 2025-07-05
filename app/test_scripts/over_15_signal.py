#!/usr/bin/env python3
"""
signal2_test.py

Standalone test harness for Signal 2: Over 1.5 Goals Rate.
Fill in HOME_ID, AWAY_ID, LEAGUE_ID, KICKOFF below
then simply run:

    python signal2_test.py
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
    Return kickoff.year for calendar‐year leagues, otherwise
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


def get_last5_team_fixtures(team_id: int, league_id: int, season: int) -> list[dict]:
    """
    Fetch up to the last 15 fixtures, filter out unplayed fixtures,
    and return the most recent 5 played.
    """
    fixtures = get_last_n_team_fixtures(team_id, league_id, season, n=15)
    # Exclude fixtures with missing scores (unplayed)
    played = [f for f in fixtures if f.get("goals", {}).get("home") is not None
                                             and f.get("goals", {}).get("away") is not None]
    return played[:5]


class Fixture:
    def __init__(self, home, away, league, kickoff_dt):
        self.home_team_api_id = home
        self.away_team_api_id = away
        self.league_api_id    = league
        self.kickoff          = kickoff_dt


def compute_over15_signal(fx: Fixture):
    # 1) infer season
    ko = fx.kickoff
    season = infer_season(fx.league_api_id, ko)
    if not season:
        print("❌  Could not infer season from kickoff date")
        sys.exit(1)

    # 2) fetch last 5 valid fixtures for each team
    home5 = get_last5_team_fixtures(fx.home_team_api_id, fx.league_api_id, season)
    away5 = get_last5_team_fixtures(fx.away_team_api_id, fx.league_api_id, season)

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


def main():
    try:
        kickoff_dt = datetime.fromisoformat(KICKOFF)
    except ValueError:
        print("❌  KICKOFF must be ISO-8601, e.g. 2025-05-27T19:30:00")
        sys.exit(1)

    fx = Fixture(HOME_ID, AWAY_ID, LEAGUE_ID, kickoff_dt)
    compute_over15_signal(fx)


if __name__ == "__main__":
    main()
