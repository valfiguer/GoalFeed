"""Processor module for GoalFeed."""
from .normalize import NormalizedItem, normalize_item, normalize_all
from .classify import classify_sport, classify_category, determine_status, classify_item, classify_all
from .ranker import calculate_score, rank_item, rank_all
from .dedupe import check_duplicate, dedupe_item, dedupe_all

__all__ = [
    # Normalize
    'NormalizedItem',
    'normalize_item',
    'normalize_all',
    # Classify
    'classify_sport',
    'classify_category',
    'determine_status',
    'classify_item',
    'classify_all',
    # Ranker
    'calculate_score',
    'rank_item',
    'rank_all',
    # Dedupe
    'check_duplicate',
    'dedupe_item',
    'dedupe_all'
]
