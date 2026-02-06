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


def run_collection_cycle(config, repo, logger) -> int:
    """
    Run a collection cycle: fetch RSS, process, and save candidates to DB.
    Does NOT publish anything.

    Returns:
        Number of unique items saved
    """
    try:
        # 1. Collect from all RSS sources
        logger.info("📡 Collecting from RSS feeds...")

        db_sources = repo.get_sources(active_only=True)

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

        normalized = normalize_all(raw_items)
        unique = dedupe_all(normalized)

        if not unique:
            logger.info("All items were duplicates")
            return 0

        classified = classify_all(unique)
        ranked = rank_all(classified)

        logger.info(f"📊 {len(ranked)} unique items after processing")

        # 3. Save candidates to DB (no publishing)
        planner = get_planner()
        planner.save_candidates(ranked)

        return len(ranked)

    except Exception as e:
        logger.error(f"Error in collection cycle: {e}", exc_info=True)
        return 0


def is_scheduled_publish_time(config, published_slots: set, logger) -> bool:
    """
    Check if now is within a scheduled publish window.
    Uses a 5-minute window after each scheduled time.

    Args:
        config: App config
        published_slots: Set of time slots already published today ("HH:MM")
        logger: Logger instance

    Returns:
        True if it's time to publish
    """
    from utils.timeutils import now_in_tz, parse_time_string

    current = now_in_tz(config.tz)
    current_minutes = current.hour * 60 + current.minute

    for slot_time in config.scheduled_post_times:
        if slot_time in published_slots:
            continue

        slot_hour, slot_min = parse_time_string(slot_time)
        slot_minutes = slot_hour * 60 + slot_min

        # Allow publishing within 5 minutes after the scheduled time
        if 0 <= (current_minutes - slot_minutes) < 5:
            logger.info(f"📅 Scheduled publish time: {slot_time}")
            return True

    return False


def get_current_slot(config) -> str:
    """Get the current matching time slot string, or empty string."""
    from utils.timeutils import now_in_tz, parse_time_string

    current = now_in_tz(config.tz)
    current_minutes = current.hour * 60 + current.minute

    for slot_time in config.scheduled_post_times:
        slot_hour, slot_min = parse_time_string(slot_time)
        slot_minutes = slot_hour * 60 + slot_min

        if 0 <= (current_minutes - slot_minutes) < 5:
            return slot_time

    return ""


def run_scheduled_publish(config, repo, logger) -> int:
    """
    Publish the best unposted transfer/rumor article from the DB.
    If no transfer news is available, publish a football meme instead.

    Returns:
        Number of items published (0 or 1)
    """
    try:
        # Get unposted candidates
        candidates = repo.get_unposted_candidates(min_score=20, limit=50)

        # Filter to only transfer/rumor categories
        transfer_candidates = [
            c for c in candidates
            if c.get('category') in ('transfer', 'rumor', 'breaking')
        ]

        if transfer_candidates:
            best = transfer_candidates[0]
            return _publish_candidate(best, repo, config, logger)
        else:
            # No transfer news -> publish a meme
            logger.info("🤷 No transfer/rumor news available - posting meme")
            return _publish_meme(repo, config, logger)

    except Exception as e:
        logger.error(f"Error in scheduled publish: {e}", exc_info=True)
        return 0


def _publish_candidate(best: dict, repo, config, logger) -> int:
    """Publish a single article candidate from DB dict."""
    from processor.normalize import NormalizedItem
    from utils.timeutils import iso_to_datetime

    pub_at = best.get('published_at')
    if pub_at and isinstance(pub_at, str):
        try:
            pub_at = iso_to_datetime(pub_at)
        except Exception:
            pub_at = None

    item = NormalizedItem(
        title=best.get('title', ''),
        normalized_title=best.get('normalized_title', ''),
        link=best.get('link', ''),
        canonical_url=best.get('canonical_url', ''),
        summary=best.get('summary', ''),
        published_at=pub_at,
        content_hash=best.get('content_hash', ''),
        image_url=best.get('image_url', ''),
        source_name=best.get('source_name', ''),
        source_domain=best.get('source_domain', ''),
        source_weight=0
    )
    item.sport = best.get('sport', 'football_eu')
    item.category = best.get('category', 'default')
    item.status = best.get('status', '')
    item.score = best.get('score', 0)
    item.article_id = best.get('id', 0)

    logger.info(
        f"📋 Publishing top article (score={item.score}, cat={item.category}): "
        f"{item.title[:60]}..."
    )

    if process_single_article(item, repo, config, logger):
        return 1
    return 0


