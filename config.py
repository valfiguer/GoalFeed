"""
GoalFeed Configuration Module
All settings are loaded from environment variables with sensible defaults.
"""
import os
from typing import Dict, List, Set
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class WatermarkConfig:
    """Watermark configuration settings."""
    path: str = "assets/logo.png"
    size_ratio: float = 0.16  # 16% del ancho de la imagen
    margin_ratio: float = 0.04
    opacity: float = 0.65


@dataclass
class LiveConfig:
    """Live matches configuration settings."""
    poll_seconds: int = 90  # Poll interval for live matches
    max_events_per_match: int = 6  # Max events to publish per match
    event_cooldown_minutes: int = 8  # Cooldown between events of same match
    
    # API Football (RapidAPI) configuration
    api_key: str = ""  # Set via env var FOOTBALL_API_KEY
    api_host: str = "free-api-live-football-data.p.rapidapi.com"  # Free tier API
    
    # Competitions to track (API-Football IDs)
    tracked_leagues: Dict[int, str] = None
    
    # Live images by competition
    live_images: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tracked_leagues is None:
            self.tracked_leagues = {
                2: "UEFA Champions League",  # UCL
                140: "LaLiga",  # La Liga
            }
        if self.live_images is None:
            self.live_images = {
                "ucl": "assets/live_ucl.jpg",
                "champions": "assets/live_ucl.jpg",
                "laliga": "assets/live_laliga.jpg",
                "default": "assets/live_football.jpg"
            }


# Top teams to track for live matches
TOP_TEAMS = {
    # Spain
    "Real Madrid", "Barcelona", "Atlético Madrid", "Atletico Madrid",
    "Atl. Madrid", "Atlético de Madrid",
    # England
    "Manchester City", "Manchester United", "Man City", "Man United",
    "Liverpool", "Arsenal", "Chelsea", "Tottenham",
    # Germany
    "Bayern Munich", "Bayern München", "Borussia Dortmund", "Dortmund",
    # France
    "PSG", "Paris Saint-Germain", "Paris Saint Germain",
    # Italy
    "Inter", "Inter Milan", "Internazionale", "AC Milan", "Milan",
    "Juventus",
}


@dataclass
class RSSSource:
    """RSS feed source configuration."""
    name: str
    url: str
    sport_hint: str  # football_eu, nba, tennis
    weight: int = 10  # 1-25, higher = more important source


