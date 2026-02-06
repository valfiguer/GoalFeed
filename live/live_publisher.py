"""
Live Publisher for GoalFeed.
Handles formatting and publishing of live match events.
"""
import logging
import os
from typing import Optional, Dict
from io import BytesIO
from pathlib import Path

from config import get_config
from .live_collector import LiveMatch, LiveEvent, EventType

logger = logging.getLogger(__name__)

# Project root for asset paths
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


class LivePublisher:
    """
    Formats and publishes live match events to Telegram.
    """
    
    def __init__(self):
        """Initialize the live publisher."""
        self.config = get_config()
        self.live_config = self.config.live
    
    def format_goal_message(self, match: LiveMatch, event: LiveEvent) -> str:
        """
        Format a goal message.
        
        Format:
        ⚽ GOL | Champions League
        Real Madrid 1–0 Bayern
        Min 34 | Jude Bellingham
        """
        lines = []
        
        # Header with emoji and league
        lines.append(f"⚽ <b>GOL</b> | {match.league_name}")
        
        # Score line
        lines.append(f"<b>{match.home_team}</b> {event.home_score}–{event.away_score} <b>{match.away_team}</b>")
        
        # Details line
        details = []
        if event.minute:
            details.append(f"Min {event.minute}'")
        if event.player:
            details.append(event.player)
        
        if details:
            lines.append(" | ".join(details))
        
        # Additional info (penalty, own goal, assist)
        extras = []
        if event.detail:
            if event.detail.lower() == "penalty":
                extras.append("⚡ Penalty")
            elif "own goal" in event.detail.lower():
                extras.append("🔴 Autogol")
        
        if event.assist:
            extras.append(f"🅰️ Asistencia: {event.assist}")
        
        if extras:
            lines.append("\n".join(extras))
        
        # Hashtags
        hashtags = self._get_league_hashtags(match)
        if hashtags:
            lines.append(f"\n{hashtags}")
        
        return "\n".join(lines)
    
    def format_red_card_message(self, match: LiveMatch, event: LiveEvent) -> str:
        """
        Format a red card message.
        
        Format:
        🟥 EXPULSIÓN | LaLiga
        Barcelona 1–1 Sevilla
        Min 67 | Jugador
        """
        lines = []
        
        # Header
        lines.append(f"🟥 <b>EXPULSIÓN</b> | {match.league_name}")
        
        # Score line
        lines.append(f"<b>{match.home_team}</b> {event.home_score}–{event.away_score} <b>{match.away_team}</b>")
        
        # Details
        details = []
        if event.minute:
            details.append(f"Min {event.minute}'")
        if event.player:
            details.append(event.player)
        
        if details:
            lines.append(" | ".join(details))
        
        # Type of red card
        if event.detail:
            if "second" in event.detail.lower() or "yellow" in event.detail.lower():
                lines.append("📒📒 Doble amarilla")
            else:
                lines.append("🔴 Roja directa")
        
        # Hashtags
        hashtags = self._get_league_hashtags(match)
        if hashtags:
            lines.append(f"\n{hashtags}")
        
        return "\n".join(lines)
    
    def format_final_message(self, match: LiveMatch, event: LiveEvent) -> str:
        """
        Format a match final message.
        
        Format:
        🏁 FINAL | Champions League
        Real Madrid 2–1 Bayern
        """
        lines = []
        
        # Header
        lines.append(f"🏁 <b>FINAL</b> | {match.league_name}")
        
        # Final score
        lines.append(f"<b>{match.home_team}</b> {event.home_score}–{event.away_score} <b>{match.away_team}</b>")
        
        # Winner indication
        if event.home_score > event.away_score:
            lines.append(f"🏆 Victoria local")
        elif event.away_score > event.home_score:
            lines.append(f"🏆 Victoria visitante")
        else:
            lines.append(f"🤝 Empate")
        
        # Hashtags
        hashtags = self._get_league_hashtags(match)
        if hashtags:
            lines.append(f"\n{hashtags}")
        
        return "\n".join(lines)
    
    def format_penalty_miss_message(self, match: LiveMatch, event: LiveEvent) -> str:
        """
        Format a penalty miss message.
        """
        lines = []
        
        # Header
        lines.append(f"❌ <b>PENALTI FALLADO</b> | {match.league_name}")
        
        # Score line
        lines.append(f"<b>{match.home_team}</b> {event.home_score}–{event.away_score} <b>{match.away_team}</b>")
        
        # Details
        details = []
        if event.minute:
            details.append(f"Min {event.minute}'")
        if event.player:
            details.append(event.player)
        
        if details:
            lines.append(" | ".join(details))
        
        # Hashtags
        hashtags = self._get_league_hashtags(match)
        if hashtags:
            lines.append(f"\n{hashtags}")
        
        return "\n".join(lines)
    
    def format_var_message(self, match: LiveMatch, event: LiveEvent) -> str:
        """
        Format a VAR decision message.
        """
        lines = []
        
        # Header
        lines.append(f"📺 <b>VAR</b> | {match.league_name}")
        
        # Score line
        lines.append(f"<b>{match.home_team}</b> {event.home_score}–{event.away_score} <b>{match.away_team}</b>")
        
        # Details
        if event.minute:
            lines.append(f"Min {event.minute}'")
        
        if event.detail:
            lines.append(f"⚖️ Decisión: {event.detail}")
        
        # Hashtags
        hashtags = self._get_league_hashtags(match)
        if hashtags:
            lines.append(f"\n{hashtags}")
        
        return "\n".join(lines)
    
    def format_event_message(self, match: LiveMatch, event: LiveEvent) -> str:
        """
        Format any event message based on type.
        
        Args:
            match: The match
            event: The event
            
        Returns:
            Formatted message string
        """
        if event.event_type == EventType.GOAL:
            return self.format_goal_message(match, event)
        elif event.event_type == EventType.RED_CARD:
            return self.format_red_card_message(match, event)
        elif event.event_type == EventType.FINAL:
            return self.format_final_message(match, event)
        elif event.event_type == EventType.PENALTY_MISS:
            return self.format_penalty_miss_message(match, event)
        elif event.event_type == EventType.VAR:
            return self.format_var_message(match, event)
        else:
            # Generic format
            return f"📢 {match.league_name}\n{match.home_team} {event.home_score}–{event.away_score} {match.away_team}"
    
    def _get_league_hashtags(self, match: LiveMatch) -> str:
        """Get hashtags for a league."""
        league_key = match.league_key if hasattr(match, 'league_key') else match.get_league_key()
        
        hashtag_map = {
            "ucl": "#UCL #ChampionsLeague",
            "laliga": "#LaLiga #FútbolEspañol",
            "premier": "#PremierLeague",
            "bundesliga": "#Bundesliga",
            "seriea": "#SerieA",
        }
        
        base_tags = hashtag_map.get(league_key, "#Fútbol")
        return f"{base_tags} #GoalFeed"
    
    def get_live_image(self, match: LiveMatch) -> Optional[bytes]:
        """
        Get the appropriate live image for a match.
        
        Args:
            match: The match
            
        Returns:
            Image bytes or None
        """
        league_key = match.get_league_key()
        
        # Try to get specific image
        image_path = self.live_config.live_images.get(
            league_key,
            self.live_config.live_images.get("default")
        )
        
        if image_path:
            # Build absolute path
            if not os.path.isabs(image_path):
                image_path = os.path.join(PROJECT_ROOT, image_path)
            
            if os.path.exists(image_path):
                try:
                    with open(image_path, 'rb') as f:
                        return f.read()
                except IOError as e:
                    logger.warning(f"Could not read live image: {e}")
        
        # Fallback to creating a placeholder
        return self._create_live_placeholder(match)
    
    def _create_live_placeholder(self, match: LiveMatch) -> bytes:
        """Create a placeholder image for live events."""
        from media import create_placeholder_image
        
        text = f"🔴 LIVE\n{match.league_name}"
        return create_placeholder_image(text=text, color="#e74c3c")


