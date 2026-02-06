-- GoalFeed Database Schema
-- SQLite database for tracking articles, posts, and sources

-- RSS Sources table
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    sport_hint TEXT NOT NULL,
    weight INTEGER DEFAULT 10,
    active INTEGER DEFAULT 1,
    last_fetched_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Articles table (all fetched articles)
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    
    -- Original data
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    link TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    summary TEXT,
    published_at TEXT,
    
    -- Classification
    sport TEXT NOT NULL,
    category TEXT,
    status TEXT DEFAULT 'RUMOR',  -- CONFIRMADO, RUMOR, EN_DESARROLLO
    
    -- Scoring
    score INTEGER DEFAULT 0,
    
    -- Deduplication
    content_hash TEXT NOT NULL,
    
    -- Media
    image_url TEXT,
    
    -- Metadata
    source_name TEXT,
    source_domain TEXT,
    
    -- Tracking
    is_duplicate INTEGER DEFAULT 0,
    is_posted INTEGER DEFAULT 0,
    is_digested INTEGER DEFAULT 0,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

-- Create indexes for articles
CREATE INDEX IF NOT EXISTS idx_articles_canonical_url ON articles(canonical_url);
CREATE INDEX IF NOT EXISTS idx_articles_content_hash ON articles(content_hash);
CREATE INDEX IF NOT EXISTS idx_articles_sport ON articles(sport);
CREATE INDEX IF NOT EXISTS idx_articles_score ON articles(score DESC);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at);
CREATE INDEX IF NOT EXISTS idx_articles_is_posted ON articles(is_posted);
CREATE INDEX IF NOT EXISTS idx_articles_is_duplicate ON articles(is_duplicate);

-- Posts table (published to Telegram)
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER,
    
    -- Telegram data
    telegram_message_id INTEGER,
    telegram_chat_id TEXT,
    
    -- Content
    caption TEXT,
    image_path TEXT,
    
    -- Metadata
    sport TEXT,
    post_type TEXT DEFAULT 'single',  -- single, digest
    
    -- Timing
    posted_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

-- Create indexes for posts
CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts(posted_at);
CREATE INDEX IF NOT EXISTS idx_posts_sport ON posts(sport);
CREATE INDEX IF NOT EXISTS idx_posts_post_type ON posts(post_type);

-- Digests table (grouped posts)
CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Telegram data
    telegram_message_id INTEGER,
    telegram_chat_id TEXT,
    
    -- Content
    caption TEXT,
    image_path TEXT,
    
    -- Metadata
    sport TEXT NOT NULL,
    article_count INTEGER DEFAULT 0,
    
    -- Timing
    posted_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Digest items (articles in a digest)
CREATE TABLE IF NOT EXISTS digest_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    digest_id INTEGER NOT NULL,
    article_id INTEGER NOT NULL,
    position INTEGER DEFAULT 0,
    
    FOREIGN KEY (digest_id) REFERENCES digests(id),
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

CREATE INDEX IF NOT EXISTS idx_digest_items_digest_id ON digest_items(digest_id);

-- Settings table (optional, for runtime config)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Daily stats table (for tracking limits)
CREATE TABLE IF NOT EXISTS daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    post_count INTEGER DEFAULT 0,
    digest_count INTEGER DEFAULT 0,
    articles_fetched INTEGER DEFAULT 0,
    articles_duplicated INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date);

-- Live events table (for tracking live match events)
CREATE TABLE IF NOT EXISTS live_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Match identification
    match_id TEXT NOT NULL,  -- External API match ID
    league_id INTEGER,
    league_name TEXT,
    
    -- Teams
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    
    -- Score at event time
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    
    -- Event details
    event_type TEXT NOT NULL,  -- goal, red_card, final, penalty_miss, var
    event_minute INTEGER,
    event_player TEXT,
    event_detail TEXT,  -- Additional info (assist, penalty, own goal, etc.)
    
    -- Telegram data
    telegram_message_id INTEGER,
    telegram_chat_id TEXT,
    
    -- Tracking
    is_published INTEGER DEFAULT 0,
    published_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint to prevent duplicate events
    UNIQUE(match_id, event_type, event_minute, event_player)
);

-- Create indexes for live_events
CREATE INDEX IF NOT EXISTS idx_live_events_match_id ON live_events(match_id);
CREATE INDEX IF NOT EXISTS idx_live_events_event_type ON live_events(event_type);
CREATE INDEX IF NOT EXISTS idx_live_events_created_at ON live_events(created_at);
CREATE INDEX IF NOT EXISTS idx_live_events_is_published ON live_events(is_published);

-- Live matches table (for tracking active matches)
CREATE TABLE IF NOT EXISTS live_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Match identification
    match_id TEXT NOT NULL UNIQUE,
    league_id INTEGER,
    league_name TEXT,
    
    -- Teams
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    
    -- Current state
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    match_status TEXT,  -- NS, 1H, HT, 2H, FT, etc.
    current_minute INTEGER,
    
    -- Tracking
    events_published INTEGER DEFAULT 0,
    last_event_at TEXT,
    is_top_team_match INTEGER DEFAULT 0,
    
    -- Timestamps
    match_start TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_live_matches_match_id ON live_matches(match_id);
CREATE INDEX IF NOT EXISTS idx_live_matches_match_status ON live_matches(match_status);

-- Insert default settings
INSERT OR IGNORE INTO settings (key, value) VALUES ('initialized', 'true');
INSERT OR IGNORE INTO settings (key, value) VALUES ('version', '1.1.0');
