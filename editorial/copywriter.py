"""
Copywriter module for GoalFeed.
Generates engaging captions with a controlled "tabloid" style.
Uses HTML formatting for Telegram (bold, italic, etc.)
"""
import logging
import random
from typing import List, Optional
import html

from config import (
    get_config,
    HEADLINE_TEMPLATES,
    STATUS_CONFIG,
    SPORT_DISPLAY,
    CATEGORY_HASHTAGS
)
from processor.normalize import NormalizedItem
from utils.text import truncate_text, clean_html

logger = logging.getLogger(__name__)


def escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    return html.escape(text)


def make_telegram_html_safe(text: str, max_length: int = 1024) -> str:
    """Make text safe for Telegram HTML, respecting max length."""
    if len(text) > max_length:
        text = text[:max_length - 3] + "..."
    return text


class Copywriter:
    """
    Generates captions for Telegram posts.
    
    Style: Controlled "tabloid" feel without fabricating information.
    Uses HTML formatting for bold, italic, etc.
    """
    
    def __init__(self):
        self.config = get_config()
    
    def generate_headline(self, item: NormalizedItem) -> str:
        """
        Generate an engaging headline with emoji and bold formatting.
        
        Args:
            item: NormalizedItem to create headline for
            
        Returns:
            Headline string with emoji and HTML bold
        """
        # Get templates for category
        category = item.category or 'default'
        templates = HEADLINE_TEMPLATES.get(category, HEADLINE_TEMPLATES['default'])
        
        # Choose random template
        template = random.choice(templates)
        
        # Clean and truncate original title
        headline = clean_html(item.title)
        headline = truncate_text(headline, 100, "...")
        headline = escape_html(headline)
        
        # Apply template and make bold
        formatted = template.format(headline=headline)
        
        return f"<b>{formatted}</b>"
    
    def generate_summary(self, item: NormalizedItem, max_lines: int = 3) -> str:
        """
        Generate a brief summary (2-3 lines) in italic.
        
        Args:
            item: NormalizedItem to summarize
            max_lines: Maximum lines
            
        Returns:
            Summary text with italic formatting
        """
        # Use summary if available, otherwise use title
        if item.summary:
            summary = clean_html(item.summary)
        else:
            summary = clean_html(item.title)
        
        # Truncate to reasonable length
        max_length = 200 * max_lines
        summary = truncate_text(summary, max_length, "...")
        summary = escape_html(summary)
        
        return f"<i>{summary}</i>"
    
    def generate_status_line(self, item: NormalizedItem) -> str:
        """
        Generate the status line (CONFIRMADO/RUMOR/EN DESARROLLO) with formatting.
        
        Args:
            item: NormalizedItem
            
        Returns:
            Status line string with bold label
        """
        status = item.status
        status_info = STATUS_CONFIG.get(status, STATUS_CONFIG['RUMOR'])
        
        return f"<b>Estado:</b> {status_info['emoji']} {status_info['label']}"
    
    def generate_hashtags(self, item: NormalizedItem) -> str:
        """
        Generate relevant hashtags.
        
        Args:
            item: NormalizedItem
            
        Returns:
            Hashtag string
        """
        hashtags = []
        
        # Sport hashtag
        sport_info = SPORT_DISPLAY.get(item.sport, SPORT_DISPLAY['football_eu'])
        hashtags.append(sport_info['hashtag'])
        
        # Category hashtag
        if item.category and item.category in CATEGORY_HASHTAGS:
            hashtags.append(CATEGORY_HASHTAGS[item.category])
        
        # Status hashtag
        if item.status == "RUMOR":
            hashtags.append("#Rumor")
        elif item.status == "CONFIRMADO":
            hashtags.append("#Confirmado")
        elif item.status == "EN_DESARROLLO":
            hashtags.append("#EnDesarrollo")
        
        # Add GoalFeed tag
        hashtags.append("#GoalFeed")
        
        return " ".join(hashtags)
    
    def generate_source_line(self, item: NormalizedItem) -> str:
        """
        Generate the source attribution line with formatting.
        
        Args:
            item: NormalizedItem
            
        Returns:
            Source line string
        """
        source = item.source_name or item.source_domain or "Fuente"
        source = escape_html(source)
        return f"📰 <b>Vía:</b> {source}"
    
    def generate_caption(self, item: NormalizedItem) -> str:
        """
        Generate full caption for a single article post with HTML formatting.
        
        Format:
        - Headline with emoji (BOLD)
        - Summary (2-3 lines) (ITALIC)
        - Status line (BOLD label)
        - Hashtags
        - Source (BOLD label)
        
        Args:
            item: NormalizedItem
            
        Returns:
            Full caption string with HTML (max 1024 chars for Telegram)
        """
        parts = []
        
        # Headline (bold)
        headline = self.generate_headline(item)
        parts.append(headline)
        
        # Empty line
        parts.append("")
        
        # Summary (italic)
        summary = self.generate_summary(item)
        if summary and clean_html(item.summary or "") != item.title:
            parts.append(summary)
            parts.append("")
        
        # Status (bold label)
        status = self.generate_status_line(item)
        parts.append(status)
        
        # Empty line
        parts.append("")
        
        # Hashtags
        hashtags = self.generate_hashtags(item)
        parts.append(hashtags)
        
        # Source (bold label)
        source = self.generate_source_line(item)
        parts.append(source)
        
        # Join and ensure safe length
        caption = "\n".join(parts)
        caption = make_telegram_html_safe(caption, max_length=1024)
        
        return caption
    
    def generate_digest_caption(
        self,
        items: List[NormalizedItem],
        sport: str
    ) -> str:
        """
        Generate caption for a digest post with HTML formatting.
        
        Format:
        📌 <b>GoalFeed | Resumen {sport}</b> (últimos 20 min)
        
        1. <b>Headline 1</b>
        2. <b>Headline 2</b>
        ...
        
        Hashtags
        
        Args:
            items: List of NormalizedItem for digest
            sport: Sport type
            
        Returns:
            Digest caption string with HTML
        """
        parts = []
        
        # Header (bold)
        sport_info = SPORT_DISPLAY.get(sport, SPORT_DISPLAY['football_eu'])
        header = f"📌 <b>GoalFeed | Resumen {sport_info['name']}</b> <i>(últimos {self.config.digest_window_minutes} min)</i>"
        parts.append(header)
        parts.append("")
        
        # Numbered list of headlines (bold)
        for i, item in enumerate(items, 1):
            # Get sport emoji
            emoji = sport_info['emoji']
            
            # Clean and escape title
            title = clean_html(item.title)
            title = truncate_text(title, 80, "...")
            title = escape_html(title)
            
            # Add status indicator
            status_emoji = STATUS_CONFIG.get(item.status, {}).get('emoji', '')
            
            line = f"{i}. {emoji} <b>{title}</b> {status_emoji}"
            parts.append(line)
        
        parts.append("")
        
        # Hashtags
        hashtags = [sport_info['hashtag'], "#Resumen", "#GoalFeed"]
        parts.append(" ".join(hashtags))
        
        # Join and ensure safe length
        caption = "\n".join(parts)
        caption = make_telegram_html_safe(caption, max_length=1024)
        
        return caption
    
    def get_conditional_language(self, status: str) -> dict:
        """
        Get conditional language based on status.
        
        Args:
            status: Article status
            
        Returns:
            Dict with language suggestions
        """
        if status == "RUMOR":
            return {
                "verbs": ["podría", "estaría", "según fuentes", "se rumorea"],
                "prefixes": ["Posible:", "Se dice que", "Rumores apuntan a"],
                "suffixes": ["según fuentes cercanas", "aún sin confirmar"]
            }
        elif status == "EN_DESARROLLO":
            return {
                "verbs": ["está sucediendo", "se está desarrollando", "en curso"],
                "prefixes": ["Última hora:", "En desarrollo:"],
                "suffixes": ["más información próximamente", "actualizaremos"]
            }
        else:  # CONFIRMADO
            return {
                "verbs": ["confirma", "anuncia", "hace oficial"],
                "prefixes": ["Oficial:", "Confirmado:"],
                "suffixes": ["comunicado oficial", "ya es oficial"]
            }


def get_copywriter() -> Copywriter:
    """Get a Copywriter instance."""
    return Copywriter()


def generate_caption(item: NormalizedItem) -> str:
    """Convenience function to generate a caption."""
    return get_copywriter().generate_caption(item)


def generate_digest_caption(items: List[NormalizedItem], sport: str) -> str:
    """Convenience function to generate a digest caption."""
    return get_copywriter().generate_digest_caption(items, sport)
