"""
Database repository functions for GoalFeed.
High-level database operations for articles, posts, sources, etc.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import json

from .database import get_database, Database
from utils.timeutils import utc_now, get_start_of_day, datetime_to_iso

logger = logging.getLogger(__name__)


@dataclass
class ArticleRecord:
    """Article data structure for database operations."""
    id: Optional[int] = None
    source_id: Optional[int] = None
    title: str = ""
    normalized_title: str = ""
    link: str = ""
    canonical_url: str = ""
    summary: Optional[str] = None
    published_at: Optional[str] = None
    sport: str = "football_eu"
    category: Optional[str] = None
    status: str = "RUMOR"
    score: int = 0
    content_hash: str = ""
    image_url: Optional[str] = None
    source_name: Optional[str] = None
    source_domain: Optional[str] = None
    is_duplicate: bool = False
    is_posted: bool = False
    is_digested: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class PostRecord:
    """Post data structure for database operations."""
    id: Optional[int] = None
    article_id: Optional[int] = None
    telegram_message_id: Optional[int] = None
    telegram_chat_id: Optional[str] = None
    caption: Optional[str] = None
    image_path: Optional[str] = None
    sport: Optional[str] = None
    post_type: str = "single"
    posted_at: Optional[str] = None


class Repository:
    """Database repository for all GoalFeed operations."""
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize repository.
        
        Args:
            db: Database instance (uses global if not provided)
        """
        self.db = db or get_database()
    
    # ===================
    # SOURCES
    # ===================
    
    def get_sources(self, active_only: bool = True) -> List[Dict]:
        """
        Get all RSS sources.
        
        Args:
            active_only: Only return active sources
            
        Returns:
            List of source dictionaries
        """
        query = "SELECT * FROM sources"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY weight DESC, name ASC"
        
        rows = self.db.fetchall(query)
        return [dict(row) for row in rows]
    
    def upsert_source(self, name: str, url: str, sport_hint: str, weight: int = 10) -> int:
        """
        Insert or update a source.
        
        Returns:
            Source ID
        """
        existing = self.db.fetchone(
            "SELECT id FROM sources WHERE url = ?",
            (url,)
        )
        
        if existing:
            self.db.execute(
                """UPDATE sources 
                   SET name = ?, sport_hint = ?, weight = ?, updated_at = ?
                   WHERE url = ?""",
                (name, sport_hint, weight, datetime_to_iso(utc_now()), url)
            )
            return existing['id']
        else:
            cursor = self.db.execute(
                """INSERT INTO sources (name, url, sport_hint, weight)
                   VALUES (?, ?, ?, ?)""",
                (name, url, sport_hint, weight)
            )
            return cursor.lastrowid
    
    def update_source_fetched(self, source_id: int):
        """Update the last_fetched_at timestamp for a source."""
        self.db.execute(
            "UPDATE sources SET last_fetched_at = ? WHERE id = ?",
            (datetime_to_iso(utc_now()), source_id)
        )
    
    def seed_sources(self, sources: List[Dict]):
        """
        Seed multiple sources into the database.
        
        Args:
            sources: List of source dicts with name, url, sport_hint, weight
        """
        for source in sources:
            self.upsert_source(
                name=source.get('name', ''),
                url=source.get('url', ''),
                sport_hint=source.get('sport_hint', 'football_eu'),
                weight=source.get('weight', 10)
            )
        logger.info(f"Seeded {len(sources)} sources")
    
    # ===================
    # ARTICLES
    # ===================
    
    def upsert_article(self, article: ArticleRecord) -> int:
        """
        Insert or update an article.
        
        Args:
            article: ArticleRecord to save
            
        Returns:
            Article ID
        """
        now = datetime_to_iso(utc_now())
        
        # Check if exists by canonical_url
        existing = self.db.fetchone(
            "SELECT id FROM articles WHERE canonical_url = ?",
            (article.canonical_url,)
        )
        
        if existing:
            # Update existing
            self.db.execute(
                """UPDATE articles SET
                   title = ?, normalized_title = ?, summary = ?,
                   sport = ?, category = ?, status = ?, score = ?,
                   image_url = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    article.title, article.normalized_title, article.summary,
                    article.sport, article.category, article.status, article.score,
                    article.image_url, now, existing['id']
                )
            )
            return existing['id']
        else:
            # Insert new
            cursor = self.db.execute(
                """INSERT INTO articles (
                    source_id, title, normalized_title, link, canonical_url,
                    summary, published_at, sport, category, status, score,
                    content_hash, image_url, source_name, source_domain,
                    is_duplicate, is_posted, is_digested, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    article.source_id, article.title, article.normalized_title,
                    article.link, article.canonical_url, article.summary,
                    article.published_at, article.sport, article.category,
                    article.status, article.score, article.content_hash,
                    article.image_url, article.source_name, article.source_domain,
                    int(article.is_duplicate), int(article.is_posted),
                    int(article.is_digested), now, now
                )
            )
            return cursor.lastrowid
    
    def get_article_by_id(self, article_id: int) -> Optional[Dict]:
        """Get an article by ID."""
        row = self.db.fetchone(
            "SELECT * FROM articles WHERE id = ?",
            (article_id,)
        )
        return dict(row) if row else None
    
    def get_article_by_canonical_url(self, canonical_url: str) -> Optional[Dict]:
        """Get an article by canonical URL."""
        row = self.db.fetchone(
            "SELECT * FROM articles WHERE canonical_url = ?",
            (canonical_url,)
        )
        return dict(row) if row else None
    
    def get_article_by_content_hash(self, content_hash: str) -> Optional[Dict]:
        """Get an article by content hash."""
        row = self.db.fetchone(
            "SELECT * FROM articles WHERE content_hash = ?",
            (content_hash,)
        )
        return dict(row) if row else None
    
    def is_duplicate(self, canonical_url: str, content_hash: str) -> bool:
        """
        Check if an article is a duplicate.
        
        Args:
            canonical_url: Canonical URL
            content_hash: Content hash
            
        Returns:
            True if duplicate exists
        """
        row = self.db.fetchone(
            """SELECT id FROM articles 
               WHERE canonical_url = ? OR content_hash = ?
               LIMIT 1""",
            (canonical_url, content_hash)
        )
        return row is not None
    
    def get_recent_articles(
        self,
        hours: int = 6,
        sport: Optional[str] = None,
        posted_only: bool = False,
        unposted_only: bool = False
    ) -> List[Dict]:
        """
        Get recent articles.
        
        Args:
            hours: How many hours back to look
            sport: Filter by sport
            posted_only: Only return posted articles
            unposted_only: Only return unposted articles
            
        Returns:
            List of article dicts
        """
        cutoff = utc_now() - timedelta(hours=hours)
        cutoff_str = datetime_to_iso(cutoff)
        
        query = "SELECT * FROM articles WHERE created_at >= ?"
        params = [cutoff_str]
        
        if sport:
            query += " AND sport = ?"
            params.append(sport)
        
        if posted_only:
            query += " AND is_posted = 1"
        elif unposted_only:
            query += " AND is_posted = 0 AND is_duplicate = 0"
        
        query += " ORDER BY score DESC, created_at DESC"
        
        rows = self.db.fetchall(query, tuple(params))
        return [dict(row) for row in rows]
    
    def get_unposted_candidates(
        self,
        min_score: int = 0,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get unposted article candidates for publishing.
        
        Args:
            min_score: Minimum score threshold
            limit: Maximum number of results
            
        Returns:
            List of candidate article dicts
        """
        rows = self.db.fetchall(
            """SELECT * FROM articles 
               WHERE is_posted = 0 
               AND is_duplicate = 0 
               AND is_digested = 0
               AND score >= ?
               ORDER BY score DESC, created_at DESC
               LIMIT ?""",
            (min_score, limit)
        )
        return [dict(row) for row in rows]
    
    def get_digest_candidates(
        self,
        sport: str,
        window_minutes: int = 20,
        score_min: int = 55,
        score_max: int = 75
    ) -> List[Dict]:
        """
        Get candidates for digest aggregation.
        
        Args:
            sport: Sport type
            window_minutes: Time window in minutes
            score_min: Minimum score
            score_max: Maximum score
            
        Returns:
            List of candidate articles
        """
        cutoff = utc_now() - timedelta(minutes=window_minutes)
        cutoff_str = datetime_to_iso(cutoff)
        
        rows = self.db.fetchall(
            """SELECT * FROM articles 
               WHERE sport = ?
               AND is_posted = 0 
               AND is_duplicate = 0
               AND is_digested = 0
               AND score >= ? AND score <= ?
               AND created_at >= ?
               ORDER BY score DESC
               LIMIT 10""",
            (sport, score_min, score_max, cutoff_str)
        )
        return [dict(row) for row in rows]
    
    def mark_article_posted(self, article_id: int):
        """Mark an article as posted."""
        self.db.execute(
            "UPDATE articles SET is_posted = 1, updated_at = ? WHERE id = ?",
            (datetime_to_iso(utc_now()), article_id)
        )
    
    def mark_article_duplicate(self, article_id: int):
        """Mark an article as duplicate."""
        self.db.execute(
            "UPDATE articles SET is_duplicate = 1, updated_at = ? WHERE id = ?",
            (datetime_to_iso(utc_now()), article_id)
        )
    
    def mark_articles_digested(self, article_ids: List[int]):
        """Mark multiple articles as included in a digest."""
        now = datetime_to_iso(utc_now())
        for article_id in article_ids:
            self.db.execute(
                "UPDATE articles SET is_digested = 1, updated_at = ? WHERE id = ?",
                (now, article_id)
            )
    
    def get_similar_titles_recent(
        self,
        normalized_title: str,
        hours: int = 6
    ) -> List[Dict]:
        """
        Get articles with similar titles in recent hours.
        Used for fuzzy deduplication.
        
        Args:
            normalized_title: Normalized title to compare
            hours: Hours to look back
            
        Returns:
            List of recent articles for comparison
        """
        cutoff = utc_now() - timedelta(hours=hours)
        cutoff_str = datetime_to_iso(cutoff)
        
        rows = self.db.fetchall(
            """SELECT id, normalized_title, canonical_url FROM articles 
               WHERE created_at >= ?
               ORDER BY created_at DESC
               LIMIT 500""",
            (cutoff_str,)
        )
        return [dict(row) for row in rows]
    
    # ===================
    # POSTS
    # ===================
    
    def record_post(
        self,
        article_id: int,
        telegram_message_id: int,
        telegram_chat_id: str,
        caption: str,
        image_path: Optional[str] = None,
        sport: Optional[str] = None,
        post_type: str = "single"
    ) -> int:
        """
        Record a published post.
        
        Returns:
            Post ID
        """
        cursor = self.db.execute(
            """INSERT INTO posts (
                article_id, telegram_message_id, telegram_chat_id,
                caption, image_path, sport, post_type, posted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                article_id, telegram_message_id, telegram_chat_id,
                caption, image_path, sport, post_type,
                datetime_to_iso(utc_now())
            )
        )
        
        # Mark article as posted
        self.mark_article_posted(article_id)
        
        # Update daily stats
        self._increment_daily_posts()
        
        return cursor.lastrowid
    
    def count_posts_today(self, tz_name: str = "Europe/Madrid") -> int:
        """
        Count posts made today.
        
        Args:
            tz_name: Timezone for 'today' calculation
            
        Returns:
            Number of posts today
        """
        start_of_day = get_start_of_day(tz_name)
        start_str = datetime_to_iso(start_of_day)
        
        row = self.db.fetchone(
            "SELECT COUNT(*) as count FROM posts WHERE posted_at >= ?",
            (start_str,)
        )
        return row['count'] if row else 0
    
    def count_posts_last_hour(self) -> int:
        """
        Count posts in the last hour.
        
        Returns:
            Number of posts in last hour
        """
        cutoff = utc_now() - timedelta(hours=1)
        cutoff_str = datetime_to_iso(cutoff)
        
        row = self.db.fetchone(
            "SELECT COUNT(*) as count FROM posts WHERE posted_at >= ?",
            (cutoff_str,)
        )
        return row['count'] if row else 0
    
    def last_post_time_by_sport(self, sport: str) -> Optional[datetime]:
        """
        Get the last post time for a sport.
        
        Args:
            sport: Sport type
            
        Returns:
            Last post datetime or None
        """
        row = self.db.fetchone(
            """SELECT posted_at FROM posts 
               WHERE sport = ? 
               ORDER BY posted_at DESC 
               LIMIT 1""",
            (sport,)
        )
        
        if row and row['posted_at']:
            from utils.timeutils import iso_to_datetime
            return iso_to_datetime(row['posted_at'])
        return None
    
    def get_recent_posts(self, hours: int = 24) -> List[Dict]:
        """Get posts from the last N hours."""
        cutoff = utc_now() - timedelta(hours=hours)
        cutoff_str = datetime_to_iso(cutoff)
        
        rows = self.db.fetchall(
            """SELECT p.*, a.title as article_title
               FROM posts p
               LEFT JOIN articles a ON p.article_id = a.id
               WHERE p.posted_at >= ?
               ORDER BY p.posted_at DESC""",
            (cutoff_str,)
        )
        return [dict(row) for row in rows]
    
    # ===================
    # DIGESTS
    # ===================
    
    def record_digest(
        self,
        article_ids: List[int],
        telegram_message_id: int,
        telegram_chat_id: str,
        caption: str,
        image_path: Optional[str] = None,
        sport: str = "football_eu"
    ) -> int:
        """
        Record a published digest.
        
        Returns:
            Digest ID
        """
        cursor = self.db.execute(
            """INSERT INTO digests (
                telegram_message_id, telegram_chat_id, caption,
                image_path, sport, article_count, posted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                telegram_message_id, telegram_chat_id, caption,
                image_path, sport, len(article_ids),
                datetime_to_iso(utc_now())
            )
        )
        
        digest_id = cursor.lastrowid
        
        # Record digest items
        for pos, article_id in enumerate(article_ids):
            self.db.execute(
                """INSERT INTO digest_items (digest_id, article_id, position)
                   VALUES (?, ?, ?)""",
                (digest_id, article_id, pos)
            )
        
        # Mark articles as digested
        self.mark_articles_digested(article_ids)
        
        # Update daily stats
        self._increment_daily_digests()
        
        return digest_id
    
    def count_digests_today(self, tz_name: str = "Europe/Madrid") -> int:
        """Count digests made today."""
        start_of_day = get_start_of_day(tz_name)
        start_str = datetime_to_iso(start_of_day)
        
        row = self.db.fetchone(
            "SELECT COUNT(*) as count FROM digests WHERE posted_at >= ?",
            (start_str,)
        )
        return row['count'] if row else 0
    
    # ===================
    # DAILY STATS
    # ===================
    
    def _get_today_date(self) -> str:
        """Get today's date string."""
        return utc_now().strftime("%Y-%m-%d")
    
    def _ensure_daily_stats(self):
        """Ensure today's daily stats row exists."""
        today = self._get_today_date()
        existing = self.db.fetchone(
            "SELECT id FROM daily_stats WHERE date = ?",
            (today,)
        )
        if not existing:
            self.db.execute(
                "INSERT INTO daily_stats (date) VALUES (?)",
                (today,)
            )
    
    def _increment_daily_posts(self):
        """Increment today's post count."""
        self._ensure_daily_stats()
        today = self._get_today_date()
        self.db.execute(
            """UPDATE daily_stats 
               SET post_count = post_count + 1, updated_at = ?
               WHERE date = ?""",
            (datetime_to_iso(utc_now()), today)
        )
    
    def _increment_daily_digests(self):
        """Increment today's digest count."""
        self._ensure_daily_stats()
        today = self._get_today_date()
        self.db.execute(
            """UPDATE daily_stats 
               SET digest_count = digest_count + 1, updated_at = ?
               WHERE date = ?""",
            (datetime_to_iso(utc_now()), today)
        )
    
    def increment_articles_fetched(self, count: int = 1):
        """Increment today's fetched article count."""
        self._ensure_daily_stats()
        today = self._get_today_date()
        self.db.execute(
            """UPDATE daily_stats 
               SET articles_fetched = articles_fetched + ?, updated_at = ?
               WHERE date = ?""",
            (count, datetime_to_iso(utc_now()), today)
        )
    
    def increment_articles_duplicated(self, count: int = 1):
        """Increment today's duplicated article count."""
        self._ensure_daily_stats()
        today = self._get_today_date()
        self.db.execute(
            """UPDATE daily_stats 
               SET articles_duplicated = articles_duplicated + ?, updated_at = ?
               WHERE date = ?""",
            (count, datetime_to_iso(utc_now()), today)
        )
    
    def get_daily_stats(self, date: Optional[str] = None) -> Optional[Dict]:
        """Get daily stats for a specific date."""
        if date is None:
            date = self._get_today_date()
        
        row = self.db.fetchone(
            "SELECT * FROM daily_stats WHERE date = ?",
            (date,)
        )
        return dict(row) if row else None
    
    # ===================
    # SETTINGS
    # ===================
    
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value."""
        row = self.db.fetchone(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        )
        return row['value'] if row else default
    
    def set_setting(self, key: str, value: str):
        """Set a setting value."""
        self.db.execute(
            """INSERT OR REPLACE INTO settings (key, value, updated_at)
               VALUES (?, ?, ?)""",
            (key, value, datetime_to_iso(utc_now()))
        )
    
    # ===================
    # LIVE MATCHES
    # ===================
    
    def upsert_live_match(
        self,
        match_id: str,
        league_id: int,
        league_name: str,
        home_team: str,
        away_team: str,
        home_score: int = 0,
        away_score: int = 0,
        match_status: str = "NS",
        current_minute: int = 0,
        is_top_team_match: bool = False,
        match_start: Optional[str] = None
    ) -> int:
        """
        Insert or update a live match.
        
        Returns:
            Match row ID
        """
        now = datetime_to_iso(utc_now())
        
        existing = self.db.fetchone(
            "SELECT id FROM live_matches WHERE match_id = ?",
            (match_id,)
        )
        
        if existing:
            self.db.execute(
                """UPDATE live_matches SET
                   home_score = ?, away_score = ?, match_status = ?,
                   current_minute = ?, updated_at = ?
                   WHERE match_id = ?""",
                (home_score, away_score, match_status, current_minute, now, match_id)
            )
            return existing['id']
        else:
            cursor = self.db.execute(
                """INSERT INTO live_matches (
                    match_id, league_id, league_name, home_team, away_team,
                    home_score, away_score, match_status, current_minute,
                    is_top_team_match, match_start, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    match_id, league_id, league_name, home_team, away_team,
                    home_score, away_score, match_status, current_minute,
                    int(is_top_team_match), match_start, now, now
                )
            )
            return cursor.lastrowid
    
    def get_live_match(self, match_id: str) -> Optional[Dict]:
        """Get a live match by match_id."""
        row = self.db.fetchone(
            "SELECT * FROM live_matches WHERE match_id = ?",
            (match_id,)
        )
        return dict(row) if row else None
    
    def get_active_live_matches(self) -> List[Dict]:
        """Get all active (non-finished) live matches."""
        rows = self.db.fetchall(
            """SELECT * FROM live_matches 
               WHERE match_status NOT IN ('FT', 'AET', 'PEN', 'CANC', 'PST', 'ABD')
               ORDER BY created_at DESC"""
        )
        return [dict(row) for row in rows]
    
    def increment_match_events(self, match_id: str):
        """Increment the events_published counter for a match."""
        now = datetime_to_iso(utc_now())
        self.db.execute(
            """UPDATE live_matches 
               SET events_published = events_published + 1,
                   last_event_at = ?,
                   updated_at = ?
               WHERE match_id = ?""",
            (now, now, match_id)
        )
    
    def get_match_event_count(self, match_id: str) -> int:
        """Get the number of events published for a match."""
        row = self.db.fetchone(
            "SELECT events_published FROM live_matches WHERE match_id = ?",
            (match_id,)
        )
        return row['events_published'] if row else 0
    
    def get_last_event_time(self, match_id: str) -> Optional[datetime]:
        """Get the last event time for a match."""
        row = self.db.fetchone(
            "SELECT last_event_at FROM live_matches WHERE match_id = ?",
            (match_id,)
        )
        if row and row['last_event_at']:
            from utils.timeutils import iso_to_datetime
            return iso_to_datetime(row['last_event_at'])
        return None
    
    # ===================
    # LIVE EVENTS
    # ===================
    
    def record_live_event(
        self,
        match_id: str,
        league_id: int,
        league_name: str,
        home_team: str,
        away_team: str,
        home_score: int,
        away_score: int,
        event_type: str,
        event_minute: Optional[int] = None,
        event_player: Optional[str] = None,
        event_detail: Optional[str] = None,
        telegram_message_id: Optional[int] = None,
        telegram_chat_id: Optional[str] = None
    ) -> Optional[int]:
        """
        Record a live event.
        
        Returns:
            Event ID or None if duplicate
        """
        now = datetime_to_iso(utc_now())
        
        try:
            cursor = self.db.execute(
                """INSERT INTO live_events (
                    match_id, league_id, league_name, home_team, away_team,
                    home_score, away_score, event_type, event_minute,
                    event_player, event_detail, telegram_message_id,
                    telegram_chat_id, is_published, published_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    match_id, league_id, league_name, home_team, away_team,
                    home_score, away_score, event_type, event_minute,
                    event_player, event_detail, telegram_message_id,
                    telegram_chat_id, 1 if telegram_message_id else 0,
                    now if telegram_message_id else None, now
                )
            )
            return cursor.lastrowid
        except Exception as e:
            # Likely duplicate constraint violation
            logger.warning(f"Could not record live event (likely duplicate): {e}")
            return None
    
    def is_event_published(
        self,
        match_id: str,
        event_type: str,
        event_minute: Optional[int] = None,
        event_player: Optional[str] = None
    ) -> bool:
        """Check if an event has already been published."""
        if event_minute is not None and event_player:
            row = self.db.fetchone(
                """SELECT id FROM live_events 
                   WHERE match_id = ? AND event_type = ? 
                   AND event_minute = ? AND event_player = ?""",
                (match_id, event_type, event_minute, event_player)
            )
        elif event_type == 'final':
            row = self.db.fetchone(
                """SELECT id FROM live_events 
                   WHERE match_id = ? AND event_type = 'final'""",
                (match_id,)
            )
        else:
            row = self.db.fetchone(
                """SELECT id FROM live_events 
                   WHERE match_id = ? AND event_type = ?""",
                (match_id, event_type)
            )
        
        return row is not None
    
    def get_match_events(self, match_id: str) -> List[Dict]:
        """Get all events for a match."""
        rows = self.db.fetchall(
            """SELECT * FROM live_events 
               WHERE match_id = ?
               ORDER BY event_minute ASC, created_at ASC""",
            (match_id,)
        )
        return [dict(row) for row in rows]
    
    def count_live_events_today(self, tz_name: str = "Europe/Madrid") -> int:
        """Count live events published today."""
        start_of_day = get_start_of_day(tz_name)
        start_str = datetime_to_iso(start_of_day)
        
        row = self.db.fetchone(
            """SELECT COUNT(*) as count FROM live_events 
               WHERE is_published = 1 AND published_at >= ?""",
            (start_str,)
        )
        return row['count'] if row else 0


# Convenience function
def get_repository() -> Repository:
    """Get a Repository instance."""
    return Repository()
