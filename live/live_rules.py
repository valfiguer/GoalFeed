"""
Live Rules for GoalFeed.
Anti-spam and filtering rules for live match events.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from config import get_config
from .live_collector import LiveMatch, LiveEvent, EventType

logger = logging.getLogger(__name__)


class LiveRules:
    """
    Rules engine for live match event publishing.
    
    Implements anti-spam protections:
    - Max events per match
    - Cooldown between events of same match
    - No duplicate events
    """
    
    def __init__(self):
        """Initialize live rules engine."""
        self.config = get_config()
        self.live_config = self.config.live
        
        self.max_events_per_match = self.live_config.max_events_per_match
        self.event_cooldown_minutes = self.live_config.event_cooldown_minutes
    
    def can_publish_event(
        self,
        match: LiveMatch,
        event: LiveEvent,
        repo
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if an event can be published.
        
        Args:
            match: The match
            event: The event to publish
            repo: Repository for checking constraints
            
        Returns:
            Tuple of (can_publish, reason_if_blocked)
        """
        # 1. Check if event was already published
        if repo.is_event_published(
            match_id=match.match_id,
            event_type=event.event_type.value,
            event_minute=event.minute,
            event_player=event.player
        ):
            return False, "Event already published"
        
        # 2. Check max events per match (except for FINAL)
        if event.event_type != EventType.FINAL:
            event_count = repo.get_match_event_count(match.match_id)
            
            if event_count >= self.max_events_per_match:
                return False, f"Max events ({self.max_events_per_match}) reached for match"
        
        # 3. Check cooldown (except for FINAL which is always allowed)
        if event.event_type != EventType.FINAL:
            last_event_time = repo.get_last_event_time(match.match_id)
            
            if last_event_time:
                from utils.timeutils import utc_now
                cooldown_end = last_event_time + timedelta(minutes=self.event_cooldown_minutes)
                
                if utc_now() < cooldown_end:
                    remaining = (cooldown_end - utc_now()).total_seconds() / 60
                    return False, f"Cooldown active ({remaining:.1f} min remaining)"
        
        # 4. Check if it's a top team match (should already be filtered, but double-check)
        if not match.is_top_team_match:
            return False, "Not a top team match"
        
        return True, None
    
    def filter_publishable_events(
        self,
        events: List[Tuple[LiveMatch, LiveEvent]],
        repo
    ) -> List[Tuple[LiveMatch, LiveEvent]]:
        """
        Filter a list of events to only those that can be published.
        
        Args:
            events: List of (match, event) tuples
            repo: Repository instance
            
        Returns:
            Filtered list of publishable events
        """
        publishable = []
        
        for match, event in events:
            can_publish, reason = self.can_publish_event(match, event, repo)
            
            if can_publish:
                publishable.append((match, event))
                logger.info(
                    f"✓ Event eligible: {event.event_type.value} - "
                    f"{match.home_team} vs {match.away_team}"
                )
            else:
                logger.debug(
                    f"✗ Event blocked: {event.event_type.value} - "
                    f"{match.home_team} vs {match.away_team} - {reason}"
                )
        
        return publishable
    
    def prioritize_events(
        self,
        events: List[Tuple[LiveMatch, LiveEvent]]
    ) -> List[Tuple[LiveMatch, LiveEvent]]:
        """
        Prioritize events for publishing order.
        
        Priority order:
        1. Finals (match end)
        2. Goals
        3. Red cards
        4. VAR decisions
        5. Other
        
        Args:
            events: List of events
            
        Returns:
            Sorted list by priority
        """
        priority_map = {
            EventType.FINAL: 0,
            EventType.GOAL: 1,
            EventType.RED_CARD: 2,
            EventType.PENALTY_MISS: 3,
            EventType.VAR: 4,
            EventType.HALFTIME: 5,
        }
        
        def get_priority(item: Tuple[LiveMatch, LiveEvent]) -> int:
            _, event = item
            return priority_map.get(event.event_type, 10)
        
        return sorted(events, key=get_priority)
    
    def get_event_importance(self, event: LiveEvent) -> str:
        """
        Get importance level of an event.
        
        Args:
            event: The event
            
        Returns:
            Importance level (high, medium, low)
        """
        if event.event_type == EventType.FINAL:
            return "high"
        elif event.event_type == EventType.GOAL:
            return "high"
        elif event.event_type == EventType.RED_CARD:
            return "medium"
        elif event.event_type == EventType.PENALTY_MISS:
            return "medium"
        elif event.event_type == EventType.VAR:
            return "low"
        else:
            return "low"


def get_live_rules() -> LiveRules:
    """Get a LiveRules instance."""
    return LiveRules()
