#!/usr/bin/env python3
"""
signal12_fast_starters.py

Standalone test harness for Signal 12: Fast Starters.
Checks whether the home team scored in the first half (≤45') in ≥ 4 of their last 5 matches.

Fill in HOME_ID, AWAY_ID, LEAGUE_ID, KICKOFF below,
then simply run:

    python signal12_fast_starters.py
"""

import sys
import requests
from datetime import datetime
from typing import Any, Dict, List

# ─── USER CONFIG — fill these before running ────────────────────────────────
API_KEY   = "b47854ddeca91f45d4d56db66fd9209b"
API_BASE  = "https://v3.football.api-sports.io/"
HOME_ID   = 365     # e.g. Orebro
AWAY_ID   = 6697    # e.g. Sandviken
LEAGUE_ID = 114     # e.g. Sweden Suprettan
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
    114  # Sweden Superettan
}

HEADERS = {"x-apisports-key": API_KEY}


def infer_season(league_id: int, kickoff_dt: datetime) -> int:
    """
    Return kickoff.year for calendar-year leagues; otherwise
    return kickoff.year - 1 if kickoff.month < 8 else kickoff.year.
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


def check_team_first_half_performance(fixtures: List[Dict[str, Any]], team_id: int, team_name: str) -> tuple:
    """
    Check the team's first half performance (goals scored and conceded).
    Returns (goals_scored_count, goals_conceded_count, missing_fixtures)
    """
    goals_scored_count = 0
    goals_conceded_count = 0
    missing = []
    
    print(f"\n📋 Analyzing {team_name} team's first half performance:")
    
    for i, fixture in enumerate(fixtures, 1):
        fid = fixture["fixture"]["id"]
        home_team = fixture["teams"]["home"]
        away_team = fixture["teams"]["away"]
        
        # Determine if our team was home or away in this fixture
        if home_team["id"] == team_id:
            team_role = "home"
            opponent = away_team["name"]
            opponent_id = away_team["id"]
        else:
            team_role = "away"
            opponent = home_team["name"]
            opponent_id = home_team["id"]
        
        events = get_fixture_events(fid)
        if not events:
            missing.append(fid)
            print(f"   {i}. vs {opponent} ({team_role}) - ❌ No events data")
            continue

        # Track goals scored and conceded
        goals_scored = []
        goals_conceded = []
        
        for event in events:
            if event.get("type") == "Goal":
                elapsed = event.get("time", {}).get("elapsed")
                if isinstance(elapsed, int) and 1 <= elapsed <= 45:
                    goal_team_id = event.get("team", {}).get("id")
                    player_name = event.get("player", {}).get("name", "Unknown")
                    
                    if goal_team_id == team_id:
                        # Team scored
                        goals_scored.append(f"{elapsed}' {player_name}")
                    elif goal_team_id == opponent_id:
                        # Team conceded
                        goals_conceded.append(f"{elapsed}' {player_name}")
        
        # Update counters
        if goals_scored:
            goals_scored_count += 1
        if goals_conceded:
            goals_conceded_count += 1
        
        # Display results for this fixture
        status_parts = []
        if goals_scored:
            status_parts.append(f"⚽ Scored: {', '.join(goals_scored)}")
        if goals_conceded:
            status_parts.append(f"🥅 Conceded: {', '.join(goals_conceded)}")
        
        if status_parts:
            status = " | ".join(status_parts)
            print(f"   {i}. vs {opponent} ({team_role}) - {status}")
        else:
            print(f"   {i}. vs {opponent} ({team_role}) - ⭕ No 1H goals (either way)")
    
    return goals_scored_count, goals_conceded_count, missing


class FixtureInfo:
    def __init__(self, home: int, away: int, league: int, kickoff_dt: datetime):
        self.home_team_api_id = home
        self.away_team_api_id = away
        self.league_api_id    = league
        self.kickoff          = kickoff_dt


def compute_fast_starters_signal(fx: FixtureInfo):
    # 1) Infer season
    ko = fx.kickoff
    season = infer_season(fx.league_api_id, ko)
    if not season:
        print("❌ Could not infer season from kickoff date")
        sys.exit(1)

    print(f"\n🚩 Season: {season}")
    print(f"🏠 Home Team ID: {fx.home_team_api_id}")
    print(f"✈️  Away Team ID: {fx.away_team_api_id}")

    # 2) Fetch last 5 fixtures for the HOME team
    home5 = get_last_n_team_fixtures(fx.home_team_api_id, fx.league_api_id, season, n=5)
    print(f"\n▶️  Home team last {len(home5)} fixtures:")
    for i, f in enumerate(home5, 1):
        dt = f["fixture"]["date"]
        g = f["goals"]
        home_team = f["teams"]["home"]["name"]
        away_team = f["teams"]["away"]["name"]
        print(f"   {i}. {dt[:10]} - {home_team} {g['home']}-{g['away']} {away_team} (ID: {f['fixture']['id']})")

    if len(home5) < 5:
        print("⚠️ Insufficient home team fixtures (need 5).")
        print("\n🏁 Fast Starters signal → Status=-, Note='Insufficient data'\n")
        return

    # 3) Fetch last 5 fixtures for the AWAY team
    away5 = get_last_n_team_fixtures(fx.away_team_api_id, fx.league_api_id, season, n=5)
    print(f"\n▶️  Away team last {len(away5)} fixtures:")
    for i, f in enumerate(away5, 1):
        dt = f["fixture"]["date"]
        g = f["goals"]
        home_team = f["teams"]["home"]["name"]
        away_team = f["teams"]["away"]["name"]
        print(f"   {i}. {dt[:10]} - {home_team} {g['home']}-{g['away']} {away_team} (ID: {f['fixture']['id']})")

    if len(away5) < 5:
        print("⚠️ Insufficient away team fixtures (need 5).")
        print("\n🏁 Fast Starters signal → Status=-, Note='Insufficient data'\n")
        return

    # 4) Check HOME team's first half performance
    home_scored_count, home_conceded_count, home_missing = check_team_first_half_performance(
        home5, fx.home_team_api_id, "Home"
    )
    
    if home_missing:
        print(f"\n⚠️ Missing events for home team fixture IDs: {home_missing}")
        print("   → Counting them as 'no 1H activity' by default.")

    print(f"\n📊 Home team 1H performance:")
    print(f"   • Scored in {home_scored_count}/{len(home5)} matches")
    print(f"   • Conceded in {home_conceded_count}/{len(home5)} matches")

    # 5) Check AWAY team's first half performance  
    away_scored_count, away_conceded_count, away_missing = check_team_first_half_performance(
        away5, fx.away_team_api_id, "Away"
    )
    
    if away_missing:
        print(f"\n⚠️ Missing events for away team fixture IDs: {away_missing}")
        print("   → Counting them as 'no 1H activity' by default.")

    print(f"\n📊 Away team 1H performance:")
    print(f"   • Scored in {away_scored_count}/{len(away5)} matches")
    print(f"   • Conceded in {away_conceded_count}/{len(away5)} matches")

    # 6) Determine overall signal based on both teams' attacking and defensive performance
    print(f"\n🎯 SIGNAL ANALYSIS:")
    print(f"   • Home team 1H goals scored: {home_scored_count}/5")
    print(f"   • Home team 1H goals conceded: {home_conceded_count}/5")
    print(f"   • Away team 1H goals scored: {away_scored_count}/5")
    print(f"   • Away team 1H goals conceded: {away_conceded_count}/5")
    
    # Enhanced signal logic considering both scoring and defensive patterns
    home_attacking_strong = home_scored_count >= 4  # Strong attacking
    home_attacking_weak = home_scored_count <= 1    # Weak attacking
    home_defensive_weak = home_conceded_count >= 4  # Poor defense (good for goals)
    home_defensive_strong = home_conceded_count <= 1 # Strong defense (bad for goals)
    
    away_attacking_strong = away_scored_count >= 4
    away_attacking_weak = away_scored_count <= 1
    away_defensive_weak = away_conceded_count >= 4
    away_defensive_strong = away_conceded_count <= 1
    
    # Signal determination based on goal-scoring probability
    if (home_attacking_strong or away_defensive_weak or home_defensive_weak or away_attacking_strong) and not (home_defensive_strong and away_attacking_weak):
        status = "Y"
        factors = []
        if home_attacking_strong:
            factors.append("Home strong attack")
        if away_defensive_weak:
            factors.append("Away weak defense")
        if home_defensive_weak:
            factors.append("Home weak defense")
        if away_attacking_strong:
            factors.append("Away strong attack")
        note = f"H: {home_scored_count}⚽/{home_conceded_count}🥅, A: {away_scored_count}⚽/{away_conceded_count}🥅 → Fast Start Likely - {', '.join(factors)} (Green)"
        
    elif (home_attacking_weak and away_defensive_strong) or (home_defensive_strong and away_attacking_weak):
        status = "N"
        factors = []
        if home_attacking_weak:
            factors.append("Home weak attack")
        if away_defensive_strong:
            factors.append("Away strong defense")
        if home_defensive_strong:
            factors.append("Home strong defense")
        if away_attacking_weak:
            factors.append("Away weak attack")
        note = f"H: {home_scored_count}⚽/{home_conceded_count}🥅, A: {away_scored_count}⚽/{away_conceded_count}🥅 → Slow Start Likely - {', '.join(factors)} (Red)"
        
    else:
        status = "-"
        note = f"H: {home_scored_count}⚽/{home_conceded_count}🥅, A: {away_scored_count}⚽/{away_conceded_count}🥅 → Mixed Patterns (Neutral)"

    print(f"\n🏁 Fast Starters signal → Status={status}, Note='{note}'\n")


def main():
    try:
        kickoff_dt = datetime.fromisoformat(KICKOFF)
    except ValueError:
        print("❌ KICKOFF must be ISO-8601, e.g. 2025-06-01T19:30:00")
        sys.exit(1)

    fx = FixtureInfo(HOME_ID, AWAY_ID, LEAGUE_ID, kickoff_dt)
    compute_fast_starters_signal(fx)


if __name__ == "__main__":
    main()