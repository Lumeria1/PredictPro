#!/usr/bin/env python3
"""
over15_test.py

Standalone test harness for Signal 2 (Over 1.5 Goals Rate).
Fill in HOME_ID, AWAY_ID, LEAGUE_ID, KICKOFF below then run:

    python over15_test.py
"""

import os
import sys
import requests
from datetime import datetime

# ─── USER CONFIG ───────────────────────────────────────────────────────────────
API_KEY    = "b47854ddeca91f45d4d56db66fd9209b"
API_BASE   = "https://v3.football.api-sports.io/"
HOME_ID   = 120     # e.g. Comunicaciones = 1013 or your own
AWAY_ID   = 129     # e.g. Sportivo Italiano = 2177 or your own
LEAGUE_ID = 71      # e.g. Argentina Primera B = 114
KICKOFF   = "2025-05-31T19:30:00"  # ISO datetime of the fixture

# If your league runs Jan–Dec, include it here:
CALENDAR_SEASON_LEAGUES = {
    103,   # Norway Eliteserien
    113,   # Sweden Allsvenskan
    71,    # Brazil Serie A
    131,   # Argentina Primera Division
    129,   # Argentina Primera Nacional
    293,   # South Korea K League 2
    # … add other calendar-year competitions here
}

# ──────────────────────────────────────────────────────────────────────────────

HEADERS = {"x-apisports-key": API_KEY}

def infer_season(league_id: int, kickoff: datetime) -> int:
    if league_id in CALENDAR_SEASON_LEAGUES:
        return kickoff.year
    return kickoff.year - 1 if kickoff.month < 8 else kickoff.year

def get_last5_side(team_id: int, league_id: int, season: int, side: str) -> list[dict]:
    """
    Grab the last 15 fixtures, filter by side, then return the most
    recent 5 where the given team was HOME or AWAY.
    """
    resp = requests.get(
        f"{API_BASE}fixtures",
        headers=HEADERS,
        params={"team": team_id, "league": league_id, "season": season, "last": 15},
    )
    if resp.status_code == 403:
        print("❗  API-Football: 403 Forbidden – free-tier limit reached.")
        return []
    resp.raise_for_status()
    all_fx = resp.json().get("response", []) or []
    # keep only fixtures where this team was on the requested side
    side_fx = [f for f in all_fx if f["teams"][side]["id"] == team_id]
    return side_fx[:5]

def compute_over15_signal(home_id:int, away_id:int, league_id:int, kickoff:datetime):
    season = infer_season(league_id, kickoff)
    print(f"\n🚩 Season: {season}")

    home5 = get_last5_side(home_id, league_id, season, "home")
    away5 = get_last5_side(away_id, league_id, season, "away")

    print(f"▶️  Home fixtures fetched ({len(home5)}):")
    for f in home5:
        d = f["fixture"]["date"]
        g = f["goals"]
        print(f"   • {d} → {g['home']}-{g['away']}")

    print(f"\n▶️  Away fixtures fetched ({len(away5)}):")
    for f in away5:
        d = f["fixture"]["date"]
        g = f["goals"]
        print(f"   • {d} → {g['home']}-{g['away']}")

    # Combine and drop any unplayed games
    combined = [*home5, *away5]
    played = [f for f in combined if f["goals"]["home"] is not None and f["goals"]["away"] is not None]
    if len(played) < 10:
        print(f"\n⚠️  Only {len(played)} completed games, need 10 for Over 1.5.")
        return

    over_count = sum(1 for f in played if (f["goals"]["home"] + f["goals"]["away"]) >= 2)
    rate       = over_count / len(played)
    status     = "Y" if rate >= 0.8 else "N" if rate < 0.6 else "-"

    print(f"\n🏁 Over 1.5 signal → Status={status}, Rate={rate:.0%} ({over_count}/{len(played)})\n")

def main():
    try:
        ko = datetime.fromisoformat(KICKOFF)
    except ValueError:
        print("❌  KICKOFF must be ISO-8601, e.g. 2025-05-27T19:30:00")
        sys.exit(1)

    print(f"\n=== Over 1.5 Test: {HOME_ID} vs {AWAY_ID} on {KICKOFF} ===")
    compute_over15_signal(HOME_ID, AWAY_ID, LEAGUE_ID, ko)

if __name__ == "__main__":
    main()
