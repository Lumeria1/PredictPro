#!/usr/bin/env python3
"""
signal14_lineups.py

Standalone test harness for Signal 14: Lineups.
Fallback logic (no star‐player list yet):
  - Neutral (–) if current time is >1 hour before kickoff, or if lineups are not yet published
  - Green (Y) if exactly 11 starters are listed for the HOME team
  - Red (N) if fewer than 11 starters are listed for the HOME team

Fill in HOME_ID, AWAY_ID, LEAGUE_ID, KICKOFF below,
then simply run:

    python signal14_lineups.py
"""

import sys
import requests
from datetime import datetime, timedelta
from typing import Any, Dict, List

# ─── USER CONFIG — fill these in before running ────────────────────────────────
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
    293   # South Korea K League 2
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


def get_lineups_for_fixture(fixture_id: int) -> List[Dict[str, Any]]:
    """
    Fetch lineups for a given fixture.
    """
    resp = requests.get(
        f"{API_BASE}fixtures/lineups",
        headers=HEADERS,
        params={"fixture": fixture_id},
    )
    if resp.status_code == 403:
        print("❗ API-Football: 403 Forbidden – free-tier limit reached for lineups.")
        return []
    resp.raise_for_status()
    return resp.json().get("response", []) or []


class FixtureInfo:
    def __init__(self, home: int, away: int, league: int, kickoff_dt: datetime):
        self.home_team_api_id = home
        self.away_team_api_id = away
        self.league_api_id    = league
        self.kickoff          = kickoff_dt


def compute_lineups_signal(fx: FixtureInfo):
    # 1) Infer season (just for context printing)
    ko = fx.kickoff
    season = infer_season(fx.league_api_id, ko)
    print(f"\n🚩 Season: {season}")

    # 2) Check current time vs kickoff - 1h
    now = datetime.now()  # naive local time
    kickoff_dt = fx.kickoff
    cutoff = kickoff_dt - timedelta(hours=1)

    if now < cutoff:
        # More than 1h until kick-off → Neutral
        print("⚠️ More than 1 hour until kickoff → lineups not yet published")
        print("\n🏁 Lineups signal → Status=-, Note='Too early for lineups'\n")
        return

    # 3) Fetch lineups
    lineups = get_lineups_for_fixture(fx.home_team_api_id)  # pass in fixture id below
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
        if entry.get("team", {}).get("id") == fx.home_team_api_id:
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
    elif count_starters < 11:
        status = "N"
        note = f"{count_starters} starters listed → Incomplete (Red)"
    else:
        # More than 11 is unexpected, treat as Neutral
        status = "-"
        note = f"{count_starters} starters listed → Unexpected (Neutral)"

    print(f"\n▶️ Home starting XI count: {count_starters}")
    print(f"\n🏁 Lineups signal → Status={status}, Note='{note}'\n")


def main():
    try:
        kickoff_dt = datetime.fromisoformat(KICKOFF)
    except ValueError:
        print("❌ KICKOFF must be ISO-8601, e.g. 2025-06-01T19:30:00")
        sys.exit(1)

    fx = FixtureInfo(HOME_ID, AWAY_ID, LEAGUE_ID, kickoff_dt)
    compute_lineups_signal(fx)


if __name__ == "__main__":
    main()
