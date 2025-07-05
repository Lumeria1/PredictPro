#!/usr/bin/env python3
"""
signal10_1h_over05.py

Standalone test harness for Signal 10: 1H Over 0.5 Rate.
Fill in HOME_ID, AWAY_ID, LEAGUE_ID, KICKOFF below,
then run:

    python signal10_1h_over05.py
"""

import sys
import requests
from datetime import datetime
from typing import Any, Dict, List

# ─── USER CONFIG — fill these in before running ────────────────────────────────
API_KEY   = "b47854ddeca91f45d4d56db66fd9209b"
API_BASE  = "https://v3.football.api-sports.io/"
HOME_ID   = 468     # e.g. Brown Adrogue 
AWAY_ID   = 481     # e.g. Villa Dalmine 
LEAGUE_ID = 131     # e.g. Argentina Primera B - Apertura 
KICKOFF   = "2025-06-07T19:30:00"  # ISO datetime of the fixture
# ─────────────────────────────────────────────────────────────────────────────

# Leagues running on calendar‐year
CALENDAR_SEASON_LEAGUES = {
    71,   # Brazil Serie A
    98,   # Japan J1 League
    103,  # Norway Eliteserien
    113,  # Sweden Allsvenskan
    129,  # Argentina Primera Nacional
    131,  # Argentina Primera B
    188,  # Australia A-League
    293   # South Korea K League 2
}

HEADERS = {"x-apisports-key": API_KEY}


def infer_season(league_id: int, kickoff_dt: datetime) -> int:
    """
    Return kickoff.year for calendar‐year leagues; otherwise
    return kickoff.year - 1 if month < 8 else kickoff.year.
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


def get_fixture_events(fixture_id: int) -> List[Dict[str, Any]]:
    """
    Fetch all event objects for a given fixture.
    """
    resp = requests.get(
        f"{API_BASE}fixtures/events",
        headers=HEADERS,
        params={"fixture": fixture_id},
    )
    if resp.status_code == 403:
        print("❗ API-Football: 403 Forbidden – free-tier limit reached for events.")
        return []
    resp.raise_for_status()
    return resp.json().get("response", []) or []


def parse_minute(minute_str: Any) -> int:
    """
    Convert a minute field (e.g. 45 or '45+1') to an integer floor value.
    If minute_str is invalid, return a large number.
    """
    try:
        m = str(minute_str)
        if "+" in m:
            return int(m.split("+")[0])
        return int(m)
    except (ValueError, TypeError):
        return 999


class FixtureInfo:
    def __init__(self, home: int, away: int, league: int, kickoff_dt: datetime):
        self.home_team_api_id = home
        self.away_team_api_id = away
        self.league_api_id    = league
        self.kickoff          = kickoff_dt


def compute_1h_over05_signal(fx: FixtureInfo):
    # 1) Infer season
    ko = fx.kickoff
    season = infer_season(fx.league_api_id, ko)
    if not season:
        print("❌ Could not infer season from kickoff date")
        sys.exit(1)

    # 2) Fetch last 5 fixtures for home + last 5 for away
    home5 = get_last_n_team_fixtures(fx.home_team_api_id, fx.league_api_id, season, n=5)
    away5 = get_last_n_team_fixtures(fx.away_team_api_id, fx.league_api_id, season, n=5)

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
    elif positive_count <= 5:
        status = "N"
        note = f"{positive_count}/10 had a 1H goal → Red"
    else:
        status = "-"
        note = f"{positive_count}/10 had a 1H goal → Neutral"

    print(f"\n🏁 1H Over 0.5 signal → Status={status}, Note='{note}'\n")


def main():
    try:
        kickoff_dt = datetime.fromisoformat(KICKOFF)
    except ValueError:
        print("❌ KICKOFF must be ISO-8601, e.g. 2025-06-01T19:30:00")
        sys.exit(1)

    fx = FixtureInfo(HOME_ID, AWAY_ID, LEAGUE_ID, kickoff_dt)
    compute_1h_over05_signal(fx)


if __name__ == "__main__":
    main()
