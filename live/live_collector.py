"""
Live Match Collector for GoalFeed.
Fetches live match data from football API.

Supports multiple API providers:
- free-api-live-football-data (RapidAPI) - Free tier
- api-football-v1 (RapidAPI) - Paid tier
"""
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set
from datetime import datetime
from enum import Enum

import requests

from config import get_config, TOP_TEAMS

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of match events to track."""
    GOAL = "goal"
    RED_CARD = "red_card"
    FINAL = "final"
    PENALTY_MISS = "penalty_miss"
    VAR = "var"
    HALFTIME = "halftime"


class MatchStatus(str, Enum):
    """Match status codes from API."""
    NOT_STARTED = "NS"
    FIRST_HALF = "1H"
    HALFTIME = "HT"
    SECOND_HALF = "2H"
    EXTRA_TIME = "ET"
    PENALTY = "PEN"
    FINISHED = "FT"
    FINISHED_AET = "AET"
    BREAK = "BT"
    SUSPENDED = "SUSP"
    INTERRUPTED = "INT"
    POSTPONED = "PST"
    CANCELLED = "CANC"
    ABANDONED = "ABD"
    TECHNICAL_LOSS = "AWD"
    WALKOVER = "WO"
    LIVE = "LIVE"


@dataclass
class LiveEvent:
    """Represents a live match event."""
    match_id: str
    event_type: EventType
    minute: Optional[int] = None
    player: Optional[str] = None
    assist: Optional[str] = None
    detail: Optional[str] = None  # penalty, own goal, etc.
    team: Optional[str] = None
    
    # Score at time of event
    home_score: int = 0
    away_score: int = 0
    
    def __post_init__(self):
        if isinstance(self.event_type, str):
            self.event_type = EventType(self.event_type)


@dataclass
class LiveMatch:
    """Represents a live match."""
    match_id: str
    league_id: int
    league_name: str
    
    home_team: str
    away_team: str
    home_score: int = 0
    away_score: int = 0
    
    status: str = "NS"
    minute: Optional[int] = None
    
    # Match events
    events: List[LiveEvent] = field(default_factory=list)
    
    # Metadata
    is_top_team_match: bool = False
    venue: Optional[str] = None
    match_start: Optional[datetime] = None
    
    def get_league_key(self) -> str:
        """Get a key for the league (for images, etc.)."""
        league_lower = self.league_name.lower()
        if "champions" in league_lower or "ucl" in league_lower:
            return "ucl"
        elif "laliga" in league_lower or "la liga" in league_lower or "primera" in league_lower:
            return "laliga"
        elif "premier" in league_lower:
            return "premier"
        elif "bundesliga" in league_lower:
            return "bundesliga"
        elif "serie a" in league_lower:
            return "seriea"
        else:
            return "default"


class LiveCollector:
    """
    Collects live match data from football APIs.
    
    Supports:
    - free-api-live-football-data.p.rapidapi.com (Free tier)
    - api-football-v1.p.rapidapi.com (Paid tier)
    """
    
    def __init__(self):
        """Initialize the live collector."""
        self.config = get_config()
        self.live_config = self.config.live
        
        self.api_key = self.live_config.api_key
        self.api_host = self.live_config.api_host
        
        self.tracked_leagues = self.live_config.tracked_leagues
        self.top_teams = self.config.top_teams
        
        # Cache for previous state (to detect new events)
        self._previous_states: Dict[str, Dict] = {}
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a request to the API.
        
        Args:
            url: Full API URL
            params: Query parameters
            
        Returns:
            JSON response or None on error
        """
        if not self.api_key:
            logger.warning("No API key configured for live matches")
            return None
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=self.config.request_timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if isinstance(data, dict):
                if data.get('message') and 'not subscribed' in data.get('message', '').lower():
                    logger.error(f"API subscription required: {data.get('message')}")
                    return None
                if data.get('errors') and len(data.get('errors', [])) > 0:
                    logger.error(f"API error: {data['errors']}")
                    return None
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid JSON response: {e}")
            return None
    
    def _is_top_team_match(self, home_team: str, away_team: str) -> bool:
        """Check if the match involves a top team."""
        home_lower = home_team.lower()
        away_lower = away_team.lower()
        
        for team in self.top_teams:
            team_lower = team.lower()
            if team_lower in home_lower or team_lower in away_lower:
                return True
        
        return False
    
    def _normalize_team_name(self, name: str) -> str:
        """Normalize team name for display."""
        if not name:
            return "Unknown"
        
        # Common replacements
        replacements = {
            "FC Barcelona": "Barcelona",
            "Real Madrid CF": "Real Madrid",
            "Atletico Madrid": "Atlético Madrid",
            "Club Atletico de Madrid": "Atlético Madrid",
            "Manchester United": "Man United",
            "Manchester City": "Man City",
            "Paris Saint Germain": "PSG",
            "Paris Saint-Germain": "PSG",
            "Bayern München": "Bayern Munich",
            "Bayern Munich": "Bayern Munich",
            "Borussia Dortmund": "Dortmund",
            "Inter Milan": "Inter",
            "Internazionale": "Inter",
            "AC Milan": "Milan",
        }
        
        return replacements.get(name, name)
    
    def _is_tracked_league(self, league_name: str, league_id: Optional[int] = None) -> bool:
        """Check if a league should be tracked."""
        # Check by ID first
        if league_id and league_id in self.tracked_leagues:
            return True
        
        # Check by name
        league_lower = league_name.lower() if league_name else ""
        tracked_keywords = [
            "champions", "ucl", "uefa champions",
            "laliga", "la liga", "primera division", "primera división",
            "premier league",
            "serie a",
            "bundesliga"
        ]
        
        for keyword in tracked_keywords:
            if keyword in league_lower:
                return True
        
        return False
    
    def fetch_live_matches_free_api(self) -> List[LiveMatch]:
        """
        Fetch live matches using free-api-live-football-data.
        Uses football-get-matches-by-date endpoint and filters for live matches.
        
        Returns:
            List of LiveMatch objects
        """
        live_matches = []
        
        # Get today's date in YYYYMMDD format
        today = datetime.now().strftime("%Y%m%d")
        
        # Fetch matches for today
        url = f"https://{self.api_host}/football-get-matches-by-date"
        data = self._make_request(url, {"date": today})
        
        if not data or data.get('status') != 'success':
            logger.warning(f"Failed to fetch matches: {data}")
            return []
        
        # Get matches from response
        matches = data.get('response', {}).get('matches', [])
        logger.info(f"Fetched {len(matches)} matches for today")
        
        for match_data in matches:
            try:
                # Check if match is currently live (started but not finished)
                status_info = match_data.get('status', {})
                is_started = status_info.get('started', False)
                is_finished = status_info.get('finished', False)
                is_cancelled = status_info.get('cancelled', False)
                
                # Skip if not live
                if not is_started or is_finished or is_cancelled:
                    continue
                
                # Extract match info from free API format
                league_id = match_data.get('leagueId', 0)
                
                # Get team names
                home_data = match_data.get('home', {})
                away_data = match_data.get('away', {})
                home_team = home_data.get('name', '') or home_data.get('longName', '')
                away_team = away_data.get('name', '') or away_data.get('longName', '')
                
                # Check if it's a top team match
                is_top = self._is_top_team_match(home_team, away_team)
                
                if not is_top:
                    continue
                
                # Determine league name from our tracked leagues or use generic
                league_name = self.tracked_leagues.get(league_id, "Football")
                
                # Also check by league name patterns
                if not self._is_tracked_league(league_name, league_id):
                    # If it's a top team, still include if it looks like a major competition
                    # (Champions League has leagueId around 894202, 904988 etc)
                    pass  # We already filtered by top teams, so include it
                
                # Get scores
                home_score = home_data.get('score', 0) or 0
                away_score = away_data.get('score', 0) or 0
                
                # Get red cards info
                home_red_cards = home_data.get('redCards', 0) or 0
                away_red_cards = away_data.get('redCards', 0) or 0
                
                # Get match status
                status_reason = status_info.get('reason', {})
                status = status_reason.get('short', 'LIVE')
                
                match_id = str(match_data.get('id', ''))
                
                match = LiveMatch(
                    match_id=match_id,
                    league_id=league_id,
                    league_name=league_name,
                    home_team=self._normalize_team_name(home_team),
                    away_team=self._normalize_team_name(away_team),
                    home_score=int(home_score) if home_score else 0,
                    away_score=int(away_score) if away_score else 0,
                    status=status,
                    minute=None,  # Free API doesn't provide minute in this format
                    is_top_team_match=is_top,
                )
                
                logger.info(f"🔴 LIVE: {match.home_team} {match.home_score}-{match.away_score} {match.away_team}")
                live_matches.append(match)
                
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Error parsing match: {e}")
                continue
        
        logger.info(f"Found {len(live_matches)} live top-team matches")
        return live_matches
    
    def fetch_live_matches_api_football(self) -> List[LiveMatch]:
        """
        Fetch live matches using api-football-v1 (paid API).
        
        Returns:
            List of LiveMatch objects
        """
        live_matches = []
        
        url = f"https://{self.api_host}/v3/fixtures"
        data = self._make_request(url, {"live": "all"})
        
        if not data or 'response' not in data:
            return []
        
        for fixture in data['response']:
            try:
                league_id = fixture['league']['id']
                
                # Only track configured leagues
                if league_id not in self.tracked_leagues:
                    continue
                
                home_team = fixture['teams']['home']['name']
                away_team = fixture['teams']['away']['name']
                
                # Check if it's a top team match
                is_top = self._is_top_team_match(home_team, away_team)
                
                if not is_top:
                    continue
                
                match = LiveMatch(
                    match_id=str(fixture['fixture']['id']),
                    league_id=league_id,
                    league_name=self.tracked_leagues.get(league_id, fixture['league']['name']),
                    home_team=self._normalize_team_name(home_team),
                    away_team=self._normalize_team_name(away_team),
                    home_score=fixture['goals']['home'] or 0,
                    away_score=fixture['goals']['away'] or 0,
                    status=fixture['fixture']['status']['short'],
                    minute=fixture['fixture']['status']['elapsed'],
                    is_top_team_match=is_top,
                    venue=fixture['fixture'].get('venue', {}).get('name')
                )
                
                live_matches.append(match)
                
            except (KeyError, TypeError) as e:
                logger.warning(f"Error parsing fixture: {e}")
                continue
        
        logger.info(f"Found {len(live_matches)} live top-team matches")
        return live_matches
    
    def fetch_live_matches(self) -> List[LiveMatch]:
        """
        Fetch all live matches from tracked leagues.
        Auto-detects which API to use based on the configured host.
        
        Returns:
            List of LiveMatch objects
        """
        # Detect API type from host
        if "free-api-live-football-data" in self.api_host:
            return self.fetch_live_matches_free_api()
        else:
            return self.fetch_live_matches_api_football()
    
    def fetch_match_events(self, match_id: str) -> List[LiveEvent]:
        """
        Fetch events for a specific match.
        
        Args:
            match_id: The fixture ID
            
        Returns:
            List of LiveEvent objects
        """
        events = []
        
        # For free API, events might be included in match data
        # For paid API, there's a separate endpoint
        if "api-football-v1" in self.api_host:
            url = f"https://{self.api_host}/v3/fixtures/events"
            data = self._make_request(url, {"fixture": match_id})
            
            if not data or 'response' not in data:
                return []
            
            for event in data['response']:
                try:
                    event_type = event['type'].lower()
                    detail = event.get('detail', '').lower()
                    
                    # Map API event types to our EventType
                    if event_type == 'goal':
                        ev_type = EventType.GOAL
                        ev_detail = None
                        
                        if 'penalty' in detail:
                            ev_detail = "Penalty"
                        elif 'own goal' in detail:
                            ev_detail = "Own Goal"
                            
                    elif event_type == 'card' and 'red' in detail:
                        ev_type = EventType.RED_CARD
                        ev_detail = "Direct" if 'straight' in detail else "Second Yellow"
                        
                    elif event_type == 'var':
                        ev_type = EventType.VAR
                        ev_detail = detail
                        
                    else:
                        continue
                    
                    live_event = LiveEvent(
                        match_id=match_id,
                        event_type=ev_type,
                        minute=event.get('time', {}).get('elapsed'),
                        player=event.get('player', {}).get('name'),
                        assist=event.get('assist', {}).get('name'),
                        detail=ev_detail,
                        team=event.get('team', {}).get('name')
                    )
                    
                    events.append(live_event)
                    
                except (KeyError, TypeError) as e:
                    logger.warning(f"Error parsing event: {e}")
                    continue
        
        return events
    
    def detect_new_events(self, match: LiveMatch, previous_events: List[Dict]) -> List[LiveEvent]:
        """
        Detect new events by comparing with previous state.
        
        Args:
            match: Current match state
            previous_events: List of previously recorded events
            
        Returns:
            List of new events
        """
        new_events = []
        
        # Get current events
        current_events = self.fetch_match_events(match.match_id)
        
        # Build set of previous event identifiers
        previous_ids = set()
        for ev in previous_events:
            ev_id = f"{ev['event_type']}_{ev.get('event_minute')}_{ev.get('event_player', '')}"
            previous_ids.add(ev_id)
        
        # Find new events
        for event in current_events:
            ev_id = f"{event.event_type.value}_{event.minute}_{event.player or ''}"
            
            if ev_id not in previous_ids:
                # Update scores on the event
                event.home_score = match.home_score
                event.away_score = match.away_score
                new_events.append(event)
        
        return new_events
    
    def check_match_finished(self, match: LiveMatch, previous_status: Optional[str]) -> bool:
        """
        Check if a match has just finished.
        
        Args:
            match: Current match state
            previous_status: Previous match status
            
        Returns:
            True if match just finished
        """
        finished_statuses = {'FT', 'AET', 'PEN', 'FINISHED'}
        
        if match.status in finished_statuses:
            if previous_status and previous_status not in finished_statuses:
                return True
        
        return False
    
    def get_live_data(self, repo) -> List[tuple]:
        """
        Get all live data and detect publishable events.
        
        Args:
            repo: Repository instance for checking previous state
            
        Returns:
            List of (LiveMatch, LiveEvent) tuples for new publishable events
        """
        publishable = []
        
        # Fetch current live matches
        live_matches = self.fetch_live_matches()
        
        for match in live_matches:
            # Get previous match state from DB
            db_match = repo.get_live_match(match.match_id)
            previous_events = repo.get_match_events(match.match_id) if db_match else []
            previous_status = db_match['match_status'] if db_match else None
            previous_home_score = db_match['home_score'] if db_match else 0
            previous_away_score = db_match['away_score'] if db_match else 0
            
            # Update match in DB
            repo.upsert_live_match(
                match_id=match.match_id,
                league_id=match.league_id,
                league_name=match.league_name,
                home_team=match.home_team,
                away_team=match.away_team,
                home_score=match.home_score,
                away_score=match.away_score,
                match_status=match.status,
                current_minute=match.minute or 0,
                is_top_team_match=match.is_top_team_match
            )
            
            # Check for match finished event
            if self.check_match_finished(match, previous_status):
                final_event = LiveEvent(
                    match_id=match.match_id,
                    event_type=EventType.FINAL,
                    minute=90,
                    home_score=match.home_score,
                    away_score=match.away_score
                )
                publishable.append((match, final_event))
            
            # Check for goals by comparing scores
            if db_match:
                goals_diff_home = match.home_score - previous_home_score
                goals_diff_away = match.away_score - previous_away_score
                
                # Detect new home goals
                for _ in range(goals_diff_home):
                    goal_event = LiveEvent(
                        match_id=match.match_id,
                        event_type=EventType.GOAL,
                        minute=match.minute,
                        team=match.home_team,
                        home_score=match.home_score,
                        away_score=match.away_score
                    )
                    publishable.append((match, goal_event))
                
                # Detect new away goals
                for _ in range(goals_diff_away):
                    goal_event = LiveEvent(
                        match_id=match.match_id,
                        event_type=EventType.GOAL,
                        minute=match.minute,
                        team=match.away_team,
                        home_score=match.home_score,
                        away_score=match.away_score
                    )
                    publishable.append((match, goal_event))
            
            # Detect new events from API (for detailed info like player names)
            new_events = self.detect_new_events(match, previous_events)
            
            for event in new_events:
                # Avoid duplicating goal events already detected by score change
                if event.event_type != EventType.GOAL:
                    publishable.append((match, event))
        
        return publishable


def get_live_collector() -> LiveCollector:
    """Get a LiveCollector instance."""
    return LiveCollector()