def publish_live_event(
    match: LiveMatch,
    event: LiveEvent,
    repo,
    publisher=None
) -> Optional[int]:
    """
    Publish a live event to Telegram.
    
    Args:
        match: The match
        event: The event to publish
        repo: Repository for recording
        publisher: Optional TelegramPublisher instance
        
    Returns:
        Telegram message ID or None on failure
    """
    from publisher import get_publisher
    from media import process_image_with_watermark
    
    config = get_config()
    live_pub = LivePublisher()
    
    # Format message
    caption = live_pub.format_event_message(match, event)
    
    # Get image
    image_data = live_pub.get_live_image(match)
    
    if image_data:
        # Apply watermark
        processed_image = process_image_with_watermark(image_data)
    else:
        processed_image = None
    
    # Get or create publisher
    if publisher is None:
        publisher = get_publisher()
    
    # Publish
    try:
        if processed_image:
            message_id = publisher.send_photo(
                image_data=processed_image,
                caption=caption
            )
        else:
            # Fallback to text-only (shouldn't happen normally)
            message_id = publisher.send_message(caption=caption)
        
        if message_id:
            # Record the event
            repo.record_live_event(
                match_id=match.match_id,
                league_id=match.league_id,
                league_name=match.league_name,
                home_team=match.home_team,
                away_team=match.away_team,
                home_score=event.home_score,
                away_score=event.away_score,
                event_type=event.event_type.value,
                event_minute=event.minute,
                event_player=event.player,
                event_detail=event.detail,
                telegram_message_id=message_id,
                telegram_chat_id=config.channel_chat_id
            )
            
            # Increment match event counter
            repo.increment_match_events(match.match_id)
            
            logger.info(
                f"✅ Published live event: {event.event_type.value} - "
                f"{match.home_team} vs {match.away_team}"
            )
            
            return message_id
        else:
            logger.error(f"Failed to publish live event")
            return None
            
    except Exception as e:
        logger.error(f"Error publishing live event: {e}")
        return None


def get_live_publisher() -> LivePublisher:
    """Get a LivePublisher instance."""
    return LivePublisher()
