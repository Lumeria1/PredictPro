#!/usr/bin/env python3
"""
signal6_test.py

Standalone test harness for Signal 6: Motivation – League Stakes.
Fill in HOME_ID, AWAY_ID, LEAGUE_ID, KICKOFF below,
then run:

    python signal6_test.py
"""

import sys
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional

# ─── USER CONFIG — fill these before running ────────────────────────────────
API_KEY   = "b47854ddeca91f45d4d56db66fd9209b"
API_BASE  = "https://v3.football.api-sports.io/"
HOME_ID   = 7061    # e.g. Cheongju 
AWAY_ID   = 2753    # e.g. Asan 
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

# Default threshold for top‐4 (continental spots) in all leagues unless overridden
TOP4_THRESHOLD = 4

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


def get_standings(league_id: int, season: int) -> List[Dict[str, Any]]:
    """
    Fetch the current standings for a given league and season.
    Returns "response"[0]["league"]["standings"][0] — a list of dicts containing
    'rank', 'team':{'id', 'name'}, 'all':{'played':X}, etc.
    """
    resp = requests.get(
        
        f"{API_BASE}standings",
        headers=HEADERS,
        params={"league": league_id, "season": season},
    )
    if resp.status_code == 403:
        print("❗ API-Football: 403 Forbidden – free-tier limit reached.")
        return []
    resp.raise_for_status()
    data = resp.json().get("response", [])
    if not data:
        return []
    # There may be multiple “groups” (e.g., Clausura vs Apertura).
    all_groups = data[0].get("league", {}).get("standings", [])
    for group in all_groups:
        # If at least one team has > 0 matches played, assume this is the active table
        if any(entry.get("all", {}).get("played", 0) > 0 for entry in group):
            return group

    # Fallback: just return the first group if none have played >0
    return all_groups[0] if all_groups else []


class Fixture:
    def __init__(self, home: int, away: int, league: int, kickoff_dt: datetime):
        self.home_team_api_id = home
        self.away_team_api_id = away
        self.league_api_id    = league
        self.kickoff          = kickoff_dt


def compute_league_stakes_signal(fx: Fixture):
    # 1) infer season
    ko = fx.kickoff
    season = infer_season(fx.league_api_id, ko)
    if not season:
        print("❌ Could not infer season from kickoff date")
        sys.exit(1)

    # 2) fetch standings and find home/away entries
    standings = get_standings(fx.league_api_id, season)
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

    home_data = pos_map.get(fx.home_team_api_id)
    away_data = pos_map.get(fx.away_team_api_id)

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
    releg_n = RELEGATION_CUTOFFS.get(fx.league_api_id, 3)  # default to bottom 3
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

    print(f"\n🏁 League Stakes signal → Status={status}, Note='{note}'\n")


def main():
    try:
        kickoff_dt = datetime.fromisoformat(KICKOFF)
    except ValueError:
        print("❌ KICKOFF must be ISO-8601, e.g. 2025-06-01T19:30:00")
        sys.exit(1)

    fx = Fixture(HOME_ID, AWAY_ID, LEAGUE_ID, kickoff_dt)
    compute_league_stakes_signal(fx)


if __name__ == "__main__":
    main()
