"""
Publishing planner for GoalFeed.
Decides what to publish and when.
"""
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from config import get_config
from processor.normalize import NormalizedItem
from scheduler.rules import get_rules_checker
from db.repo import get_repository, ArticleRecord

logger = logging.getLogger(__name__)


class PostType(Enum):
    """Type of post to publish."""
    SINGLE = "single"
    DIGEST = "digest"


@dataclass
class PublishPlan:
    """Plan for a single publish action."""
    post_type: PostType
    items: List[NormalizedItem] = field(default_factory=list)
    article_ids: List[int] = field(default_factory=list)
    sport: str = "football_eu"
    priority: int = 0
    reason: str = ""


class Planner:
    """
    Plans what articles to publish based on rules and scores.
    """
    
    def __init__(self):
        self.config = get_config()
        self.rules = get_rules_checker()
        self.repo = get_repository()
    
    def save_candidates(self, items: List[NormalizedItem]) -> List[int]:
        """
        Save candidate articles to database.
        
        Args:
            items: List of NormalizedItem to save
            
        Returns:
            List of article IDs
        """
        article_ids = []
        
        for item in items:
            try:
                record = ArticleRecord(
                    title=item.title,
                    normalized_title=item.normalized_title,
                    link=item.link,
                    canonical_url=item.canonical_url,
                    summary=item.summary,
                    published_at=item.published_at.isoformat() if item.published_at else None,
                    sport=item.sport,
                    category=item.category,
                    status=item.status,
                    score=item.score,
                    content_hash=item.content_hash,
                    image_url=item.image_url,
                    source_name=item.source_name,
                    source_domain=item.source_domain
                )
                
                article_id = self.repo.upsert_article(record)
                article_ids.append(article_id)
                
                # Store ID in item for later use
                item.article_id = article_id
                
            except Exception as e:
                logger.error(f"Error saving article: {e}")
        
        if article_ids:
            self.repo.increment_articles_fetched(len(article_ids))
        
        return article_ids
    
    def plan_publications(self, items: List[NormalizedItem]) -> List[PublishPlan]:
        """
        Create a publication plan from candidate items.
        
        Args:
            items: List of processed NormalizedItem objects
            
        Returns:
            List of PublishPlan objects to execute
        """
        plans = []
        
        # Save all items to database first
        self.save_candidates(items)
        
        # Group items by sport
        by_sport = {}
        for item in items:
            if item.sport not in by_sport:
                by_sport[item.sport] = []
            by_sport[item.sport].append(item)
        
        # Check for digest opportunities
        for sport, sport_items in by_sport.items():
            should_digest, digest_candidates = self.rules.should_create_digest(sport)
            
            if should_digest:
                # Create digest plan
                # Convert DB rows to NormalizedItem-like objects
                digest_items = []
                for item in sport_items[:self.config.digest_max_items]:
                    if item.score >= self.config.digest_score_min and item.score <= self.config.digest_score_max:
                        digest_items.append(item)
                
                if len(digest_items) > self.config.digest_trigger_count:
                    plan = PublishPlan(
                        post_type=PostType.DIGEST,
                        items=digest_items[:self.config.digest_max_items],
                        article_ids=[getattr(i, 'article_id', 0) for i in digest_items[:self.config.digest_max_items]],
                        sport=sport,
                        priority=50,  # Medium priority for digests
                        reason="digest_aggregation"
                    )
                    plans.append(plan)
                    
                    # Remove digest items from individual consideration
                    for item in digest_items:
                        if item in sport_items:
                            sport_items.remove(item)
                    logger.info(f"Planned digest for {sport} with {len(digest_items)} items")
        
        # Plan individual high-score articles
        all_remaining = []
        for sport_items in by_sport.values():
            all_remaining.extend(sport_items)
        
        # Sort by score
        all_remaining.sort(key=lambda x: x.score, reverse=True)
        
        for item in all_remaining:
            # Check if this item passes rules
            can_publish, reason = self.rules.can_publish_now(
                score=item.score,
                sport=item.sport
            )
            
            if can_publish:
                plan = PublishPlan(
                    post_type=PostType.SINGLE,
                    items=[item],
                    article_ids=[getattr(item, 'article_id', 0)],
                    sport=item.sport,
                    priority=item.score,
                    reason="single_article"
                )
                plans.append(plan)
        
        # Sort plans by priority
        plans.sort(key=lambda x: x.priority, reverse=True)
        
        # Limit to what we can actually publish
        remaining_daily = self.rules.get_remaining_daily_posts()
        remaining_hourly = self.rules.get_remaining_hourly_posts()
        max_to_publish = min(remaining_daily, remaining_hourly)
        
        if len(plans) > max_to_publish:
            logger.info(
                f"Limiting plans from {len(plans)} to {max_to_publish} "
                f"(daily={remaining_daily}, hourly={remaining_hourly})"
            )
            plans = plans[:max_to_publish]
        
        logger.info(f"Created {len(plans)} publication plans")
        return plans
    
    def get_next_publish(self, items: List[NormalizedItem]) -> Optional[PublishPlan]:
        """
        Get the single highest-priority item to publish next.
        
        Args:
            items: List of processed NormalizedItem objects
            
        Returns:
            PublishPlan or None if nothing should be published
        """
        plans = self.plan_publications(items)
        
        if not plans:
            return None
        
        # Get highest priority plan
        next_plan = plans[0]
        
        # Verify we can still publish
        can_publish, reason = self.rules.can_publish_now(
            score=next_plan.priority,
            sport=next_plan.sport
        )
        
        if not can_publish:
            logger.info(f"Cannot publish next item: {reason}")
            return None
        
        return next_plan
    
    def get_pending_candidates(self, min_score: int = 50, limit: int = 10) -> List[dict]:
        """
        Get pending candidates from database that haven't been posted.
        
        Args:
            min_score: Minimum score threshold
            limit: Maximum candidates to return
            
        Returns:
            List of article dicts
        """
        return self.repo.get_unposted_candidates(min_score, limit)


def get_planner() -> Planner:
    """Get a Planner instance."""
    return Planner()
