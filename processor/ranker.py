"""
Ranking module for GoalFeed.
Calculates importance scores for articles.
"""
import logging
from typing import List, Optional
import re

from config import get_config, TRANSFER_SPECIALIST_DOMAINS
from processor.normalize import NormalizedItem
from utils.timeutils import get_recency_minutes
from db.repo import get_repository

logger = logging.getLogger(__name__)


# Big entities that boost score (football only)
BIG_ENTITIES = {
    "football_eu": [
        # Top Spanish clubs
        "real madrid", "barcelona", "barça", "atletico madrid", "atlético",
        "sevilla", "valencia", "villarreal", "real betis", "real sociedad",
        # Top English clubs
        "manchester united", "man utd", "manchester city", "man city",
        "liverpool", "chelsea", "arsenal", "tottenham", "spurs",
        "newcastle", "aston villa", "west ham",
        # Top Italian clubs
        "juventus", "juve", "ac milan", "inter milan", "inter",
        "napoli", "roma", "lazio", "atalanta", "fiorentina",
        # Top German clubs
        "bayern munich", "bayern", "dortmund", "borussia dortmund",
        "bayer leverkusen", "leverkusen", "rb leipzig", "leipzig",
        # Top French clubs
        "psg", "paris saint-germain", "marseille", "lyon", "monaco", "lille",
        # Portuguese clubs
        "benfica", "porto", "sporting cp",
        # Dutch clubs
        "ajax", "psv", "feyenoord",
        # Other notable clubs
        "celtic", "rangers", "galatasaray", "fenerbahce",
        # Top players (current)
        "messi", "cristiano ronaldo", "mbappe", "mbappé", "haaland",
        "bellingham", "vinicius", "vinícius", "salah", "de bruyne",
        "modric", "pedri", "gavi", "saka", "foden", "valverde",
        "yamal", "lamine yamal", "endrick", "arda guler", "arda güler",
        "cole palmer", "palmer", "rice", "declan rice",
        "odegaard", "ødegaard", "wirtz", "florian wirtz",
        "musiala", "jamal musiala", "kane", "harry kane",
        "osimhen", "victor osimhen", "neymar",
        "lewandowski", "raphinha", "olmo", "dani olmo",
        "rodri", "bernardo silva", "bruno fernandes",
        "son", "heung-min son", "alexander-arnold",
        "tchouameni", "camavinga", "militao",
        # Top managers
        "ancelotti", "guardiola", "klopp", "arteta", "simeone",
        "xavi", "flick", "mourinho", "nagelsmann", "conte",
        "slot", "emery", "ten hag", "de zerbi", "postecoglou",
        # Big competitions
        "champions league", "europa league", "conference league",
        "world cup", "mundial", "eurocopa", "nations league",
        "copa del rey", "fa cup", "premier league", "la liga", "laliga",
        "serie a", "bundesliga", "ligue 1", "dfb pokal",
        "coppa italia", "coupe de france", "supercopa",
        # Transfer market
        "mercado de fichajes", "deadline day", "ventana de transferencias",
    ]
}


# Category score bonuses
CATEGORY_BONUSES = {
    "breaking": 18,
    "rumor": 15,
    "transfer": 12,
    "injury": 10,
    "controversy": 8,
    "match_result": 5,
    "stats": 3,
    "schedule": 0,
    "default": 0
}


def calculate_recency_score(item: NormalizedItem) -> int:
    """
    Calculate recency score (0-30).
    More recent = higher score.
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
    """
    weight = item.source_weight
    return min(25, max(0, weight))


def calculate_entity_score(item: NormalizedItem) -> int:
    """
    Calculate big entity score (0-25).
    Boost for mentions of important teams, players, events.
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
    Calculate category bonus (0-18).
    """
    return CATEGORY_BONUSES.get(item.category, 0)


def calculate_exclusivity_score(item: NormalizedItem) -> int:
    """
    Calculate exclusivity score (0-10).
    Bonus for exclusive/scoop content from specialist transfer sources.
    """
    score = 0
    text = (item.title + " " + (item.summary or "")).lower()

    # Check if source is a transfer specialist
    source_domain = (item.source_domain or "").lower()
    for domain in TRANSFER_SPECIALIST_DOMAINS:
        if domain in source_domain:
            score += 4
            break

    # Check for exclusivity keywords in text
    exclusivity_keywords = [
        "exclusiva", "exclusive", "primicia", "scoop",
        "en exclusiva", "informacion exclusiva",
        "puede adelantar", "hemos sabido",
        "fabrizio romano", "here we go",
    ]

    for keyword in exclusivity_keywords:
        if keyword in text:
            score += 3
            break

    # Check for specific reporter mentions (transfer specialists)
    reporter_keywords = [
        "fabrizio romano", "gerard romero", "matteo moretto",
        "david ornstein", "florian plettenberg",
    ]

    for reporter in reporter_keywords:
        if reporter in text:
            score += 3
            break

    return min(10, score)


def calculate_repetition_penalty(item: NormalizedItem) -> int:
    """
    Calculate repetition penalty (-10 to 0).
    Penalize if similar articles already posted today.
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
    - Category bonus: 0-18
    - Exclusivity bonus: 0-10
    - Repetition penalty: -10 to 0
    """
    recency = calculate_recency_score(item)
    source = calculate_source_score(item)
    entity = calculate_entity_score(item)
    category = calculate_category_score(item)
    exclusivity = calculate_exclusivity_score(item)
    penalty = calculate_repetition_penalty(item)

    total = recency + source + entity + category + exclusivity + penalty

    # Clamp to 0-100
    total = max(0, min(100, total))

    logger.debug(
        f"Score for '{item.title[:40]}...': "
        f"recency={recency}, source={source}, entity={entity}, "
        f"category={category}, exclusivity={exclusivity}, "
        f"penalty={penalty}, total={total}"
    )

    return total


def rank_item(item: NormalizedItem) -> NormalizedItem:
    """
    Calculate and set the score for an item.
    """
    item.score = calculate_score(item)
    return item


def rank_all(items: list[NormalizedItem]) -> list[NormalizedItem]:
    """
    Rank all items and sort by score.
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
