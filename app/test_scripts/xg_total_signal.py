#!/usr/bin/env python3
"""
signal4_test.py

Standalone test harness for Signal 4: xG Total.
Fill in HOME_ID, AWAY_ID, LEAGUE_ID, KICKOFF below,
then run:

    python signal4_test.py
"""

import sys
import requests
from datetime import datetime
from typing import Optional, Tuple, List, Dict

# ─── USER CONFIG — fill these before running ────────────────────────────────
API_KEY   = "b47854ddeca91f45d4d56db66fd9209b"
API_BASE  = "https://v3.football.api-sports.io/"
HOME_ID   = 483     # e.g.  Los Andes 
AWAY_ID   = 1962    # e.g. Alvarado 
LEAGUE_ID = 129     # e.g. Argentina Primera Nacional 
KICKOFF   = "2025-05-31T19:30:00"  # ISO datetime of the fixture
# ─────────────────────────────────────────────────────────────────────────────

CALENDAR_SEASON_LEAGUES = {
    103,   # Norway Eliteserien
    113,   # Sweden Allsvenskan
    71,    # Brazil Serie A
    131,   # Argentina Primera B
    129,   # Argentina Primera Nacional
    # … add other calendar-year competitions here
}

HEADERS = {"x-apisports-key": API_KEY}


def infer_season(league_id: int, kickoff_dt: datetime) -> int:
    """
    Return kickoff.year for calendar‐year leagues; otherwise
    return the campaign start year (if kickoff.month < 8 use year–1).
    """
    if league_id in CALENDAR_SEASON_LEAGUES:
        return kickoff_dt.year
    return kickoff_dt.year - 1 if kickoff_dt.month < 8 else kickoff_dt.year


def get_last_n_team_fixtures(team_id: int, league_id: int, season: int, n: int) -> List[Dict]:
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


def get_fixture_xg(fixture_id: int) -> Optional[Tuple[float, float]]:
    """
    Call /fixtures/statistics?fixture=ID to retrieve xG for home and away.
    Returns (home_xg, away_xg) as floats, or None if not found.
    """
    resp = requests.get(
        f"{API_BASE}fixtures/statistics",
        headers=HEADERS,
        params={"fixture": fixture_id}
    )
    if resp.status_code == 403:
        print("❗  API-Football: 403 Forbidden – free-tier limit reached.")
        return None
    resp.raise_for_status()
    data = resp.json().get("response", []) or []
    if not data:
        return None

    stats = data[0].get("statistics", []) or []
    for stat in stats:
        if stat.get("type") == "Expected Goals":
            val = stat.get("value", {})
            try:
                hx = float(val.get("home", 0) or 0)
                ax = float(val.get("away", 0) or 0)
                return hx, ax
            except (TypeError, ValueError):
                return None

    return None


def get_last5_team_fixtures(team_id: int, league_id: int, season: int) -> List[Dict]:
    """
    Fetch up to the last 20 fixtures, filter out any unplayed fixtures
    or those missing xG data, then return the most recent 5 valid.
    """
    fixtures = get_last_n_team_fixtures(team_id, league_id, season, n=20)

    valid: List[Dict] = []
    for f in fixtures:
        goals = f.get("goals", {})
        if goals.get("home") is None or goals.get("away") is None:
            continue

        fid = f.get("fixture", {}).get("id")
        if fid is None:
            continue

        xg = get_fixture_xg(fid)
        if xg is None:
            continue

        # attach xG values for later use
        f["xg_home"] = xg[0]
        f["xg_away"] = xg[1]
        valid.append(f)

        if len(valid) >= 5:
            break

    return valid[:5]


class Fixture:
    def __init__(self, home: int, away: int, league: int, kickoff_dt: datetime):
        self.home_team_api_id = home
        self.away_team_api_id = away
        self.league_api_id    = league
        self.kickoff          = kickoff_dt


def compute_xg_total_signal(fx: Fixture):
    # 1) infer season
    ko = fx.kickoff
    season = infer_season(fx.league_api_id, ko)
    if not season:
        print("❌  Could not infer season from kickoff date")
        sys.exit(1)

    # 2) fetch last 5 valid fixtures for each team (filter out unplayed+no xG)
    home5 = get_last5_team_fixtures(fx.home_team_api_id, fx.league_api_id, season)
    away5 = get_last5_team_fixtures(fx.away_team_api_id, fx.league_api_id, season)

    print(f"\n🚩 Season: {season}")
    print(f"▶️  Last 5 HOME team fixtures ({len(home5)}):")
    for f in home5:
        dt = f["fixture"]["date"]
        g  = f["goals"]
        xh = f["xg_home"]
        xa = f["xg_away"]
        print(f"   • {dt} → {g['home']}-{g['away']} (Fixture ID: {f['fixture']['id']}, xG: {xh:.2f}+{xa:.2f})")

    print(f"\n▶️  Last 5 AWAY team fixtures ({len(away5)}):")
    for f in away5:
        dt = f["fixture"]["date"]
        g  = f["goals"]
        xh = f["xg_home"]
        xa = f["xg_away"]
        print(f"   • {dt} → {g['home']}-{g['away']} (Fixture ID: {f['fixture']['id']}, xG: {xh:.2f}+{xa:.2f})")

    # 3) Combine into a single list of up to 10 fixtures
    combined = home5 + away5
    print(f"\n🔗 Combined fixtures count: {len(combined)}")

    # If fewer than 10 played fixtures, warn and exit
    if len(combined) < 10:
        print("⚠️  Insufficient played fixtures to compute xG Total signal.")
        return

    # 4) Sum combined xG across all 10 matches
    total_xg = sum(f["xg_home"] + f["xg_away"] for f in combined)
    avg_xg = total_xg / len(combined)

    # 5) Determine status
    #    ✔️ Green if avg_xg ≥ 2.8
    #    ✘ White X if avg_xg ≤ 2.0
    #    ➖ Neutral if 2.1–2.7
    if avg_xg >= 2.8:
        status = "Y"
    elif avg_xg <= 2.0:
        status = "N"
    else:
        status = "-"

    note = f"Avg combined xG: {avg_xg:.2f} over {len(combined)} matches (Total xG: {total_xg:.2f})"
    print(f"\n🏁 xG Total signal → Status={status}, Note='{note}'\n")


def main():
    try:
        kickoff_dt = datetime.fromisoformat(KICKOFF)
    except ValueError:
        print("❌  KICKOFF must be ISO-8601, e.g. 2025-05-27T19:30:00")
        sys.exit(1)

    fx = Fixture(HOME_ID, AWAY_ID, LEAGUE_ID, kickoff_dt)
    compute_xg_total_signal(fx)


if __name__ == "__main__":
    main()
