"""Utils module for GoalFeed."""
from .timeutils import (
    get_timezone,
    now_in_tz,
    utc_now,
    parse_time_string,
    is_within_active_window,
    parse_rss_date,
    get_recency_minutes,
    get_date_bucket,
    get_start_of_day,
    get_start_of_hour,
    minutes_since,
    datetime_to_iso,
    iso_to_datetime,
    format_relative_time
)

from .text import (
    normalize_title,
    canonicalize_url,
    get_domain,
    generate_article_hash,
    truncate_text,
    clean_html,
    extract_first_sentence,
    extract_keywords,
    is_valid_url,
    make_telegram_safe
)

__all__ = [
    # Time utilities
    'get_timezone',
    'now_in_tz',
    'utc_now',
    'parse_time_string',
    'is_within_active_window',
    'parse_rss_date',
    'get_recency_minutes',
    'get_date_bucket',
    'get_start_of_day',
    'get_start_of_hour',
    'minutes_since',
    'datetime_to_iso',
    'iso_to_datetime',
    'format_relative_time',
    # Text utilities
    'normalize_title',
    'canonicalize_url',
    'get_domain',
    'generate_article_hash',
    'truncate_text',
    'clean_html',
    'extract_first_sentence',
    'extract_keywords',
    'is_valid_url',
    'make_telegram_safe'
]