def _publish_meme(repo, config, logger) -> int:
    """Publish a random football meme."""
    import random

    memes = get_football_memes()
    meme = random.choice(memes)

    try:
        # Create meme image
        meme_image = create_meme_image(meme["text"], meme.get("subtext", ""))

        if not meme_image:
            logger.error("Failed to create meme image")
            return 0

        # Process with watermark
        processed = process_image_with_watermark(meme_image)
        if not processed:
            processed = meme_image

        # Caption
        caption = f"😂 <b>{meme['text']}</b>"
        if meme.get("subtext"):
            caption += f"\n\n{meme['subtext']}"
        caption += "\n\n#FutbolMemes #GoalFeed"

        message_id = publish_article(
            image_data=processed,
            caption=caption,
            source_url="",
            source_name="GoalFeed Memes"
        )

        if message_id:
            logger.info(f"✅ Published meme: {meme['text'][:50]}...")
            return 1
        return 0

    except Exception as e:
        logger.error(f"Error publishing meme: {e}")
        return 0


def get_football_memes() -> list:
    """Return a list of football meme texts."""
    return [
        {
            "text": "Cuando tu equipo ficha a un crack y al dia siguiente se lesiona",
            "subtext": "El futbol no perdona 😭"
        },
        {
            "text": "El fichaje estrella del verano viendo el banquillo desde dentro",
            "subtext": "No era lo que le prometieron 🪑"
        },
        {
            "text": "Agente libre a los 35 anos: 'Aun tengo nivel de Champions'",
            "subtext": "Narrator: No lo tenia 📉"
        },
        {
            "text": "El presidente del club: 'No hay dinero para fichajes'",
            "subtext": "Tambien el presidente: *se compra un yate* 🛥️"
        },
        {
            "text": "Yo explicando a mi novia por que un fichaje de 100M es una ganga",
            "subtext": "Es que viene con la clausula de reventa... 📊"
        },
        {
            "text": "El futbolista: 'Quiero quedarme aqui toda mi vida'",
            "subtext": "3 meses despues: *se va al rival* 🏃💨"
        },
        {
            "text": "Cuando dicen 'fichaje inminente' y pasan 47 dias",
            "subtext": "A cualquier hora se cierra... ⏳"
        },
        {
            "text": "El Madrid y el Barca peleando por el mismo fichaje",
            "subtext": "Y al final se lo lleva el Newcastle 🤑"
        },
        {
            "text": "Deadline Day: 23:58 y tu equipo aun no ha fichado a nadie",
            "subtext": "Este ano seguro que reforzamos en enero... 🤡"
        },
        {
            "text": "Yo F5-eando Transfermarkt cada 30 segundos",
            "subtext": "Seguro que ahora si hay novedades 🔄"
        },
        {
            "text": "El jugador que pide irse y luego dice 'siempre quise quedarme'",
            "subtext": "Cuando no le salen las ofertas que esperaba 🎭"
        },
        {
            "text": "Periodistas deportivos en verano: 'BOMBAZO INMINENTE'",
            "subtext": "El bombazo: un lateral del Getafe al Valladolid 💣"
        },
        {
            "text": "Mi equipo gastando 200M: Octavos de Champions y fuera",
            "subtext": "El Girona con su plantilla low cost: semifinalista 🏆"
        },
        {
            "text": "El futbolista en Instagram: 'Feliz en mi club' ❤️",
            "subtext": "Su agente en la misma hora: *llama a 15 equipos* 📞"
        },
        {
            "text": "Cuando el rumor dice 'fuentes cercanas al club'",
            "subtext": "Las fuentes: el tio que vende cafe fuera del estadio ☕"
        },
        {
            "text": "POV: Tu portero estrella se va gratis al rival",
            "subtext": "Y encima les para todo en el clasico 😤"
        },
        {
            "text": "El jugador con 2 goles en 30 partidos: 'Merezco mas minutos'",
            "subtext": "El entrenador: 🤨"
        },
        {
            "text": "Enero: 'No vamos a fichar, confiamos en la plantilla'",
            "subtext": "La plantilla: 5 lesionados y 2 sancionados 🏥"
        },
        {
            "text": "Las presentaciones de fichajes: traje, estadio lleno, fuegos artificiales",
            "subtext": "6 meses despues: cedido al Leganes 📦"
        },
        {
            "text": "El VAR cuando es a favor de tu equipo: Gran tecnologia 👏",
            "subtext": "El VAR en contra: Esto es un robo, futbol de antes! 😡"
        },
    ]


