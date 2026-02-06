"""
Time utilities for GoalFeed.
Handles timezone conversions, active window checking, etc.
"""
import pytz
from datetime import datetime, timedelta
from typing import Optional
from dateutil import parser as dateutil_parser


def get_timezone(tz_name: str = "Europe/Madrid") -> pytz.timezone:
    """Get a pytz timezone object."""
    return pytz.timezone(tz_name)


def now_in_tz(tz_name: str = "Europe/Madrid") -> datetime:
    """Get current datetime in specified timezone."""
    tz = get_timezone(tz_name)
    return datetime.now(tz)


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(pytz.UTC)


def parse_time_string(time_str: str) -> tuple[int, int]:
    """
    Parse a time string like "08:00" into (hour, minute).
    
    Args:
        time_str: Time string in HH:MM format
        
    Returns:
        Tuple of (hour, minute)
    """
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1])


def is_within_active_window(
    start_time: str = "08:00",
    end_time: str = "23:30",
    tz_name: str = "Europe/Madrid"
) -> bool:
    """
    Check if current time is within the active publishing window.
    
    Args:
        start_time: Start of active window (HH:MM)
        end_time: End of active window (HH:MM)
        tz_name: Timezone name
        
    Returns:
        True if within active window
    """
    current = now_in_tz(tz_name)
    
    start_hour, start_min = parse_time_string(start_time)
    end_hour, end_min = parse_time_string(end_time)
    
    current_minutes = current.hour * 60 + current.minute
    start_minutes = start_hour * 60 + start_min
    end_minutes = end_hour * 60 + end_min
    
    return start_minutes <= current_minutes <= end_minutes


def parse_rss_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse various date formats from RSS feeds.
    
    Args:
        date_str: Date string from RSS feed
        
    Returns:
        Parsed datetime in UTC or None if parsing fails
    """
    if not date_str:
        return None
    
    try:
        parsed = dateutil_parser.parse(date_str)
        
        # If no timezone info, assume UTC
        if parsed.tzinfo is None:
            parsed = pytz.UTC.localize(parsed)
        else:
            parsed = parsed.astimezone(pytz.UTC)
        
        return parsed
    except (ValueError, TypeError):
        return None


def get_recency_minutes(published_at: Optional[datetime]) -> int:
    """
    Get how many minutes ago an article was published.
    
    Args:
        published_at: Article publication datetime (UTC)
        
    Returns:
        Minutes since publication, or 9999 if unknown
    """
    if not published_at:
        return 9999
    
    now = utc_now()
    
    # Ensure published_at is timezone-aware
    if published_at.tzinfo is None:
        published_at = pytz.UTC.localize(published_at)
    
    delta = now - published_at
    return int(delta.total_seconds() / 60)


def get_date_bucket(dt: Optional[datetime] = None) -> str:
    """
    Get a date bucket string for deduplication.
    Format: YYYY-MM-DD-HH (hourly bucket)
    
    Args:
        dt: Datetime to bucket (defaults to now)
        
    Returns:
        Date bucket string
    """
    if dt is None:
        dt = utc_now()
    
    return dt.strftime("%Y-%m-%d-%H")


def get_start_of_day(tz_name: str = "Europe/Madrid") -> datetime:
    """
    Get the start of the current day in specified timezone.
    
    Args:
        tz_name: Timezone name
        
    Returns:
        Datetime at start of day (00:00:00)
    """
    tz = get_timezone(tz_name)
    current = now_in_tz(tz_name)
    
    start_of_day = current.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_of_day


def get_start_of_hour() -> datetime:
    """Get the start of the current hour in UTC."""
    now = utc_now()
    return now.replace(minute=0, second=0, microsecond=0)


def minutes_since(dt: datetime) -> int:
    """
    Calculate minutes elapsed since a given datetime.
    
    Args:
        dt: Reference datetime
        
    Returns:
        Minutes elapsed
    """
    now = utc_now()
    
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    else:
        dt = dt.astimezone(pytz.UTC)
    
    delta = now - dt
    return int(delta.total_seconds() / 60)


def datetime_to_iso(dt: datetime) -> str:
    """Convert datetime to ISO format string."""
    return dt.isoformat()


def iso_to_datetime(iso_str: str) -> datetime:
    """Parse ISO format string to datetime."""
    return dateutil_parser.isoparse(iso_str)


def format_relative_time(dt: datetime) -> str:
    """
    Format a datetime as relative time (e.g., "hace 5 minutos").
    
    Args:
        dt: Datetime to format
        
    Returns:
        Relative time string in Spanish
    """
    minutes = minutes_since(dt)
    
    if minutes < 1:
        return "hace un momento"
    elif minutes < 60:
        return f"hace {minutes} minutos"
    elif minutes < 120:
        return "hace 1 hora"
    elif minutes < 1440:  # 24 hours
        hours = minutes // 60
        return f"hace {hours} horas"
    else:
        days = minutes // 1440
        return f"hace {days} días"