@dataclass
class Config:
    """Main application configuration."""
    
    # Telegram Bot
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    channel_chat_id: str = field(default_factory=lambda: os.getenv("CHANNEL_CHAT_ID", ""))
    
    # Timezone
    tz: str = "Europe/Madrid"
    
    # Polling
    poll_interval_seconds: int = 300  # 5 minutes
    
    # Rate Limiting
    max_posts_per_day: int = 24
    max_posts_per_hour: int = 3
    
    # Active Window (Europe/Madrid)
    active_window_start: str = "08:00"
    active_window_end: str = "23:30"
    offhours_min_score: int = 85
    
    # Cooldown by sport (minutes)
    cooldown_minutes_by_sport: Dict[str, int] = field(default_factory=lambda: {
        "football_eu": 15,
        "nba": 20,
        "tennis": 30
    })
    
    # Digest Settings
    digest_trigger_count: int = 4
    digest_window_minutes: int = 20
    digest_max_items: int = 5
    digest_score_min: int = 55
    digest_score_max: int = 75
    
    # Image Processing
    image_width: int = 1280
    
    # Watermark
    watermark: WatermarkConfig = field(default_factory=WatermarkConfig)
    
    # Database
    db_path: str = "data/goalfeed.db"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    # Request timeouts
    request_timeout: int = 15
    
    # Dedupe settings
    dedupe_similarity_threshold: float = 0.88
    dedupe_hours_window: int = 6
    
    # Fallback images
    fallback_images: Dict[str, str] = field(default_factory=lambda: {
        "football_eu": "assets/fallback_football.jpg",
        "nba": "assets/fallback_nba.jpg",
        "tennis": "assets/fallback_tennis.jpg",
        "default": "assets/fallback_football.jpg"
    })
    
    # Live matches configuration
    live: LiveConfig = field(default_factory=LiveConfig)
    
    # Top teams for live tracking
    top_teams: Set[str] = field(default_factory=lambda: TOP_TEAMS.copy())
    
    # RSS Sources
    rss_sources: List[RSSSource] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize RSS sources after dataclass initialization."""
        if not self.rss_sources:
            self.rss_sources = self._get_default_sources()
        
        # Override from environment if present
        if os.getenv("BOT_TOKEN"):
            self.bot_token = os.getenv("BOT_TOKEN")
        if os.getenv("CHANNEL_CHAT_ID"):
            self.channel_chat_id = os.getenv("CHANNEL_CHAT_ID")
        if os.getenv("POLL_INTERVAL_SECONDS"):
            self.poll_interval_seconds = int(os.getenv("POLL_INTERVAL_SECONDS"))
        if os.getenv("MAX_POSTS_PER_DAY"):
            self.max_posts_per_day = int(os.getenv("MAX_POSTS_PER_DAY"))
        if os.getenv("MAX_POSTS_PER_HOUR"):
            self.max_posts_per_hour = int(os.getenv("MAX_POSTS_PER_HOUR"))
        if os.getenv("LOG_LEVEL"):
            self.log_level = os.getenv("LOG_LEVEL")
        
        # Live config from environment
        if os.getenv("FOOTBALL_API_KEY"):
            self.live.api_key = os.getenv("FOOTBALL_API_KEY")
        if os.getenv("LIVE_POLL_SECONDS"):
            self.live.poll_seconds = int(os.getenv("LIVE_POLL_SECONDS"))
    
    def _get_default_sources(self) -> List[RSSSource]:
        """Get default RSS sources for all sports - Spanish language."""
        return [
            # ===============================
            # FÚTBOL - MEDIOS ESPAÑOLES
            # ===============================
            RSSSource(
                name="Marca Fútbol",
                url="https://e00-marca.uecdn.es/rss/portada.xml",
                sport_hint="football_eu",
                weight=22
            ),
            RSSSource(
                name="Marca Primera División",
                url="https://e00-marca.uecdn.es/rss/futbol/primera-division.xml",
                sport_hint="football_eu",
                weight=22
            ),
            RSSSource(
                name="AS Fútbol",
                url="https://feeds.as.com/mrss-s/pages/as/site/as.com/section/futbol/portada/",
                sport_hint="football_eu",
                weight=22
            ),
            RSSSource(
                name="Sport",
                url="https://www.sport.es/es/rss/futbol/rss.xml",
                sport_hint="football_eu",
                weight=20
            ),
            RSSSource(
                name="Mundo Deportivo Fútbol",
                url="https://www.mundodeportivo.com/feed/rss/futbol",
                sport_hint="football_eu",
                weight=20
            ),
            RSSSource(
                name="El País Deportes",
                url="https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/deportes/portada/",
                sport_hint="football_eu",
                weight=23
            ),
            RSSSource(
                name="20 Minutos Deportes",
                url="https://www.20minutos.es/rss/deportes/",
                sport_hint="football_eu",
                weight=18
            ),
            RSSSource(
                name="La Vanguardia Deportes",
                url="https://www.lavanguardia.com/rss/deportes.xml",
                sport_hint="football_eu",
                weight=21
            ),
            RSSSource(
                name="Transfermarkt ES",
                url="https://www.transfermarkt.es/rss/news",
                sport_hint="football_eu",
                weight=17  # Fichajes y traspasos
            ),
            
            # ===============================
            # NBA / BALONCESTO
            # ===============================
            RSSSource(
                name="Marca NBA",
                url="https://e00-marca.uecdn.es/rss/baloncesto/nba.xml",
                sport_hint="nba",
                weight=22
            ),
            RSSSource(
                name="AS Baloncesto",
                url="https://feeds.as.com/mrss-s/pages/as/site/as.com/section/baloncesto/portada/",
                sport_hint="nba",
                weight=22
            ),
            RSSSource(
                name="Mundo Deportivo NBA",
                url="https://www.mundodeportivo.com/feed/rss/baloncesto/nba",
                sport_hint="nba",
                weight=20
            ),
            RSSSource(
                name="Somos Basket",
                url="https://www.somosbasket.com/feed/",
                sport_hint="nba",
                weight=18
            ),
            
            # ===============================
            # TENIS
            # ===============================
            RSSSource(
                name="Marca Tenis",
                url="https://e00-marca.uecdn.es/rss/mas-deporte.xml",
                sport_hint="tennis",
                weight=20
            ),
            RSSSource(
                name="AS Tenis",
                url="https://feeds.as.com/mrss-s/pages/as/site/as.com/section/tenis/portada/",
                sport_hint="tennis",
                weight=22
            ),
            RSSSource(
                name="Mundo Deportivo Tenis",
                url="https://www.mundodeportivo.com/feed/rss/tenis",
                sport_hint="tennis",
                weight=20
            ),
            RSSSource(
                name="Eurosport Tenis",
                url="https://www.eurosport.es/rss.xml",
                sport_hint="tennis",
                weight=19
            ),
        ]


# Global config instance
config = Config()


# Official source domains for CONFIRMADO status
OFFICIAL_DOMAINS = {
    # Football
    "realmadrid.com",
    "fcbarcelona.com",
    "atleticodemadrid.com",
    "manutd.com",
    "mancity.com",
    "liverpoolfc.com",
    "chelseafc.com",
    "arsenal.com",
    "tottenhamhotspur.com",
    "juventus.com",
    "acmilan.com",
    "inter.it",
    "psg.fr",
    "fcbayern.com",
    "bvb.de",
    "laliga.com",
    "premierleague.com",
    "bundesliga.com",
    "seriea.it",
    "ligue1.com",
    "uefa.com",
    "fifa.com",
    
    # NBA
    "nba.com",
    "espn.com",
    
    # Tennis
    "atptour.com",
    "wtatennis.com",
    "ausopen.com",
    "rolandgarros.com",
    "wimbledon.com",
    "usopen.org",
    "itftennis.com"
}


# Keywords for sport classification
SPORT_KEYWORDS = {
    "nba": [
        "nba", "lakers", "warriors", "celtics", "bulls", "knicks", "nets",
        "heat", "bucks", "suns", "nuggets", "clippers", "mavericks", "spurs",
        "lebron", "curry", "durant", "giannis", "jokic", "embiid", "luka",
        "basketball", "baloncesto", "canasta", "triple", "slam dunk",
        "all-star", "playoffs nba", "mvp nba", "draft"
    ],
    "tennis": [
        "atp", "wta", "grand slam", "roland garros", "wimbledon", "us open",
        "australian open", "federer", "nadal", "djokovic", "alcaraz", "sinner",
        "swiatek", "sabalenka", "gauff", "rybakina", "medvedev", "zverev",
        "tenis", "tennis", "raqueta", "ace", "break point", "match point",
        "set", "tie break", "deuce"
    ],
    "football_eu": [
        "futbol", "fútbol", "football", "soccer", "liga", "premier league",
        "champions", "europa league", "laliga", "serie a", "bundesliga",
        "ligue 1", "real madrid", "barcelona", "atletico", "manchester",
        "liverpool", "chelsea", "arsenal", "juventus", "milan", "inter",
        "psg", "bayern", "dortmund", "messi", "ronaldo", "mbappe", "haaland",
        "bellingham", "vinicius", "gol", "fichaje", "transfer", "penalty",
        "penalti", "red card", "tarjeta roja", "portero", "goalkeeper",
        "mundial", "eurocopa", "copa del rey", "fa cup"
    ]
}


# Category keywords for classification
CATEGORY_KEYWORDS = {
    "transfer": [
        "fichaje", "transfer", "signing", "firma", "contrato", "contract",
        "traspaso", "cesión", "loan", "llegada", "salida", "venta", "compra",
        "acuerdo", "deal", "negociación", "negotiations", "interés", "interest",
        "pretende", "quiere fichar", "wants to sign", "target", "objetivo"
    ],
    "injury": [
        "lesión", "injury", "injured", "lesionado", "baja", "out", "rotura",
        "esguince", "fractura", "operación", "surgery", "recuperación",
        "recovery", "parte médico", "medical report", "muscular", "rodilla",
        "knee", "tobillo", "ankle", "semanas de baja", "weeks out"
    ],
    "match_result": [
        "resultado", "result", "ganó", "won", "perdió", "lost", "empate",
        "draw", "victoria", "victory", "derrota", "defeat", "goles", "goals",
        "marcador", "score", "final", "partido", "match", "game", "encuentro"
    ],
    "controversy": [
        "polémica", "controversy", "escándalo", "scandal", "sanción",
        "suspension", "expulsión", "red card", "var", "arbitraje", "referee",
        "injusticia", "injustice", "protesta", "protest", "denuncia",
        "investigación", "investigation", "dopaje", "doping"
    ],
    "breaking": [
        "última hora", "breaking", "urgente", "urgent", "oficial", "official",
        "comunicado", "announcement", "confirmado", "confirmed", "ya es",
        "done deal", "cerrado", "exclusiva", "exclusive", "bombazo", "shock"
    ],
    "stats": [
        "récord", "record", "estadísticas", "statistics", "stats", "histórico",
        "historic", "mejor", "best", "peor", "worst", "ranking", "clasificación",
        "standing", "tabla", "table", "promedio", "average", "racha", "streak"
    ],
    "schedule": [
        "calendario", "schedule", "fixture", "horario", "hora", "time",
        "fecha", "date", "jornada", "matchday", "convocatoria", "squad",
        "alineación", "lineup", "once", "starting eleven", "previa", "preview"
    ]
}


# Headline templates by category
HEADLINE_TEMPLATES = {
    "breaking": [
        "🚨 ÚLTIMA HORA: {headline}",
        "⚡ BOMBAZO: {headline}",
        "🔴 URGENTE: {headline}",
        "📢 OFICIAL: {headline}"
    ],
    "transfer": [
        "💰 FICHAJE: {headline}",
        "🔄 MOVIMIENTO: {headline}",
        "✍️ SE CIERRA: {headline}",
        "🎯 OBJETIVO: {headline}"
    ],
    "injury": [
        "🏥 PARTE MÉDICO: {headline}",
        "⚠️ LESIÓN: {headline}",
        "❌ BAJA: {headline}",
        "💔 MALAS NOTICIAS: {headline}"
    ],
    "match_result": [
        "⚽ RESULTADO: {headline}",
        "🏆 VICTORIA: {headline}",
        "📊 MARCADOR FINAL: {headline}"
    ],
    "controversy": [
        "😱 POLÉMICA: {headline}",
        "🔥 SE VIENE LÍO: {headline}",
        "👀 OJO A ESTO: {headline}",
        "⚠️ ESCÁNDALO: {headline}"
    ],
    "stats": [
        "📈 RÉCORD: {headline}",
        "📊 HISTÓRICO: {headline}",
        "🏅 DATO: {headline}"
    ],
    "schedule": [
        "📅 AGENDA: {headline}",
        "⏰ PRÓXIMAMENTE: {headline}",
        "📋 CONVOCATORIA: {headline}"
    ],
    "default": [
        "📰 {headline}",
        "🔔 {headline}",
        "➡️ {headline}"
    ]
}


# Status emojis and labels
STATUS_CONFIG = {
    "CONFIRMADO": {
        "emoji": "✅",
        "label": "CONFIRMADO",
        "description": "Información verificada de fuente oficial o múltiples fuentes"
    },
    "RUMOR": {
        "emoji": "🔮",
        "label": "RUMOR",
        "description": "Información de una única fuente no oficial"
    },
    "EN_DESARROLLO": {
        "emoji": "🔄",
        "label": "EN DESARROLLO",
        "description": "Noticia en curso, pueden haber actualizaciones"
    }
}


# Sport display names and hashtags
SPORT_DISPLAY = {
    "football_eu": {
        "name": "Fútbol",
        "hashtag": "#Fútbol",
        "emoji": "⚽"
    },
    "nba": {
        "name": "NBA",
        "hashtag": "#NBA",
        "emoji": "🏀"
    },
    "tennis": {
        "name": "Tenis",
        "hashtag": "#Tenis",
        "emoji": "🎾"
    }
}


# Category hashtags
CATEGORY_HASHTAGS = {
    "transfer": "#Fichajes",
    "injury": "#Lesión",
    "match_result": "#Resultados",
    "controversy": "#Polémica",
    "breaking": "#ÚltimaHora",
    "stats": "#Estadísticas",
    "schedule": "#Calendario"
}


def get_config() -> Config:
    """Get the global configuration instance."""
    return config
