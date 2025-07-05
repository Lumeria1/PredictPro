#!/usr/bin/env python3
"""
signal13_home_pressure_start.py

Standalone test harness for Signal 13: Home Pressure Start.
Uses the home team's last 3 overall fixtures to determine “pressure”:

  - Green (Y) if lost ≥ 2 of last 3
  - Red (N) if won all 3
  - Neutral (-) otherwise

Fill in HOME_ID, AWAY_ID, LEAGUE_ID, KICKOFF below,
then simply run:

    python signal13_home_pressure_start.py
"""

import sys
import requests
from datetime import datetime
from typing import Any, Dict, List

# ─── USER CONFIG — fill these before running ────────────────────────────────
API_KEY   = "b47854ddeca91f45d4d56db66fd9209b"
API_BASE  = "https://v3.football.api-sports.io/"
HOME_ID   = 130     # e.g. Gremio
AWAY_ID   = 131     # e.g. Corinthians
LEAGUE_ID = 71      # e.g. Brazil Serie A Betano
KICKOFF   = "2025-06-07T19:30:00"  # ISO datetime of the fixture
# ─────────────────────────────────────────────────────────────────────────────

# Leagues running on calendar-year
CALENDAR_SEASON_LEAGUES = {
    71,   # Brazil Serie A
    98,   # Japan J1 League
    103,  # Norway Eliteserien
    113,  # Sweden Allsvenskan
    129,  # Argentina Primera Nacional
    131,  # Argentina Primera B
    188,  # Australia A-League
    293,   # South Korea K League 2
    114,  # Sweden Suprettan
}

HEADERS = {"x-apisports-key": API_KEY}


def infer_season(league_id: int, kickoff_dt: datetime) -> int:
    """
    Return kickoff.year for calendar-year leagues; otherwise
    kickoff.year - 1 if kickoff.month < 8 else kickoff.year.
    """
    if league_id in CALENDAR_SEASON_LEAGUES:
        return kickoff_dt.year
    return kickoff_dt.year - 1 if kickoff_dt.month < 8 else kickoff_dt.year


def get_last_n_team_fixtures(
    team_id: int,
    league_id: int,
    season: int,
    n: int
) -> List[Dict[str, Any]]:
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
        },
    )
    if resp.status_code == 403:
        print("❗ API-Football: 403 Forbidden – free-tier limit reached.")
        return []
    resp.raise_for_status()
    return resp.json().get("response", []) or []


class FixtureInfo:
    def __init__(self, home: int, away: int, league: int, kickoff_dt: datetime):
        self.home_team_api_id = home
        self.away_team_api_id = away
        self.league_api_id    = league
        self.kickoff          = kickoff_dt


def compute_home_pressure_signal(fx: FixtureInfo):
    # 1) Infer season
    ko = fx.kickoff
    season = infer_season(fx.league_api_id, ko)
    if not season:
        print("❌ Could not infer season from kickoff date")
        sys.exit(1)

    # 2) Fetch last 3 fixtures (home OR away) for the home team
    last3 = get_last_n_team_fixtures(fx.home_team_api_id, fx.league_api_id, season, n=3)
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

        if home_id_prev == fx.home_team_api_id:
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
    elif wins == 3:
        status = "N"
        note = f"Won all 3 → No pressure (Red)"
    else:
        status = "-"
        note = f"Wins={wins}, Losses={losses} → Neutral"

    print(f"\n🏁 Home Pressure Start signal → Status={status}, Note='{note}'\n")


def main():
    try:
        kickoff_dt = datetime.fromisoformat(KICKOFF)
    except ValueError:
        print("❌ KICKOFF must be ISO-8601, e.g. 2025-06-01T19:30:00")
        sys.exit(1)

    fx = FixtureInfo(HOME_ID, AWAY_ID, LEAGUE_ID, kickoff_dt)
    compute_home_pressure_signal(fx)


if __name__ == "__main__":
    main()