def create_meme_image(text: str, subtext: str = "") -> bytes:
    """Create a meme-style image with text."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO
        import os

        width, height = 1280, 720
        img = Image.new('RGB', (width, height), (15, 15, 25))
        draw = ImageDraw.Draw(img)

        # Dark gradient background with football feel
        for y in range(height):
            ratio = y / height
            r = int(15 + 10 * ratio)
            g = int(40 - 20 * ratio)
            b = int(25 + 10 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Accent lines
        draw.rectangle([(0, 0), (width, 4)], fill=(46, 204, 113))
        draw.rectangle([(0, height - 4), (width, height)], fill=(46, 204, 113))

        # Try to load a good font
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSDisplay.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]

        font_large = None
        font_small = None
        for path in font_paths:
            if os.path.exists(path):
                try:
                    font_large = ImageFont.truetype(path, 42)
                    font_small = ImageFont.truetype(path, 30)
                    break
                except Exception:
                    continue

        if not font_large:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Word wrap the main text
        def wrap_text(text, font, max_width):
            words = text.split()
            lines = []
            current_line = ""
            for word in words:
                test = f"{current_line} {word}".strip()
                bbox = draw.textbbox((0, 0), test, font=font)
                if bbox[2] - bbox[0] <= max_width:
                    current_line = test
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            return lines

        max_text_width = width - 120
        main_lines = wrap_text(text, font_large, max_text_width)

        # Calculate vertical position
        line_height_main = 55
        line_height_sub = 45
        total_height = len(main_lines) * line_height_main
        if subtext:
            sub_lines = wrap_text(subtext, font_small, max_text_width)
            total_height += 30 + len(sub_lines) * line_height_sub
        else:
            sub_lines = []

        start_y = (height - total_height) // 2

        # Draw main text (white with shadow)
        y = start_y
        for line in main_lines:
            bbox = draw.textbbox((0, 0), line, font=font_large)
            tw = bbox[2] - bbox[0]
            x = (width - tw) // 2
            # Shadow
            draw.text((x + 2, y + 2), line, fill=(0, 0, 0), font=font_large)
            draw.text((x, y), line, fill=(255, 255, 255), font=font_large)
            y += line_height_main

        # Draw subtext (green/gray)
        if sub_lines:
            y += 20
            for line in sub_lines:
                bbox = draw.textbbox((0, 0), line, font=font_small)
                tw = bbox[2] - bbox[0]
                x = (width - tw) // 2
                draw.text((x + 1, y + 1), line, fill=(0, 0, 0), font=font_small)
                draw.text((x, y), line, fill=(46, 204, 113), font=font_small)
                y += line_height_sub

        # Save to bytes
        buf = BytesIO()
        img.save(buf, 'JPEG', quality=90)
        return buf.getvalue()

    except Exception as e:
        logging.getLogger('goalfeed').error(f"Error creating meme image: {e}")
        return None


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
    logger.info(f"📊 Scheduled posts: {config.max_posts_per_day}/day at {', '.join(config.scheduled_post_times)}")
    logger.info(f"🕐 Timezone: {config.tz}")
    
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
    published_slots = set()  # Track which time slots have been published today
    last_date = None  # Track date for resetting slots

    while not shutdown_requested:
        cycle_count += 1
        current_time = time.time()

        # Reset published slots at midnight
        from utils.timeutils import now_in_tz
        current_dt = now_in_tz(config.tz)
        current_date = current_dt.date()
        if last_date is not None and current_date != last_date:
            published_slots.clear()
            logger.info("🔄 New day - reset scheduled slots")
        last_date = current_date

        try:
            # Run RSS collection if interval elapsed
            if current_time - last_rss_cycle >= config.poll_interval_seconds:
                logger.info(f"\n🔄 Collection Cycle {cycle_count} starting...")

                collected = run_collection_cycle(config, repo, logger)
                last_rss_cycle = current_time

                if collected > 0:
                    logger.info(f"💾 Saved {collected} candidates to DB")

            # Check if it's a scheduled publish time
            if is_scheduled_publish_time(config, published_slots, logger):
                slot = get_current_slot(config)
                published = run_scheduled_publish(config, repo, logger)
                total_published += published

                if published > 0:
                    logger.info(f"📤 Published 1 article for slot {slot}")
                    published_slots.add(slot)
                else:
                    logger.info(f"⏭️  No article published for slot {slot} (no candidates)")
                    published_slots.add(slot)  # Mark slot as consumed anyway

            # Run Live cycle if interval elapsed and API key is configured
            if config.live.api_key:
                if current_time - last_live_cycle >= config.live.poll_seconds:
                    live_published = run_live_cycle(config, repo, logger)
                    total_live_published += live_published
                    last_live_cycle = current_time

                    if live_published > 0:
                        logger.info(f"🔴 Published {live_published} live event(s)")

            # Log stats only on collection cycles (not every minute)
            if current_time - last_rss_cycle < 5:  # Just ran collection
                stats = repo.get_daily_stats()
                if stats:
                    live_events_today = repo.count_live_events_today()
                    remaining_slots = [
                        s for s in config.scheduled_post_times
                        if s not in published_slots
                    ]
                    logger.info(
                        f"📈 Today: {stats.get('post_count', 0)} posts, "
                        f"{live_events_today} live, "
                        f"{stats.get('articles_fetched', 0)} fetched | "
                        f"Remaining slots: {remaining_slots if remaining_slots else 'none'}"
                    )

        except Exception as e:
            logger.error(f"❌ Cycle error: {e}", exc_info=True)

        # Sleep - poll every 60s to catch scheduled times accurately
        if not shutdown_requested:
            sleep_interval = 60

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
