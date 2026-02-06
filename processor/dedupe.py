"""
Deduplication module for GoalFeed.
Prevents duplicate articles from being processed or posted.
"""
import logging
from typing import List, Optional, Tuple

from rapidfuzz import fuzz

from config import get_config
from processor.normalize import NormalizedItem
from db.repo import get_repository

logger = logging.getLogger(__name__)


def is_url_duplicate(canonical_url: str) -> bool:
    """
    Check if a canonical URL already exists in database.
    
    Args:
        canonical_url: Canonical URL to check
        
    Returns:
        True if duplicate
    """
    repo = get_repository()
    existing = repo.get_article_by_canonical_url(canonical_url)
    return existing is not None


def is_hash_duplicate(content_hash: str) -> bool:
    """
    Check if a content hash already exists in database.
    
    Args:
        content_hash: Content hash to check
        
    Returns:
        True if duplicate
    """
    repo = get_repository()
    existing = repo.get_article_by_content_hash(content_hash)
    return existing is not None


def find_similar_title(
    normalized_title: str,
    threshold: float = 0.88,
    hours: int = 6
) -> Optional[dict]:
    """
    Find articles with similar titles using fuzzy matching.
    
    Args:
        normalized_title: Normalized title to compare
        threshold: Similarity threshold (0.0-1.0)
        hours: Hours to look back
        
    Returns:
        Most similar article dict or None
    """
    repo = get_repository()
    
    # Get recent articles for comparison
    recent = repo.get_similar_titles_recent(normalized_title, hours)
    
    best_match = None
    best_ratio = 0.0
    
    for article in recent:
        # Calculate similarity ratio
        ratio = fuzz.ratio(
            normalized_title,
            article['normalized_title']
        ) / 100.0
        
        if ratio >= threshold and ratio > best_ratio:
            best_ratio = ratio
            best_match = article
    
    if best_match:
        logger.debug(
            f"Found similar title (ratio={best_ratio:.2f}): "
            f"'{normalized_title[:40]}' ~ '{best_match['normalized_title'][:40]}'"
        )
    
    return best_match


def is_update_article(item: NormalizedItem) -> bool:
    """
    Check if an article is an update to existing news (not just duplicate).
    
    Updates are allowed if they contain certain keywords indicating
    new information (confirmado, oficial, parte medico, comunicado).
    
    Args:
        item: NormalizedItem to check
        
    Returns:
        True if this is an update
    """
    update_keywords = [
        'confirmado', 'confirmed', 'oficial', 'official',
        'parte medico', 'medical report', 'comunicado', 'announcement',
        'actualización', 'update', 'última hora', 'breaking',
        'definitivo', 'final', 'done deal'
    ]
    
    text = (item.title + " " + (item.summary or "")).lower()
    
    for keyword in update_keywords:
        if keyword in text:
            return True
    
    return False


def check_duplicate(item: NormalizedItem) -> Tuple[bool, str]:
    """
    Full duplicate check for an item.
    
    Args:
        item: NormalizedItem to check
        
    Returns:
        Tuple of (is_duplicate, reason)
    """
    config = get_config()
    
    # Check URL duplicate
    if is_url_duplicate(item.canonical_url):
        return True, "url_duplicate"
    
    # Check hash duplicate
    if is_hash_duplicate(item.content_hash):
        return True, "hash_duplicate"
    
    # Check fuzzy title match
    similar = find_similar_title(
        item.normalized_title,
        threshold=config.dedupe_similarity_threshold,
        hours=config.dedupe_hours_window
    )
    
    if similar:
        # Check if this is an update (allowed)
        if is_update_article(item):
            logger.info(
                f"Allowing update article: '{item.title[:50]}'"
            )
            return False, "update_allowed"
        
        return True, "title_similar"
    
    return False, "unique"


def dedupe_item(item: NormalizedItem) -> bool:
    """
    Check if item is duplicate and mark if so.
    
    Args:
        item: NormalizedItem to check
        
    Returns:
        True if item should be processed (not duplicate)
    """
    is_dup, reason = check_duplicate(item)
    
    if is_dup:
        logger.debug(
            f"Duplicate ({reason}): '{item.title[:50]}'"
        )
        return False
    
    return True


def dedupe_all(items: list[NormalizedItem]) -> list[NormalizedItem]:
    """
    Filter out duplicate items.
    
    Args:
        items: List of NormalizedItem objects
        
    Returns:
        List with duplicates removed
    """
    unique_items = []
    duplicate_count = 0
    
    # Also check against items in this batch
    seen_titles = set()
    seen_urls = set()
    
    for item in items:
        # Check against batch
        if item.canonical_url in seen_urls:
            duplicate_count += 1
            continue
        
        # Quick title similarity check within batch
        is_batch_dup = False
        for seen_title in seen_titles:
            ratio = fuzz.ratio(item.normalized_title, seen_title) / 100.0
            if ratio >= 0.88:
                is_batch_dup = True
                break
        
        if is_batch_dup:
            duplicate_count += 1
            continue
        
        # Check against database
        if not dedupe_item(item):
            duplicate_count += 1
            continue
        
        # Item is unique
        unique_items.append(item)
        seen_titles.add(item.normalized_title)
        seen_urls.add(item.canonical_url)
    
    logger.info(
        f"Dedupe: {len(unique_items)} unique, {duplicate_count} duplicates"
    )
    
    # Update stats
    if duplicate_count > 0:
        try:
            repo = get_repository()
            repo.increment_articles_duplicated(duplicate_count)
        except Exception:
            pass
    
    return unique_items
