#!/usr/bin/env python3
"""
GoalFeed - Telegram Sports News Auto-Publisher Bot

Main entry point and scheduler loop.
"""
import os
import sys
import time
import signal
import logging
from typing import Optional, List
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from config import get_config, RSSSource
from db import init_db, get_repository
from collector import collect_all, get_best_image
from processor import normalize_all, classify_all, rank_all, dedupe_all
from scheduler import get_planner, PostType
from editorial import generate_caption, generate_digest_caption
from media import download_image, process_image_with_watermark, create_placeholder_image
from publisher import publish_article, publish_digest
from live import LiveCollector, LiveRules, publish_live_event


# Setup logging
def setup_logging():
    """Configure logging for the application."""
    config = get_config()
    
    # Create logs directory
    log_dir = os.path.dirname(config.log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    # Create formatters
    console_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_format)
    
    # File handler
    file_handler = logging.FileHandler(config.log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Log everything to file
    file_handler.setFormatter(file_format)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Reduce noise from libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    return logging.getLogger('goalfeed')


# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global shutdown_requested
    shutdown_requested = True
    logging.getLogger('goalfeed').info("Shutdown requested...")


def seed_sources_if_needed(repo, config):
    """Seed RSS sources to database if not present, or re-seed if count changed."""
    logger = logging.getLogger('goalfeed')

    existing = repo.get_sources()
    config_count = len(config.rss_sources)

    if existing and len(existing) == config_count:
        logger.info(f"Found {len(existing)} existing sources (matches config)")
        return

    if existing and len(existing) != config_count:
        logger.info(
            f"Source count mismatch: DB={len(existing)}, config={config_count}. "
            f"Re-seeding sources..."
        )

    # Seed from config
    sources_data = [
        {
            'name': s.name,
            'url': s.url,
            'sport_hint': s.sport_hint,
            'weight': s.weight
        }
        for s in config.rss_sources
    ]

    repo.seed_sources(sources_data)
    logger.info(f"Seeded {len(sources_data)} RSS sources")


def get_fallback_image(sport: str = "football_eu") -> bytes:
    """Get fallback image for football, creating placeholder if needed."""
    config = get_config()
    fallback_path = config.fallback_images.get("football_eu", config.fallback_images["default"])

    # Build absolute path
    if not os.path.isabs(fallback_path):
        fallback_path = os.path.join(PROJECT_ROOT, fallback_path)

    # Try to load fallback
    if os.path.exists(fallback_path):
        with open(fallback_path, 'rb') as f:
            return f.read()

    # Create placeholder if fallback doesn't exist
    logging.getLogger('goalfeed').warning(
        f"Fallback image not found: {fallback_path}, using placeholder"
    )
    return create_placeholder_image(text="GoalFeed | Futbol")


def process_single_article(item, repo, config, logger) -> bool:
    """
    Process and publish a single article.
    
    Returns:
        True if published successfully
    """
    try:
        # Get image
        fallback_path = config.fallback_images.get(
            item.sport, 
            config.fallback_images['default']
        )
        
        image_url = get_best_image(
            item.image_url,
            item.link,
            fallback_path
        )
        
        # Download/load image
        if image_url.startswith(('http://', 'https://')):
            image_data = download_image(image_url)
            if not image_data:
                image_data = get_fallback_image(item.sport)
        else:
            # Local fallback
            image_data = get_fallback_image(item.sport)
        
        # Process image (resize + watermark)
        processed_image = process_image_with_watermark(image_data)
        
        if not processed_image:
            logger.error(f"Failed to process image for: {item.title[:50]}")
            return False
        
        # Generate caption
        caption = generate_caption(item)
        
        # Publish
        message_id = publish_article(
            image_data=processed_image,
            caption=caption,
            source_url=item.link,
            source_name=item.source_name
        )
        
        if message_id:
            # Record post
            article_id = getattr(item, 'article_id', None)
            if article_id:
                repo.record_post(
                    article_id=article_id,
                    telegram_message_id=message_id,
                    telegram_chat_id=config.channel_chat_id,
                    caption=caption,
                    sport=item.sport,
                    post_type='single'
                )
            
            logger.info(f"✅ Published: {item.title[:60]}...")
            return True
        else:
            logger.error(f"Failed to publish: {item.title[:50]}")
            return False
            
    except Exception as e:
        logger.error(f"Error processing article: {e}")
        return False


def process_digest(items, sport, repo, config, logger) -> bool:
    """
    Process and publish a digest.
    
    Returns:
        True if published successfully
    """
    try:
        # Get fallback image for sport
        image_data = get_fallback_image(sport)
        
        # Process image
        processed_image = process_image_with_watermark(image_data)
        
        if not processed_image:
            logger.error(f"Failed to process digest image for: {sport}")
            return False
        
        # Generate digest caption
        caption = generate_digest_caption(items, sport)
        
        # Prepare sources for buttons
        sources = [(item.link, item.source_name) for item in items]
        
        # Publish
        message_id = publish_digest(
            image_data=processed_image,
            caption=caption,
            sources=sources
        )
        
        if message_id:
            # Record digest
            article_ids = [
                getattr(item, 'article_id', 0) 
                for item in items 
                if hasattr(item, 'article_id')
            ]
            
            if article_ids:
                repo.record_digest(
                    article_ids=article_ids,
                    telegram_message_id=message_id,
                    telegram_chat_id=config.channel_chat_id,
                    caption=caption,
                    sport=sport
                )
            
            logger.info(f"✅ Published digest: {sport} ({len(items)} items)")
            return True
        else:
            logger.error(f"Failed to publish digest for: {sport}")
            return False
            
    except Exception as e:
        logger.error(f"Error processing digest: {e}")
        return False


def run_cycle(config, repo, logger) -> int:
    """
    Run a single collection and publishing cycle (RSS news).
    
    Returns:
        Number of items published
    """
    published_count = 0
    
    try:
        # 1. Collect from all RSS sources
        logger.info("📡 Collecting from RSS feeds...")
        
        # Get sources from DB (they were seeded on init)
        db_sources = repo.get_sources(active_only=True)
        
        # Convert to RSSSource objects
        sources = [
            RSSSource(
                name=s['name'],
                url=s['url'],
                sport_hint=s['sport_hint'],
                weight=s['weight']
            )
            for s in db_sources
        ]
        
        raw_items = collect_all(sources)
        
        if not raw_items:
            logger.info("No items collected this cycle")
            return 0
        
        # 2. Process items through pipeline
        logger.info(f"🔄 Processing {len(raw_items)} items...")
        
        # Normalize
        normalized = normalize_all(raw_items)
        
        # Deduplicate
        unique = dedupe_all(normalized)
        
        if not unique:
            logger.info("All items were duplicates")
            return 0
        
        # Classify
        classified = classify_all(unique)
        
        # Rank
        ranked = rank_all(classified)
        
        logger.info(f"📊 {len(ranked)} unique items after processing")
        
        # 3. Plan publications
        planner = get_planner()
        plans = planner.plan_publications(ranked)
        
        if not plans:
            logger.info("No items eligible for publication this cycle")
            return 0
        
        logger.info(f"📋 {len(plans)} publication(s) planned")
        
        # 4. Execute publications
        for plan in plans:
            if shutdown_requested:
                logger.info("Shutdown requested, stopping publications")
                break
            
            if plan.post_type == PostType.DIGEST:
                if process_digest(plan.items, plan.sport, repo, config, logger):
                    published_count += 1
            else:
                if plan.items:
                    if process_single_article(plan.items[0], repo, config, logger):
                        published_count += 1
            
            # Small delay between posts
            if len(plans) > 1:
                time.sleep(2)
        
        return published_count
        
    except Exception as e:
        logger.error(f"Error in cycle: {e}", exc_info=True)
        return 0


def run_live_cycle(config, repo, logger) -> int:
    """
    Run a single live match tracking cycle.
    
    Returns:
        Number of events published
    """
    published_count = 0
    
    # Check if live tracking is enabled
    if not config.live.api_key:
        logger.debug("Live tracking disabled (no API key)")
        return 0
    
    try:
        logger.info("🔴 Checking live matches...")
        
        # Initialize collectors and rules
        collector = LiveCollector()
        rules = LiveRules()
        
        # Get live data and detect new events
        raw_events = collector.get_live_data(repo)
        
        if not raw_events:
            logger.info("No live events detected")
            return 0
        
        logger.info(f"🔔 Detected {len(raw_events)} potential live events")
        
        # Filter events based on rules
        publishable_events = rules.filter_publishable_events(raw_events, repo)
        
        if not publishable_events:
            logger.info("No events eligible for publication")
            return 0
        
        # Prioritize events
        prioritized_events = rules.prioritize_events(publishable_events)
        
        logger.info(f"📋 {len(prioritized_events)} live events to publish")
        
        # Publish each event
        for match, event in prioritized_events:
            if shutdown_requested:
                logger.info("Shutdown requested, stopping live publications")
                break
            
            message_id = publish_live_event(match, event, repo)
            
            if message_id:
                published_count += 1
                logger.info(
                    f"✅ Published live event: {event.event_type.value} - "
                    f"{match.home_team} vs {match.away_team}"
                )
            
            # Small delay between live posts
            if len(prioritized_events) > 1:
                time.sleep(1)
        
        return published_count
        
    except Exception as e:
        logger.error(f"Error in live cycle: {e}", exc_info=True)
        return 0


def main():
    """Main entry point."""
    global shutdown_requested
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Setup logging
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("⚽ GoalFeed - Football News & Rumors")
    logger.info("🚀 Starting...")
    logger.info("=" * 60)
    
    # Load config
    config = get_config()
    
    # Validate config
    if not config.bot_token:
        logger.error("❌ BOT_TOKEN not configured!")
        logger.error("Please set BOT_TOKEN environment variable")
        sys.exit(1)
    
    if not config.channel_chat_id:
        logger.error("❌ CHANNEL_CHAT_ID not configured!")
        logger.error("Please set CHANNEL_CHAT_ID environment variable")
        sys.exit(1)
    
    logger.info(f"📺 Channel: {config.channel_chat_id}")
    logger.info(f"⏱️  Poll interval: {config.poll_interval_seconds}s")
    logger.info(f"📊 Max posts: {config.max_posts_per_day}/day, {config.max_posts_per_hour}/hour")
    logger.info(f"🕐 Active window: {config.active_window_start} - {config.active_window_end} ({config.tz})")
    
    # Live tracking info
    if config.live.api_key:
        logger.info(f"🔴 Live tracking: ENABLED (poll every {config.live.poll_seconds}s)")
        logger.info(f"⚽ Tracked leagues: {list(config.live.tracked_leagues.values())}")
    else:
        logger.info("🔴 Live tracking: DISABLED (no FOOTBALL_API_KEY)")
    
    # Initialize database
    logger.info("💾 Initializing database...")
    try:
        init_db()
        repo = get_repository()
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)
    
    # Seed sources
    seed_sources_if_needed(repo, config)
    
    logger.info("✅ Initialization complete")
    logger.info("-" * 60)
    
    # Main loop
    cycle_count = 0
    total_published = 0
    total_live_published = 0
    last_rss_cycle = 0
    last_live_cycle = 0
    
    while not shutdown_requested:
        cycle_count += 1
        current_time = time.time()
        
        try:
            # Run RSS cycle if interval elapsed
            if current_time - last_rss_cycle >= config.poll_interval_seconds:
                logger.info(f"\n🔄 RSS Cycle {cycle_count} starting...")
                
                published = run_cycle(config, repo, logger)
                total_published += published
                last_rss_cycle = current_time
                
                if published > 0:
                    logger.info(f"📤 Published {published} news item(s)")
            
            # Run Live cycle if interval elapsed and API key is configured
            if config.live.api_key:
                if current_time - last_live_cycle >= config.live.poll_seconds:
                    live_published = run_live_cycle(config, repo, logger)
                    total_live_published += live_published
                    last_live_cycle = current_time
                    
                    if live_published > 0:
                        logger.info(f"🔴 Published {live_published} live event(s)")
            
            # Get stats
            stats = repo.get_daily_stats()
            if stats:
                live_events_today = repo.count_live_events_today()
                logger.info(
                    f"📈 Today's stats: {stats.get('post_count', 0)} posts, "
                    f"{stats.get('digest_count', 0)} digests, "
                    f"{live_events_today} live events, "
                    f"{stats.get('articles_fetched', 0)} fetched"
                )
            
        except Exception as e:
            logger.error(f"❌ Cycle error: {e}", exc_info=True)
        
        # Calculate sleep time (use shorter interval for live tracking)
        if not shutdown_requested:
            if config.live.api_key:
                # Use the shorter live poll interval
                sleep_interval = min(config.live.poll_seconds, config.poll_interval_seconds)
            else:
                sleep_interval = config.poll_interval_seconds
            
            logger.info(f"😴 Sleeping for {sleep_interval}s...")
            
            # Sleep in small increments to check shutdown flag
            sleep_remaining = sleep_interval
            while sleep_remaining > 0 and not shutdown_requested:
                sleep_time = min(10, sleep_remaining)
                time.sleep(sleep_time)
                sleep_remaining -= sleep_time
    
    # Shutdown
    logger.info("-" * 60)
    logger.info(f"📊 Total published this session: {total_published} news, {total_live_published} live events")
    logger.info("👋 GoalFeed Bot shutting down...")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
