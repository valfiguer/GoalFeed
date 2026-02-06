"""
Normalization module for GoalFeed.
Handles URL canonicalization and title normalization.
"""
import logging
from typing import Optional
from datetime import datetime

from collector.rss_collector import RawItem
from utils.text import (
    normalize_title as _normalize_title,
    canonicalize_url as _canonicalize_url,
    get_domain,
    generate_article_hash,
    clean_html
)
from utils.timeutils import get_date_bucket, utc_now

logger = logging.getLogger(__name__)


class NormalizedItem:
    """Normalized article item ready for processing."""
    
    def __init__(
        self,
        title: str,
        normalized_title: str,
        link: str,
        canonical_url: str,
        content_hash: str,
        summary: Optional[str] = None,
        published_at: Optional[datetime] = None,
        image_url: Optional[str] = None,
        source_name: str = "",
        source_domain: str = "",
        source_sport_hint: str = "football_eu",
        source_weight: int = 10,
        categories: list = None
    ):
        self.title = title
        self.normalized_title = normalized_title
        self.link = link
        self.canonical_url = canonical_url
        self.content_hash = content_hash
        self.summary = summary
        self.published_at = published_at
        self.image_url = image_url
        self.source_name = source_name
        self.source_domain = source_domain
        self.source_sport_hint = source_sport_hint
        self.source_weight = source_weight
        self.categories = categories or []
        
        # These will be filled by classifier
        self.sport: str = source_sport_hint
        self.category: Optional[str] = None
        self.status: str = "RUMOR"
        
        # This will be filled by ranker
        self.score: int = 0
    
    def __repr__(self):
        return f"NormalizedItem(title='{self.title[:50]}...', score={self.score})"


def normalize_item(raw_item: RawItem) -> NormalizedItem:
    """
    Normalize a raw RSS item.
    
    Args:
        raw_item: RawItem from RSS collector
        
    Returns:
        NormalizedItem ready for processing
    """
    # Clean and normalize title
    title = clean_html(raw_item.title).strip()
    normalized_title = _normalize_title(title)
    
    # Canonicalize URL
    canonical_url = _canonicalize_url(raw_item.link)
    
    # Get domain
    source_domain = get_domain(raw_item.link)
    
    # Generate content hash for deduplication
    date_bucket = get_date_bucket(raw_item.published or utc_now())
    content_hash = generate_article_hash(normalized_title, source_domain, date_bucket)
    
    # Clean summary
    summary = None
    if raw_item.summary:
        summary = clean_html(raw_item.summary).strip()
        if len(summary) > 500:
            summary = summary[:500] + "..."
    
    return NormalizedItem(
        title=title,
        normalized_title=normalized_title,
        link=raw_item.link,
        canonical_url=canonical_url,
        content_hash=content_hash,
        summary=summary,
        published_at=raw_item.published,
        image_url=raw_item.image_url,
        source_name=raw_item.source_name,
        source_domain=source_domain,
        source_sport_hint=raw_item.source_sport_hint,
        source_weight=raw_item.source_weight,
        categories=raw_item.categories
    )


def normalize_all(raw_items: list[RawItem]) -> list[NormalizedItem]:
    """
    Normalize a list of raw items.
    
    Args:
        raw_items: List of RawItem objects
        
    Returns:
        List of NormalizedItem objects
    """
    normalized = []
    
    for raw_item in raw_items:
        try:
            item = normalize_item(raw_item)
            normalized.append(item)
        except Exception as e:
            logger.warning(f"Error normalizing item '{raw_item.title[:50]}': {e}")
            continue
    
    logger.info(f"Normalized {len(normalized)} of {len(raw_items)} items")
    return normalized
