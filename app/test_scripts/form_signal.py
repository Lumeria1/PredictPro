#!/usr/bin/env python3
"""
signal1_test.py

Standalone test harness for Signal 1 (Form).
Fill in HOME_ID, AWAY_ID, LEAGUE_ID, KICKOFF below
then simply run:

    python signal1_test.py
"""

import sys
import requests
from datetime import datetime

# ─── USER CONFIG — fill these in before running ────────────────────────────────
API_KEY   = "b47854ddeca91f45d4d56db66fd9209b"
API_BASE  = "https://v3.football.api-sports.io/"   # or your proxy
HOME_ID   = 2144    # e.g. kongsvinger
AWAY_ID   = 757     # e.g. Aalesund
LEAGUE_ID = 104     # e.g. Norway OBOS-LIGAEN
KICKOFF   = "2025-05-30T19:30:00"  # ISO datetime of the fixture
# ──────────────────────────────────────────────────────────────────────────────

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
    # Add other calendar-year competitions here
}

HEADERS = {"x-apisports-key": API_KEY}

def infer_season(league_id: int, kickoff: datetime) -> int:
    if league_id in CALENDAR_SEASON_LEAGUES:
        return kickoff.year
    return kickoff.year - 1 if kickoff.month < 8 else kickoff.year

def get_last_n_team_fixtures(team_id: int, league_id: int, season: int, n: int) -> list:
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


def get_last5_team_fixtures(team_id: int, league_id: int, season: int) -> list:
    """
    Fetch up to the last 15 fixtures, filter out unplayed fixtures,
    and return the most recent 5 played.
    """
    fixtures = get_last_n_team_fixtures(team_id, league_id, season, n=15)
    # Exclude fixtures with missing scores (unplayed)
    played = [f for f in fixtures
              if f.get("goals", {}).get("home") is not None
              and f.get("goals", {}).get("away") is not None]
    return played[:5]

class Fixture:
    def __init__(self, home, away, league, kickoff_dt):
        self.home_team_api_id = home
        self.away_team_api_id = away
        self.league_api_id    = league
        self.kickoff          = kickoff_dt

def compute_form_signal(fixture: Fixture):
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

def main():
    try:
        kickoff_dt = datetime.fromisoformat(KICKOFF)
    except ValueError:
        print("❌  KICKOFF must be ISO-8601, e.g. 2025-05-27T19:30:00")
        sys.exit(1)

    fx = Fixture(HOME_ID, AWAY_ID, LEAGUE_ID, kickoff_dt)
    compute_form_signal(fx)

if __name__ == "__main__":
    main()
