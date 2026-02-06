"""
Ranking module for GoalFeed.
Calculates importance scores for articles.
"""
import logging
from typing import List, Optional
import re

from config import get_config
from processor.normalize import NormalizedItem
from utils.timeutils import get_recency_minutes
from db.repo import get_repository

logger = logging.getLogger(__name__)


# Big entities that boost score
BIG_ENTITIES = {
    "football_eu": [
        # Top clubs
        "real madrid", "barcelona", "barça", "manchester united", "man utd",
        "manchester city", "man city", "liverpool", "chelsea", "arsenal",
        "tottenham", "spurs", "juventus", "juve", "ac milan", "inter milan",
        "psg", "paris saint-germain", "bayern munich", "bayern", "dortmund",
        "atletico madrid", "atlético", "napoli", "roma",
        # Top players
        "messi", "cristiano ronaldo", "mbappe", "mbappé", "haaland",
        "bellingham", "vinicius", "vinícius", "neymar", "salah", "de bruyne",
        "modric", "kroos", "pedri", "gavi", "saka", "foden", "valverde",
        # Big competitions
        "champions league", "world cup", "mundial", "eurocopa", "euro 2024",
        "copa del rey", "fa cup", "premier league", "la liga"
    ],
    "nba": [
        # Top teams
        "lakers", "celtics", "warriors", "bulls", "knicks", "nets",
        "heat", "bucks", "suns", "nuggets", "clippers", "mavericks",
        # Top players
        "lebron", "lebron james", "stephen curry", "steph curry",
        "kevin durant", "kd", "giannis", "jokic", "embiid", "luka doncic",
        "luka", "tatum", "ja morant", "anthony davis", "kawhi",
        # Big events
        "nba finals", "all-star", "playoffs", "draft", "trade deadline"
    ],
    "tennis": [
        # Top players
        "djokovic", "nadal", "federer", "alcaraz", "sinner", "medvedev",
        "zverev", "tsitsipas", "rublev", "ruud",
        "swiatek", "sabalenka", "gauff", "rybakina", "pegula",
        # Grand Slams
        "wimbledon", "roland garros", "us open", "australian open",
        "grand slam", "atp finals", "wta finals"
    ]
}


# Category score bonuses
CATEGORY_BONUSES = {
    "breaking": 15,
    "injury": 10,
    "transfer": 8,
    "controversy": 7,
    "match_result": 5,
    "stats": 3,
    "schedule": 0,
    "default": 0
}


def calculate_recency_score(item: NormalizedItem) -> int:
    """
    Calculate recency score (0-30).
    More recent = higher score.
    
    Args:
        item: NormalizedItem to score
        
    Returns:
        Recency score (0-30)
    """
    minutes = get_recency_minutes(item.published_at)
    
    if minutes < 30:
        return 30  # Very fresh
    elif minutes < 60:
        return 25
    elif minutes < 120:
        return 20
    elif minutes < 240:  # 4 hours
        return 15
    elif minutes < 480:  # 8 hours
        return 10
    elif minutes < 720:  # 12 hours
        return 5
    else:
        return 0


def calculate_source_score(item: NormalizedItem) -> int:
    """
    Calculate source weight score (0-25).
    
    Args:
        item: NormalizedItem to score
        
    Returns:
        Source score (0-25)
    """
    # Source weight is 1-25, use it directly
    weight = item.source_weight
    return min(25, max(0, weight))


def calculate_entity_score(item: NormalizedItem) -> int:
    """
    Calculate big entity score (0-25).
    Boost for mentions of important teams, players, events.
    
    Args:
        item: NormalizedItem to score
        
    Returns:
        Entity score (0-25)
    """
    text = (item.title + " " + (item.summary or "")).lower()
    sport = item.sport
    
    entities = BIG_ENTITIES.get(sport, [])
    
    matches = 0
    matched_entities = set()
    
    for entity in entities:
        pattern = r'\b' + re.escape(entity.lower()) + r'\b'
        if re.search(pattern, text):
            # Avoid double-counting similar entities
            base_entity = entity.split()[0]  # First word
            if base_entity not in matched_entities:
                matches += 1
                matched_entities.add(base_entity)
    
    # Score: 5 points per entity, max 25
    return min(25, matches * 5)


def calculate_category_score(item: NormalizedItem) -> int:
    """
    Calculate category bonus (0-15).
    
    Args:
        item: NormalizedItem to score
        
    Returns:
        Category bonus score
    """
    return CATEGORY_BONUSES.get(item.category, 0)


def calculate_repetition_penalty(item: NormalizedItem) -> int:
    """
    Calculate repetition penalty (-10 to 0).
    Penalize if similar articles already posted today.
    
    Args:
        item: NormalizedItem to check
        
    Returns:
        Penalty (negative value or 0)
    """
    try:
        repo = get_repository()
        
        # Get recent posted articles
        recent_posts = repo.get_recent_posts(hours=24)
        
        # Check for similar topics
        similar_count = 0
        item_keywords = set(item.normalized_title.split())
        
        for post in recent_posts:
            if not post.get('article_title'):
                continue
            
            post_title = post['article_title'].lower()
            post_keywords = set(post_title.split())
            
            # Check overlap
            overlap = len(item_keywords & post_keywords)
            if overlap >= 3:  # At least 3 common words
                similar_count += 1
        
        # Penalty for repeated topics
        if similar_count >= 2:
            return -10
        elif similar_count == 1:
            return -5
        
        return 0
        
    except Exception as e:
        logger.warning(f"Error calculating repetition penalty: {e}")
        return 0


def calculate_score(item: NormalizedItem) -> int:
    """
    Calculate total importance score (0-100).
    
    Components:
    - Recency: 0-30
    - Source weight: 0-25
    - Big entities: 0-25
    - Category bonus: 0-15
    - Repetition penalty: -10 to 0
    
    Args:
        item: NormalizedItem to score
        
    Returns:
        Total score (0-100)
    """
    recency = calculate_recency_score(item)
    source = calculate_source_score(item)
    entity = calculate_entity_score(item)
    category = calculate_category_score(item)
    penalty = calculate_repetition_penalty(item)
    
    total = recency + source + entity + category + penalty
    
    # Clamp to 0-100
    total = max(0, min(100, total))
    
    logger.debug(
        f"Score for '{item.title[:40]}...': "
        f"recency={recency}, source={source}, entity={entity}, "
        f"category={category}, penalty={penalty}, total={total}"
    )
    
    return total


def rank_item(item: NormalizedItem) -> NormalizedItem:
    """
    Calculate and set the score for an item.
    
    Args:
        item: NormalizedItem to rank
        
    Returns:
        Same item with score set
    """
    item.score = calculate_score(item)
    return item


def rank_all(items: list[NormalizedItem]) -> list[NormalizedItem]:
    """
    Rank all items and sort by score.
    
    Args:
        items: List of NormalizedItem objects
        
    Returns:
        List sorted by score (descending)
    """
    for item in items:
        try:
            rank_item(item)
        except Exception as e:
            logger.warning(f"Error ranking item '{item.title[:50]}': {e}")
            item.score = 0
    
    # Sort by score descending
    ranked = sorted(items, key=lambda x: x.score, reverse=True)
    
    # Log top scores
    if ranked:
        logger.info(
            f"Top scores: {[f'{i.score}:{i.title[:30]}' for i in ranked[:5]]}"
        )
    
    return ranked
