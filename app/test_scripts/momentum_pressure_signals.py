#!/usr/bin/env python3
"""
signal8_test.py

Standalone test harness for Signal 8: Motivation – Momentum/Pressure.
Fill in HOME_ID, AWAY_ID, LEAGUE_ID, KICKOFF below,
then run:

    python signal8_test.py
"""

import sys
import requests
from datetime import datetime
from typing import Any, Dict, List

# ─── USER CONFIG — fill these before running ────────────────────────────────
API_KEY   = "b47854ddeca91f45d4d56db66fd9209b"
API_BASE  = "https://v3.football.api-sports.io/"
HOME_ID   = 2752    # e.g. Busan 
AWAY_ID   = 2758    # e.g. Ansan Greeners 
LEAGUE_ID = 293     # e.g. South Korea K League 2 
KICKOFF   = "2025-06-07T19:30:00"  # ISO datetime of the fixture
# ─────────────────────────────────────────────────────────────────────────────
# Mapping of league_id → number of relegated teams
RELEGATION_CUTOFFS = {
    131: 1,  # Argentina Primera B Metropolitana – bottom team relegated
    129: 2,  # Argentina Primera Nacional – bottom two teams relegated
    188: 0,  # Australia A-League – no relegation system
    218: 1,  # Austria Bundesliga – bottom team relegated
    144: 1,  # Belgium Jupiler Pro League – bottom team relegated
    71: 4,   # Brazil Serie A – bottom four teams relegated
    172: 2,  # Bulgaria Parva Liga – bottom two teams relegated
    210: 1,  # Croatia HNL – bottom team relegated
    318: 3,  # Cyprus League – bottom three teams relegated
    345: 1,  # Czech Republic Chance Liga – bottom team relegated
    40: 3,   # England Championship – bottom three teams relegated
    41: 4,   # England League One – bottom four teams relegated
    43: 4,   # England National League – bottom four teams relegated
    39: 3,   # England Premier League – bottom three teams relegated
    61: 2,   # France Ligue 1 – bottom two teams relegated
    62: 4,   # France Ligue 2 – bottom four teams relegated
    78: 2,   # Germany Bundesliga – bottom two teams relegated
    197: 2,  # Greece Super League – bottom two teams relegated
    271: 2,  # Hungary OTP Bank Liga – bottom two teams relegated
    323: 0,  # India ISL – no relegation system
    382: 2,  # Israel Leumit League – bottom two teams relegated
    383: 2,  # Israel Ligat ha'Al – bottom two teams relegated
    135: 3,  # Italy Serie A – bottom three teams relegated
    89: 2,   # Netherlands Eerste Divisie – bottom two teams relegated
    88: 1,   # Netherlands Eredivisie – bottom team relegated
    408: 1,  # Northern Ireland NIFL Premiership – bottom team relegated
    94: 2,   # Portugal Liga – bottom two teams relegated
    308: 2,  # Saudi Division 1 – bottom two teams relegated
    307: 2,  # Saudi Professional League – bottom two teams relegated
    180: 1,  # Scotland Championship – bottom team relegated
    184: 2,  # Scotland League Two – bottom two teams relegated
    179: 1,  # Scotland Premiership – bottom team relegated
    286: 2,  # Serbia Super Liga – bottom two teams relegated
    292: 2,  # South Korea K League 1 – bottom two teams relegated
    293: 2,  # South Korea K League 2 – bottom two teams relegated
    373: 1,  # Slovenia Prva Liga – bottom team relegated
    140: 3,  # Spain LaLiga – bottom three teams relegated
    141: 4,  # Spain LaLiga 2 – bottom four teams relegated
    207: 1,  # Switzerland Super League – bottom team relegated
    204: 3,  # Turkey 1 Lig – bottom three teams relegated
    203: 4,  # Turkey Super Lig – bottom four teams relegated
    301: 2,  # UAE League – bottom two teams relegated
    333: 2,  # Ukraine Premier League – bottom two teams relegated
    103: 2,  # Norway Eliteserien – bottom two teams relegated
    113: 1,  # Sweden Allsvenskan – bottom team relegated
    98: 2,   # Japan J1 League – bottom two teams relegated
}
CALENDAR_SEASON_LEAGUES = {
    103,   # Norway Eliteserien
    113,   # Sweden Allsvenskan
    71,    # Brazil Serie A
    131,   # Argentina Primera B
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
        print("❗  API-Football: 403 Forbidden – free-tier limit reached.")
        return []
    resp.raise_for_status()
    return resp.json().get("response", []) or []


class Fixture:
    def __init__(self, home: int, away: int, league: int, kickoff_dt: datetime):
        self.home_team_api_id = home
        self.away_team_api_id = away
        self.league_api_id    = league
        self.kickoff          = kickoff_dt


def compute_momentum_pressure_signal(fx: Fixture):
    # 1) Infer season
    ko = fx.kickoff
    season = infer_season(fx.league_api_id, ko)
    if not season:
        print("❌ Could not infer season from kickoff date")
        sys.exit(1)
    
    # 2) Check for Home-Opener by fetching recent fixtures and filtering on “home”
    last_fixtures = get_last_n_team_fixtures(fx.home_team_api_id, fx.league_api_id, season, n=20)
    # Keep only those played (non-null goals) and where this team was the HOME side, and date < kickoff
    prior_home = []
    for f in last_fixtures:
        goals = f.get("goals", {})
        if goals.get("home") is None or goals.get("away") is None:
            continue
        if f["teams"]["home"]["id"] != fx.home_team_api_id:
            continue
        # Compare fixture date to kickoff
        api_dt = datetime.fromisoformat(f["fixture"]["date"])
        fixture_dt = api_dt.replace(tzinfo=None)
        prior_home.append(f)
    if not prior_home:
        status = "Y"
        note = "Home-opener: No previous home matches this season"
        print(f"\n🏁 Momentum/Pressure signal → Status={status}, Note='{note}'\n")
        return

    # 3) Check for Unbeaten Run ≥ 3 for Home Team
    # Fetch the last 5 played fixtures (home OR away) for home team
    last5 = get_last_n_team_fixtures(fx.home_team_api_id, fx.league_api_id, season, n=5)
    played_fixtures = [
        f for f in last5
        if f.get("goals", {}).get("home") is not None
           and f.get("goals", {}).get("away") is not None
    ]
    if len(played_fixtures) < 3:
        status = "-"
        note = "Less than 3 played matches → cannot assess unbeaten run"
        print(f"\n🏁 Momentum/Pressure signal → Status={status}, Note='{note}'\n")
        return

    unbeaten_count = 0
    # Check most recent 3 played fixtures in order they were returned (API returns sorted by date descending)
    for f in played_fixtures[:3]:
        goals = f.get("goals", {})
        home_id_prev = f["teams"]["home"]["id"]
        away_id_prev = f["teams"]["away"]["id"]
        home_goals   = goals["home"]
        away_goals   = goals["away"]

        # Determine result from the home-team-ID’s perspective
        if home_id_prev == fx.home_team_api_id:
            # They were the home side in that fixture
            if home_goals >= away_goals:
                unbeaten_count += 1
        else:
            # They were the away side in that fixture
            if away_goals >= home_goals:
                unbeaten_count += 1

    if unbeaten_count >= 3:
        status = "Y"
        note = "Home team is on a 3-match unbeaten run"
        print(f"\n🏁 Momentum/Pressure signal → Status={status}, Note='{note}'\n")
        return

    # 4) Otherwise: Neutral
    status = "-"
    note = "No unbeaten run ≥3 and not a home-opener → Neutral"
    print(f"\n🏁 Momentum/Pressure signal → Status={status}, Note='{note}'\n")


def main():
    try:
        kickoff_dt = datetime.fromisoformat(KICKOFF)
    except ValueError:
        print("❌ KICKOFF must be ISO-8601, e.g. 2025-06-01T19:30:00")
        sys.exit(1)

    fx = Fixture(HOME_ID, AWAY_ID, LEAGUE_ID, kickoff_dt)
    compute_momentum_pressure_signal(fx)


if __name__ == "__main__":
    main()