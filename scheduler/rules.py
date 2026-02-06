"""
Publishing rules for GoalFeed.
Enforces rate limits, active windows, and cooldowns.
"""
import logging
from datetime import datetime
from typing import Optional

from config import get_config
from db.repo import get_repository
from utils.timeutils import (
    is_within_active_window,
    now_in_tz,
    minutes_since
)

logger = logging.getLogger(__name__)


class RulesChecker:
    """
    Checks publishing rules to prevent saturation.
    """
    
    def __init__(self):
        self.config = get_config()
        self.repo = get_repository()
    
    def can_publish_now(self, score: int = 0, sport: Optional[str] = None) -> tuple[bool, str]:
        """
        Check if publishing is allowed right now.
        
        Args:
            score: Article score (for off-hours exception)
            sport: Sport type (for cooldown check)
            
        Returns:
            Tuple of (can_publish, reason)
        """
        # Check daily limit
        can_daily, reason = self.check_daily_limit()
        if not can_daily:
            return False, reason
        
        # Check hourly limit
        can_hourly, reason = self.check_hourly_limit()
        if not can_hourly:
            return False, reason
        
        # Check active window (with exception for high-score)
        can_window, reason = self.check_active_window(score)
        if not can_window:
            return False, reason
        
        # Check sport cooldown
        if sport:
            can_cooldown, reason = self.check_sport_cooldown(sport)
            if not can_cooldown:
                return False, reason
        
        return True, "ok"
    
    def check_daily_limit(self) -> tuple[bool, str]:
        """
        Check if daily post limit has been reached.
        
        Returns:
            Tuple of (can_publish, reason)
        """
        posts_today = self.repo.count_posts_today(self.config.tz)
        
        if posts_today >= self.config.max_posts_per_day:
            logger.warning(
                f"Daily limit reached: {posts_today}/{self.config.max_posts_per_day}"
            )
            return False, f"daily_limit_reached ({posts_today}/{self.config.max_posts_per_day})"
        
        return True, "ok"
    
    def check_hourly_limit(self) -> tuple[bool, str]:
        """
        Check if hourly post limit has been reached.
        
        Returns:
            Tuple of (can_publish, reason)
        """
        posts_hour = self.repo.count_posts_last_hour()
        
        if posts_hour >= self.config.max_posts_per_hour:
            logger.warning(
                f"Hourly limit reached: {posts_hour}/{self.config.max_posts_per_hour}"
            )
            return False, f"hourly_limit_reached ({posts_hour}/{self.config.max_posts_per_hour})"
        
        return True, "ok"
    
    def check_active_window(self, score: int = 0) -> tuple[bool, str]:
        """
        Check if current time is within active window.
        High-score articles can bypass this.
        
        Args:
            score: Article score
            
        Returns:
            Tuple of (can_publish, reason)
        """
        is_active = is_within_active_window(
            self.config.active_window_start,
            self.config.active_window_end,
            self.config.tz
        )
        
        if is_active:
            return True, "ok"
        
        # Check high-score exception
        if score >= self.config.offhours_min_score:
            logger.info(
                f"Off-hours publish allowed due to high score: {score}"
            )
            return True, "offhours_high_score"
        
        current = now_in_tz(self.config.tz)
        logger.debug(
            f"Outside active window: {current.strftime('%H:%M')} "
            f"(window: {self.config.active_window_start}-{self.config.active_window_end})"
        )
        return False, "outside_active_window"
    
    def check_sport_cooldown(self, sport: str) -> tuple[bool, str]:
        """
        Check if sport-specific cooldown has passed.
        
        Args:
            sport: Sport type
            
        Returns:
            Tuple of (can_publish, reason)
        """
        cooldown_minutes = self.config.cooldown_minutes_by_sport.get(sport, 15)
        
        last_post_time = self.repo.last_post_time_by_sport(sport)
        
        if last_post_time is None:
            return True, "ok"
        
        elapsed = minutes_since(last_post_time)
        
        if elapsed < cooldown_minutes:
            remaining = cooldown_minutes - elapsed
            logger.debug(
                f"Sport cooldown active for {sport}: {remaining}min remaining"
            )
            return False, f"sport_cooldown ({sport}, {remaining}min remaining)"
        
        return True, "ok"
    
    def get_remaining_daily_posts(self) -> int:
        """Get number of posts remaining for today."""
        posts_today = self.repo.count_posts_today(self.config.tz)
        return max(0, self.config.max_posts_per_day - posts_today)
    
    def get_remaining_hourly_posts(self) -> int:
        """Get number of posts remaining for this hour."""
        posts_hour = self.repo.count_posts_last_hour()
        return max(0, self.config.max_posts_per_hour - posts_hour)
    
    def should_create_digest(self, sport: str) -> tuple[bool, list]:
        """
        Check if a digest should be created for a sport.
        
        Conditions:
        - More than DIGEST_TRIGGER_COUNT articles
        - Within DIGEST_WINDOW_MINUTES
        - Score between DIGEST_SCORE_MIN and DIGEST_SCORE_MAX
        
        Args:
            sport: Sport type
            
        Returns:
            Tuple of (should_digest, candidate_articles)
        """
        candidates = self.repo.get_digest_candidates(
            sport=sport,
            window_minutes=self.config.digest_window_minutes,
            score_min=self.config.digest_score_min,
            score_max=self.config.digest_score_max
        )
        
        if len(candidates) > self.config.digest_trigger_count:
            logger.info(
                f"Digest trigger for {sport}: {len(candidates)} candidates"
            )
            return True, candidates[:self.config.digest_max_items]
        
        return False, []


def get_rules_checker() -> RulesChecker:
    """Get a RulesChecker instance."""
    return RulesChecker()
