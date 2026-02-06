"""
Classification module for GoalFeed.
Classifies articles by sport and category using heuristics.
"""
import logging
from typing import Optional, Tuple
import re

from config import SPORT_KEYWORDS, CATEGORY_KEYWORDS, OFFICIAL_DOMAINS
from processor.normalize import NormalizedItem

logger = logging.getLogger(__name__)


def classify_sport(item: NormalizedItem) -> str:
    """
    Classify the sport of an article.
    
    Priority:
    1. Use sport_hint from source if available
    2. Keyword matching in title, summary, categories
    
    Args:
        item: NormalizedItem to classify
        
    Returns:
        Sport identifier (football_eu, nba, tennis)
    """
    # Start with source hint
    if item.source_sport_hint:
        return item.source_sport_hint
    
    # Combine text for analysis
    text_to_analyze = " ".join([
        item.title.lower(),
        (item.summary or "").lower(),
        " ".join(item.categories).lower()
    ])
    
    # Count keyword matches for each sport
    sport_scores = {}
    
    for sport, keywords in SPORT_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            matches = len(re.findall(pattern, text_to_analyze))
            score += matches
        
        sport_scores[sport] = score
    
    # Return sport with highest score, default to football_eu
    if sport_scores:
        best_sport = max(sport_scores, key=sport_scores.get)
        if sport_scores[best_sport] > 0:
            return best_sport
    
    return "football_eu"


def classify_category(item: NormalizedItem) -> str:
    """
    Classify the category of an article.
    
    Categories: transfer, injury, match_result, controversy, breaking, stats, schedule
    
    Args:
        item: NormalizedItem to classify
        
    Returns:
        Category identifier
    """
    # Combine text for analysis
    text_to_analyze = " ".join([
        item.title.lower(),
        (item.summary or "").lower(),
        " ".join(item.categories).lower()
    ])
    
    # Count keyword matches for each category
    category_scores = {}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            matches = len(re.findall(pattern, text_to_analyze))
            
            # Give title matches more weight
            title_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            title_matches = len(re.findall(title_pattern, item.title.lower()))
            
            score += matches + (title_matches * 2)  # Title matches worth more
        
        category_scores[category] = score
    
    # Check for "breaking" keywords first (highest priority)
    if category_scores.get('breaking', 0) >= 2:
        return 'breaking'
    
    # Return category with highest score
    if category_scores:
        best_category = max(category_scores, key=category_scores.get)
        if category_scores[best_category] > 0:
            return best_category
    
    # Default to None (will be handled as 'default' in templates)
    return 'default'


def determine_status(item: NormalizedItem) -> str:
    """
    Determine the verification status of an article.
    
    Status types:
    - CONFIRMADO: Official source or multiple sources
    - RUMOR: Single non-official source
    - EN_DESARROLLO: Breaking/developing story
    
    Args:
        item: NormalizedItem to analyze
        
    Returns:
        Status identifier
    """
    # Check if source domain is official
    if item.source_domain in OFFICIAL_DOMAINS:
        return "CONFIRMADO"
    
    # Check for "en desarrollo" keywords
    desarrollo_keywords = [
        'en desarrollo', 'breaking', 'última hora', 'developing',
        'live', 'en vivo', 'directo', 'ahora mismo', 'just in',
        'en curso', 'ongoing'
    ]
    
    text = (item.title + " " + (item.summary or "")).lower()
    
    for keyword in desarrollo_keywords:
        if keyword in text:
            return "EN_DESARROLLO"
    
    # Check for "confirmado/oficial" keywords
    confirmed_keywords = [
        'oficial', 'official', 'confirmado', 'confirmed',
        'comunicado', 'announcement', 'done deal', 'ya es',
        'firma', 'signed', 'agree', 'acuerdo cerrado'
    ]
    
    for keyword in confirmed_keywords:
        if keyword in text:
            return "CONFIRMADO"
    
    # Default to RUMOR for single source
    return "RUMOR"


def classify_item(item: NormalizedItem) -> NormalizedItem:
    """
    Fully classify an item (sport, category, status).
    
    Args:
        item: NormalizedItem to classify
        
    Returns:
        Same item with classification fields filled
    """
    item.sport = classify_sport(item)
    item.category = classify_category(item)
    item.status = determine_status(item)
    
    logger.debug(
        f"Classified: '{item.title[:40]}...' -> "
        f"sport={item.sport}, category={item.category}, status={item.status}"
    )
    
    return item


def classify_all(items: list[NormalizedItem]) -> list[NormalizedItem]:
    """
    Classify all items in a list.
    
    Args:
        items: List of NormalizedItem objects
        
    Returns:
        Same list with classification fields filled
    """
    classified = []
    
    for item in items:
        try:
            classify_item(item)
            classified.append(item)
        except Exception as e:
            logger.warning(f"Error classifying item '{item.title[:50]}': {e}")
            continue
    
    logger.info(f"Classified {len(classified)} items")
    
    # Log classification summary
    sports = {}
    categories = {}
    for item in classified:
        sports[item.sport] = sports.get(item.sport, 0) + 1
        categories[item.category] = categories.get(item.category, 0) + 1
    
    logger.debug(f"Sports distribution: {sports}")
    logger.debug(f"Category distribution: {categories}")
    
    return classified
