import requests
from .config import settings
from datetime import datetime
from typing import List, Dict, Any
# app/api_football.py

# Leagues running on calendar-year
CALENDAR_SEASON_LEAGUES = {
    71,   # Brazil Serie A
    98,   # Japan J1 League
    103,  # Norway Eliteserien
    113,  # Sweden Allsvenskan
    129,  # Argentina Primera Nacional
    131,  # Argentina Primera B
    188,  # Australia A-League
    293,  # South Korea K League 2
    114,  # Sweden Suprettan
    104,  # Norway OBOS-ligaen
    # Add other calendar-year competitions here
}

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

# Default threshold for top‐4 (continental spots) in all leagues unless overridden
TOP4_THRESHOLD = 4

HEADERS = {"x-apisports-key": settings.API_FOOTBALL_KEY}
BASE = settings.API_FOOTBALL_BASE


def infer_season(league_id: int, kickoff_dt: datetime) -> int:
    """
    Return kickoff.year for calendar-year leagues; otherwise
    return kickoff.year - 1 if kickoff.month < 8 else kickoff.year.
    """
    if league_id in CALENDAR_SEASON_LEAGUES:
        return kickoff_dt.year
    return kickoff_dt.year - 1 if kickoff_dt.month < 8 else kickoff_dt.year

def get_last_n_team_fixtures(team_id: int, league_id: int, season: int, n: int) -> list:
    """
    Fetch up to the last n fixtures (home OR away) for the given team.
    """
    resp = requests.get(
        f"{BASE}fixtures",
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

def get_last5_home_fixtures(team_id: int, league_id: int, season: int) -> list[dict]:
    """
    Fetch up to the last 15 fixtures, filter out unplayed fixtures,
    then keep only those where this team was HOME, and return the most recent 5 played.
    """
    fixtures = get_last_n_team_fixtures(team_id, league_id, season, n=15)
    # Exclude fixtures with missing scores (unplayed), AND ensure they count as HOME
    played_home = [
        f for f in fixtures
        if f.get("goals", {}).get("home") is not None
        and f.get("goals", {}).get("away") is not None
        and f.get("teams", {}).get("home", {}).get("id") == team_id
    ]
    return played_home[:5]


def get_last5_away_fixtures(team_id: int, league_id: int, season: int) -> list[dict]:
    """
    Fetch up to the last 15 fixtures, filter out unplayed fixtures,
    then keep only those where this team was AWAY, and return the most recent 5 played.
    """
    fixtures = get_last_n_team_fixtures(team_id, league_id, season, n=15)
    # Exclude fixtures with missing scores (unplayed), AND ensure they count as AWAY
    played_away = [
        f for f in fixtures
        if f.get("goals", {}).get("home") is not None
        and f.get("goals", {}).get("away") is not None
        and f.get("teams", {}).get("away", {}).get("id") == team_id
    ]
    return played_away[:5]

def get_standings(league_id: int, season: int) -> List[Dict[str, Any]]:
    """
    Fetch the current standings for a given league and season.
    Returns "response"[0]["league"]["standings"][0] — a list of dicts containing
    'rank', 'team':{'id', 'name'}, 'all':{'played':X}, etc.
    """
    resp = requests.get(
        
        f"{BASE}standings",
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

def get_fixture_events(fixture_id: int) -> List[Dict[str, Any]]:
    """
    Fetch all event objects for a given fixture.
    """
    resp = requests.get(
        f"{BASE}fixtures/events",
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
    Convert a minute field (e.g. 30 or '45+1') to an integer floor value.
    If minute_str is None or invalid, return a large number so it's ignored.
    """
    try:
        m = str(minute_str)
        if "+" in m:
            return int(m.split("+")[0])
        return int(m)
    except (ValueError, TypeError):
        return 999


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

def get_lineups_for_fixture(fixture_id: int) -> List[Dict[str, Any]]:
    """
    Fetch lineups for a given fixture.
    """
    resp = requests.get(
        f"{BASE}fixtures/lineups",
        headers=HEADERS,
        params={"fixture": fixture_id},
    )
    if resp.status_code == 403:
        print("❗ API-Football: 403 Forbidden – free-tier limit reached for lineups.")
        return []
    resp.raise_for_status()
    return resp.json().get("response", []) or []