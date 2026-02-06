"""
RSS Collector for GoalFeed.
Fetches and parses RSS feeds from configured sources.
"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

import feedparser
import requests

from config import get_config, RSSSource
from utils.timeutils import parse_rss_date, utc_now

logger = logging.getLogger(__name__)


@dataclass
class RawItem:
    """Raw item from RSS feed before processing."""
    title: str
    link: str
    summary: Optional[str] = None
    published: Optional[datetime] = None
    image_url: Optional[str] = None
    
    # Source metadata
    source_name: str = ""
    source_url: str = ""
    source_sport_hint: str = "football_eu"
    source_weight: int = 10
    
    # Additional metadata
    author: Optional[str] = None
    categories: List[str] = field(default_factory=list)


def _extract_image_from_entry(entry: Dict) -> Optional[str]:
    """
    Extract image URL from a feed entry.
    Tries multiple common RSS/Atom image fields.
    
    Args:
        entry: feedparser entry dict
        
    Returns:
        Image URL or None
    """
    # Try media:content
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if media.get('medium') == 'image' or media.get('type', '').startswith('image/'):
                return media.get('url')
            # Some feeds just have url without type
            url = media.get('url', '')
            if url and any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                return url
    
    # Try media:thumbnail
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        for thumb in entry.media_thumbnail:
            if thumb.get('url'):
                return thumb.get('url')
    
    # Try enclosures
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image/'):
                return enc.get('href') or enc.get('url')
    
    # Try links with image type
    if hasattr(entry, 'links'):
        for link in entry.links:
            if link.get('type', '').startswith('image/'):
                return link.get('href')
    
    # Try image field directly
    if hasattr(entry, 'image') and entry.image:
        if isinstance(entry.image, dict):
            return entry.image.get('href') or entry.image.get('url')
        elif isinstance(entry.image, str):
            return entry.image
    
    return None


def _extract_summary(entry: Dict, max_length: int = 500) -> Optional[str]:
    """
    Extract summary from feed entry.
    
    Args:
        entry: feedparser entry
        max_length: Maximum summary length
        
    Returns:
        Summary text or None
    """
    # Try summary first
    summary = getattr(entry, 'summary', None)
    
    # Fall back to description
    if not summary:
        summary = getattr(entry, 'description', None)
    
    # Fall back to content
    if not summary and hasattr(entry, 'content'):
        for content in entry.content:
            if content.get('value'):
                summary = content.get('value')
                break
    
    if summary and len(summary) > max_length:
        summary = summary[:max_length] + "..."
    
    return summary


def _extract_categories(entry: Dict) -> List[str]:
    """Extract categories/tags from feed entry."""
    categories = []
    
    if hasattr(entry, 'tags'):
        for tag in entry.tags:
            term = tag.get('term') or tag.get('label')
            if term:
                categories.append(term)
    
    if hasattr(entry, 'categories'):
        for cat in entry.categories:
            if isinstance(cat, str):
                categories.append(cat)
            elif isinstance(cat, dict):
                categories.append(cat.get('term', ''))
    
    return [c for c in categories if c]


def fetch_feed(source: RSSSource, timeout: int = 15) -> List[RawItem]:
    """
    Fetch and parse a single RSS feed.
    
    Args:
        source: RSS source configuration
        timeout: Request timeout in seconds
        
    Returns:
        List of RawItem objects
    """
    items = []
    
    try:
        logger.debug(f"Fetching feed: {source.name} ({source.url})")
        
        # Use requests to fetch with timeout, then parse
        headers = {
            'User-Agent': 'GoalFeed/1.0 (RSS Reader)',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        }
        
        response = requests.get(
            source.url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Parse the feed
        feed = feedparser.parse(response.content)
        
        if feed.bozo and feed.bozo_exception:
            logger.warning(
                f"Feed parse warning for {source.name}: {feed.bozo_exception}"
            )
        
        for entry in feed.entries:
            try:
                # Extract basic fields
                title = getattr(entry, 'title', None)
                link = getattr(entry, 'link', None)
                
                if not title or not link:
                    continue
                
                # Extract published date
                published_str = (
                    getattr(entry, 'published', None) or
                    getattr(entry, 'updated', None) or
                    getattr(entry, 'created', None)
                )
                published = parse_rss_date(published_str)
                
                # Create RawItem
                item = RawItem(
                    title=title.strip(),
                    link=link.strip(),
                    summary=_extract_summary(entry),
                    published=published,
                    image_url=_extract_image_from_entry(entry),
                    source_name=source.name,
                    source_url=source.url,
                    source_sport_hint=source.sport_hint,
                    source_weight=source.weight,
                    author=getattr(entry, 'author', None),
                    categories=_extract_categories(entry)
                )
                
                items.append(item)
                
            except Exception as e:
                logger.warning(f"Error parsing entry from {source.name}: {e}")
                continue
        
        logger.info(f"Fetched {len(items)} items from {source.name}")
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching {source.name}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching {source.name}: {e}")
    except Exception as e:
        logger.error(f"Error fetching feed {source.name}: {e}")
    
    return items


def collect_all(sources: Optional[List[RSSSource]] = None) -> List[RawItem]:
    """
    Collect items from all configured RSS sources.
    
    Args:
        sources: List of sources (uses config if not provided)
        
    Returns:
        List of all RawItem objects from all sources
    """
    config = get_config()
    
    if sources is None:
        sources = config.rss_sources
    
    all_items = []
    
    for source in sources:
        items = fetch_feed(source, timeout=config.request_timeout)
        all_items.extend(items)
    
    logger.info(f"Collected {len(all_items)} total items from {len(sources)} sources")
    
    return all_items


def collect_by_sport(sport: str) -> List[RawItem]:
    """
    Collect items from sources of a specific sport.
    
    Args:
        sport: Sport type (football_eu, nba, tennis)
        
    Returns:
        List of RawItem objects
    """
    config = get_config()
    
    sources = [s for s in config.rss_sources if s.sport_hint == sport]
    
    return collect_all(sources)
