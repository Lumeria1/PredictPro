#!/usr/bin/env python3
"""
signal7_test.py

Standalone test harness for Signal 7: Motivation – Bounce-Back.
Fill in HOME_ID, AWAY_ID, LEAGUE_ID, KICKOFF below,
then run:

    python signal7_test.py
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
    else:
        return kickoff_dt.year - 1 if kickoff_dt.month < 8 else kickoff_dt.year


def get_last_n_team_fixtures(team_id: int, league_id: int, season: int, n: int) -> List[Dict[str, Any]]:
    """
    Fetch up to the last n fixtures (home OR away) for the given team.
    """
    resp = requests.get(
        f"{API_BASE}fixtures",
        headers=HEADERS,
        params={"team": team_id, "league": league_id, "season": season, "last": n},
    )
    if resp.status_code == 403:
        print("❗ API-Football: 403 Forbidden – free-tier limit reached.")
        return []
    resp.raise_for_status()
    return resp.json().get("response", []) or []


class Fixture:
    def __init__(self, home: int, away: int, league: int, kickoff_dt: datetime):
        self.home_team_api_id = home
        self.away_team_api_id = away
        self.league_api_id    = league
        self.kickoff          = kickoff_dt


def compute_bounce_back_signal(fx: Fixture):
    # 1) infer season
    ko = fx.kickoff
    season = infer_season(fx.league_api_id, ko)
    if not season:
        print("❌ Could not infer season from kickoff date")
        sys.exit(1)

    # 2) fetch last 1 fixture for the home team
    last1 = get_last_n_team_fixtures(fx.home_team_api_id, fx.league_api_id, season, n=1)
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
    if home_id_prev == fx.home_team_api_id:
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
        note = f"Home team lost last time by {abs(margin)} and now at home → Bounce-Back!"
        print(f"\n🏁 Bounce-Back signal → Status={status}, Note='{note}'\n")
        return

    # 6) Check Red: home team won last match by ≥2
    if margin >= 2:
        status = "N"
        note = f"Home team won last time by {margin} (easy win) → No bounce-back needed"
        print(f"\n🏁 Bounce-Back signal → Status={status}, Note='{note}'\n")
        return

    # 7) Otherwise, Neutral
    status = "-"
    note = f"Last result margin={margin}, not qualifying for Bounce-Back or Red"
    print(f"\n🏁 Bounce-Back signal → Status={status}, Note='{note}'\n")


def main():
    try:
        kickoff_dt = datetime.fromisoformat(KICKOFF)
    except ValueError:
        print("❌ KICKOFF must be ISO-8601, e.g. 2025-06-01T19:30:00")
        sys.exit(1)

    fx = Fixture(HOME_ID, AWAY_ID, LEAGUE_ID, kickoff_dt)
    compute_bounce_back_signal(fx)


if __name__ == "__main__":
    main()
