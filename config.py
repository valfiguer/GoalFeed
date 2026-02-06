"""
GoalFeed Configuration Module
Football News & Rumors Bot - All settings loaded from environment variables.
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
    size_ratio: float = 0.22  # 22% del ancho de la imagen (logo horizontal)
    margin_ratio: float = 0.03
    opacity: float = 0.70


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
                39: "Premier League",  # EPL
                135: "Serie A",  # Italy
                78: "Bundesliga",  # Germany
                61: "Ligue 1",  # France
                3: "UEFA Europa League",  # UEL
            }
        if self.live_images is None:
            self.live_images = {
                "ucl": "assets/live_ucl.jpg",
                "champions": "assets/live_ucl.jpg",
                "laliga": "assets/live_laliga.jpg",
                "premier": "assets/live_premier.jpg",
                "bundesliga": "assets/live_bundesliga.jpg",
                "seriea": "assets/live_seriea.jpg",
                "ligue1": "assets/live_ligue1.jpg",
                "europa": "assets/live_europa.jpg",
                "default": "assets/live_football.jpg"
            }


# Top teams to track for live matches
TOP_TEAMS = {
    # Spain
    "Real Madrid", "Barcelona", "Atlético Madrid", "Atletico Madrid",
    "Atl. Madrid", "Atlético de Madrid", "Sevilla", "Sevilla FC",
    "Valencia", "Valencia CF", "Real Betis", "Betis",
    "Real Sociedad", "Villarreal",
    # England
    "Manchester City", "Manchester United", "Man City", "Man United",
    "Liverpool", "Arsenal", "Chelsea", "Tottenham",
    "Newcastle", "Newcastle United", "Aston Villa",
    "West Ham", "West Ham United",
    # Germany
    "Bayern Munich", "Bayern München", "Borussia Dortmund", "Dortmund",
    "Bayer Leverkusen", "Leverkusen", "RB Leipzig", "Leipzig",
    # France
    "PSG", "Paris Saint-Germain", "Paris Saint Germain",
    "Olympique Marseille", "Marseille", "Lyon", "Olympique Lyon",
    "Monaco", "AS Monaco", "Lille",
    # Italy
    "Inter", "Inter Milan", "Internazionale", "AC Milan", "Milan",
    "Juventus", "Napoli", "SSC Napoli", "Roma", "AS Roma",
    "Lazio", "SS Lazio", "Atalanta",
    # Portugal
    "Benfica", "SL Benfica", "Porto", "FC Porto", "Sporting CP", "Sporting",
    # Netherlands
    "Ajax", "AFC Ajax", "PSV", "PSV Eindhoven", "Feyenoord",
}


@dataclass
class RSSSource:
    """RSS feed source configuration."""
    name: str
    url: str
    sport_hint: str  # football_eu
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

    # Scheduled publication times (Europe/Madrid)
    scheduled_post_times: List[str] = field(default_factory=lambda: [
        "12:00", "15:00", "18:00", "21:00"
    ])

    # Rate Limiting
    max_posts_per_day: int = 4
    max_posts_per_hour: int = 1

    # Active Window (Europe/Madrid)
    active_window_start: str = "08:00"
    active_window_end: str = "23:30"
    offhours_min_score: int = 80

    # Cooldown by sport (minutes)
    cooldown_minutes_by_sport: Dict[str, int] = field(default_factory=lambda: {
        "football_eu": 10,
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
        """Get default RSS sources - Football only, Spanish language."""
        return [
            # ===============================
            # FUTBOL - MEDIOS GENERALES
            # ===============================
            RSSSource(
                name="Marca Futbol",
                url="https://e00-marca.uecdn.es/rss/portada.xml",
                sport_hint="football_eu",
                weight=22
            ),
            RSSSource(
                name="Marca Primera Division",
                url="https://e00-marca.uecdn.es/rss/futbol/primera-division.xml",
                sport_hint="football_eu",
                weight=22
            ),
            RSSSource(
                name="AS Futbol",
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
                name="Mundo Deportivo Futbol",
                url="https://www.mundodeportivo.com/feed/rss/futbol",
                sport_hint="football_eu",
                weight=20
            ),
            RSSSource(
                name="El Pais Deportes",
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
                weight=17
            ),

            # ===============================
            # FUTBOL - FICHAJES Y RUMORES
            # ===============================
            RSSSource(
                name="90min ES",
                url="https://www.90min.com/es/feed",
                sport_hint="football_eu",
                weight=18
            ),
            RSSSource(
                name="Football-Espana",
                url="https://www.football-espana.net/feed",
                sport_hint="football_eu",
                weight=17
            ),
            RSSSource(
                name="Diario SPORT Fichajes",
                url="https://www.sport.es/es/rss/fichajes/rss.xml",
                sport_hint="football_eu",
                weight=19
            ),
            RSSSource(
                name="Marca Champions",
                url="https://e00-marca.uecdn.es/rss/futbol/champions-league.xml",
                sport_hint="football_eu",
                weight=20
            ),
        ]


# Global config instance
config = Config()


# Official source domains for CONFIRMADO status
OFFICIAL_DOMAINS = {
    # Spanish clubs
    "realmadrid.com",
    "fcbarcelona.com",
    "atleticodemadrid.com",
    "sevillafc.es",
    "valenciacf.com",
    "villarrealcf.es",
    "realsociedad.eus",
    "realbetisbalompie.es",
    # English clubs
    "manutd.com",
    "mancity.com",
    "liverpoolfc.com",
    "chelseafc.com",
    "arsenal.com",
    "tottenhamhotspur.com",
    "nufc.co.uk",
    "avfc.co.uk",
    "whufc.com",
    # Italian clubs
    "juventus.com",
    "acmilan.com",
    "inter.it",
    "sscnapoli.it",
    "asroma.com",
    "sslazio.it",
    "atalanta.it",
    # German clubs
    "fcbayern.com",
    "bvb.de",
    "bayer04.de",
    "rbleipzig.com",
    # French clubs
    "psg.fr",
    "om.fr",
    "ol.fr",
    "asmonaco.com",
    "losc.fr",
    # Portuguese clubs
    "slbenfica.pt",
    "fcporto.pt",
    "sporting.pt",
    # Dutch clubs
    "ajax.nl",
    "psv.nl",
    "feyenoord.nl",
    # Competitions & governing bodies
    "laliga.com",
    "premierleague.com",
    "bundesliga.com",
    "seriea.it",
    "ligue1.com",
    "uefa.com",
    "fifa.com",
    "rfef.es",
    "thefa.com",
}


# Keywords for sport classification (football only)
SPORT_KEYWORDS = {
    "football_eu": [
        # General
        "futbol", "football", "soccer", "gol", "penalty", "penalti",
        "portero", "goalkeeper", "tarjeta roja", "red card",
        "tarjeta amarilla", "yellow card", "fuera de juego", "offside",
        "corner", "falta", "free kick", "delantero", "defensa", "mediocampista",
        "entrenador", "manager", "banquillo", "suplente", "titular",
        # Ligas y competiciones
        "liga", "premier league", "champions", "champions league",
        "europa league", "conference league", "laliga", "serie a",
        "bundesliga", "ligue 1", "copa del rey", "fa cup",
        "carabao cup", "dfb pokal", "coppa italia", "coupe de france",
        "supercopa", "community shield", "nations league",
        "mundial", "eurocopa", "copa america", "libertadores",
        # Fichajes y mercado
        "fichaje", "transfer", "traspaso", "cesion", "loan",
        "clausula", "clausula de rescision", "mercado", "mercado de fichajes",
        "agente libre", "free agent", "renovacion", "contrato",
        "negociacion", "acuerdo", "oferta", "puja", "tanteo",
        "rumor", "rumores", "se rumorea", "suena para",
        # Equipos top
        "real madrid", "barcelona", "atletico", "sevilla", "valencia",
        "villarreal", "betis", "real sociedad",
        "manchester", "liverpool", "chelsea", "arsenal", "tottenham",
        "newcastle", "aston villa", "west ham",
        "juventus", "milan", "inter", "napoli", "roma", "lazio",
        "psg", "bayern", "dortmund", "leverkusen",
        "benfica", "porto", "sporting", "ajax",
        # Jugadores top
        "messi", "ronaldo", "mbappe", "haaland", "bellingham",
        "vinicius", "yamal", "pedri", "gavi",
    ]
}


# Category keywords for classification
CATEGORY_KEYWORDS = {
    "breaking": [
        "ultima hora", "breaking", "urgente", "urgent", "oficial", "official",
        "comunicado", "announcement", "confirmado", "confirmed", "ya es",
        "done deal", "cerrado", "bombazo", "shock"
    ],
    "rumor": [
        "se rumorea", "rumor", "rumores", "en el radar", "podria fichar",
        "suena para", "suena con", "pretende", "interesa", "sigue de cerca",
        "tiene en agenda", "pregunta por", "apunta a", "se fija en",
        "fuentes cercanas", "segun fuentes", "segun informan",
        "estaria interesado", "estarian negociando", "estarian cerca",
        "quiere hacerse con", "pone sus ojos", "tiene en el punto de mira",
        "posible destino", "posible fichaje", "posible salida",
        "tantea", "sondea", "negocia en secreto", "contactos",
        "primicia", "exclusiva", "informacion exclusiva",
        "medios italianos", "medios ingleses", "medios franceses",
        "prensa italiana", "prensa inglesa", "prensa francesa",
        "en la orbita", "en la agenda"
    ],
    "transfer": [
        "fichaje", "transfer", "signing", "firma", "contrato", "contract",
        "traspaso", "cesion", "loan", "llegada", "salida", "venta", "compra",
        "acuerdo", "deal", "negociacion", "negotiations", "interes", "interest",
        "quiere fichar", "wants to sign", "target", "objetivo",
        "clausula", "buyout clause", "traspaso cerrado", "ya es jugador",
        "nuevo refuerzo", "mercado de fichajes", "ventana de transferencias",
        "agente libre", "free agent", "rescision", "renovacion"
    ],
    "injury": [
        "lesion", "injury", "injured", "lesionado", "baja", "out", "rotura",
        "esguince", "fractura", "operacion", "surgery", "recuperacion",
        "recovery", "parte medico", "medical report", "muscular", "rodilla",
        "knee", "tobillo", "ankle", "semanas de baja", "weeks out"
    ],
    "match_result": [
        "resultado", "result", "gano", "won", "perdio", "lost", "empate",
        "draw", "victoria", "victory", "derrota", "defeat", "goles", "goals",
        "marcador", "score", "final", "partido", "match", "game", "encuentro",
        "cronica", "resumen", "highlights", "remontada", "goleada",
        "primera division", "primera divisi", "jornada laliga",
        "derbi", "clasico", "el clasico",
        "penaltis", "tanda de penaltis", "prorroga", "tiempo extra",
        "hat trick", "hat-trick", "triplete", "doblete",
        "porteria a cero", "clean sheet", "autogol",
        "minuto", "descuento", "tiempo anadido", "tiempo de descuento"
    ],
    "controversy": [
        "polemica", "controversy", "escandalo", "scandal", "sancion",
        "suspension", "expulsion", "red card", "var", "arbitraje", "referee",
        "injusticia", "injustice", "protesta", "protest", "denuncia",
        "investigacion", "investigation", "dopaje", "doping"
    ],
    "stats": [
        "record", "estadisticas", "statistics", "stats", "historico",
        "historic", "mejor", "best", "peor", "worst", "ranking", "clasificacion",
        "standing", "tabla", "table", "promedio", "average", "racha", "streak"
    ],
    "schedule": [
        "calendario", "schedule", "fixture", "horario", "hora", "time",
        "fecha", "date", "jornada", "matchday", "convocatoria", "squad",
        "alineacion", "lineup", "once", "starting eleven", "previa", "preview",
        "donde ver", "television", "transmision", "arbitro designado",
        "analisis previo", "cara a cara", "pronostico", "apuestas",
        "proxima jornada", "proxima fecha", "suspendido", "aplazado"
    ]
}


# Headline templates by category
HEADLINE_TEMPLATES = {
    "breaking": [
        "🚨 ULTIMA HORA: {headline}",
        "⚡ BOMBAZO: {headline}",
        "🔴 URGENTE: {headline}",
        "📢 OFICIAL: {headline}",
        "🚨 FLASH: {headline}",
        "⚡ ALERTA: {headline}",
        "🔴 CONFIRMADO: {headline}",
        "📢 COMUNICADO: {headline}"
    ],
    "rumor": [
        "🔮 RUMOR: {headline}",
        "👀 OJO: {headline}",
        "🗣️ SE DICE QUE: {headline}",
        "💣 BOMBAZO: {headline}",
        "🎯 EN EL RADAR: {headline}",
        "🔎 SEGUN FUENTES: {headline}",
        "🔮 EXCLUSIVA: {headline}"
    ],
    "transfer": [
        "💰 FICHAJE: {headline}",
        "🔄 MOVIMIENTO: {headline}",
        "✍️ SE CIERRA: {headline}",
        "🎯 OBJETIVO: {headline}",
        "💰 DONE DEAL: {headline}",
        "🔄 TRASPASO: {headline}",
        "✍️ FIRMA: {headline}",
        "🎯 REFUERZO: {headline}"
    ],
    "injury": [
        "🏥 PARTE MEDICO: {headline}",
        "⚠️ LESION: {headline}",
        "❌ BAJA: {headline}",
        "💔 MALAS NOTICIAS: {headline}",
        "🏥 BAJA CONFIRMADA: {headline}",
        "⚠️ SE PIERDE: {headline}",
        "❌ NO ESTARA: {headline}"
    ],
    "match_result": [
        "⚽ CRONICA: {headline}",
        "🏆 RESULTADO: {headline}",
        "📊 MARCADOR FINAL: {headline}",
        "⚽ PARTIDAZO: {headline}",
        "🏆 ASI FUE: {headline}",
        "📊 FINAL DEL PARTIDO: {headline}",
        "⚽ RESUMEN: {headline}",
        "🏆 VICTORIA: {headline}",
        "📰 LA CRONICA: {headline}"
    ],
    "controversy": [
        "😱 POLEMICA: {headline}",
        "🔥 SE VIENE LIO: {headline}",
        "👀 OJO A ESTO: {headline}",
        "⚠️ ESCANDALO: {headline}",
        "😱 INCREDBLE: {headline}",
        "🔥 TERREMOTO: {headline}",
        "👀 ATENCION: {headline}"
    ],
    "stats": [
        "📈 RECORD: {headline}",
        "📊 HISTORICO: {headline}",
        "🏅 DATO: {headline}",
        "📈 BRUTAL: {headline}",
        "📊 IMPRESIONANTE: {headline}",
        "🏅 CIFRA: {headline}"
    ],
    "schedule": [
        "📅 PREVIA: {headline}",
        "⏰ HOY SE JUEGA: {headline}",
        "📋 CONVOCATORIA: {headline}",
        "📅 JORNADA: {headline}",
        "⏰ PROXIMO PARTIDO: {headline}",
        "📋 ALINEACION: {headline}",
        "📅 AGENDA DEL DIA: {headline}",
        "⏰ A QUE HORA JUEGA: {headline}"
    ],
    "default": [
        "📰 {headline}",
        "🔔 {headline}",
        "➡️ {headline}",
        "⚽ {headline}"
    ]
}


# Status emojis and labels
STATUS_CONFIG = {
    "CONFIRMADO": {
        "emoji": "✅",
        "label": "CONFIRMADO",
        "description": "Informacion verificada de fuente oficial o multiples fuentes"
    },
    "RUMOR": {
        "emoji": "🔮",
        "label": "RUMOR",
        "description": "Informacion de una unica fuente no oficial"
    },
    "EN_DESARROLLO": {
        "emoji": "🔄",
        "label": "EN DESARROLLO",
        "description": "Noticia en curso, pueden haber actualizaciones"
    }
}


# Sport display names and hashtags (football only)
SPORT_DISPLAY = {
    "football_eu": {
        "name": "Futbol",
        "hashtag": "#Futbol",
        "emoji": "⚽"
    }
}


# Category hashtags
CATEGORY_HASHTAGS = {
    "transfer": "#Fichajes",
    "rumor": "#Rumores",
    "injury": "#Lesion",
    "match_result": "#Resultados",
    "controversy": "#Polemica",
    "breaking": "#UltimaHora",
    "stats": "#Estadisticas",
    "schedule": "#Calendario"
}


# Specialist transfer/rumor source domains (used for exclusivity scoring)
TRANSFER_SPECIALIST_DOMAINS = {
    "transfermarkt.es",
    "transfermarkt.com",
    "fichajes.net",
    "fichajes.com",
    "90min.com",
    "football-espana.net",
    "fabrizio romano",  # reporter name, matched in text
}


def get_config() -> Config:
    """Get the global configuration instance."""
    return config
