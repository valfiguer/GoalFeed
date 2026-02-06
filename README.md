# GoalFeed 🏆

Bot autopublicador de noticias deportivas y **resultados en directo** para Telegram.

Recopila noticias deportivas (Fútbol europeo, Tenis, NBA) desde RSS, deduplica, puntúa por importancia, aplica reglas anti-saturación, genera copy con estilo atractivo y publica automáticamente en un canal de Telegram.

**NUEVO:** También trackea partidos en vivo de Champions League y LaLiga, publicando goles, expulsiones y resultados finales de equipos TOP.

## 📋 Características

### Noticias RSS
- **Recopilación automática** de noticias desde múltiples fuentes RSS
- **Clasificación inteligente** por deporte (Fútbol, NBA, Tenis) y categoría
- **Sistema de puntuación** que prioriza noticias importantes
- **Deduplicación** usando URL canónica y similitud de títulos (fuzzy matching)
- **Reglas anti-saturación**:
  - Máximo 24 posts/día
  - Máximo 3 posts/hora
  - Ventana activa configurable (08:00-23:30 Europe/Madrid)
  - Cooldown por deporte
  - Agrupación en digest cuando hay muchas noticias similares
- **Procesamiento de imágenes** con watermark del logo
- **Estados de verificación**: CONFIRMADO, RUMOR, EN DESARROLLO
- **Estilo editorial atractivo** sin inventar información

### 🔴 Resultados en Directo (NUEVO)
- **Seguimiento en tiempo real** de partidos de Champions League y LaLiga
- **Filtrado inteligente**: Solo partidos con equipos TOP (Real Madrid, Barcelona, etc.)
- **Eventos publicables**:
  - ⚽ Goles (con jugador y minuto)
  - 🟥 Expulsiones (roja directa o doble amarilla)
  - 🏁 Resultados finales
  - ❌ Penaltis fallados
  - 📺 Decisiones VAR importantes
- **Anti-spam**: Máximo de eventos por partido y cooldown entre publicaciones
- **Imágenes específicas** por competición (UCL, LaLiga)

## 🚀 Instalación

### Requisitos previos

- Python 3.11 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

1. **Clonar o crear el proyecto**

```bash
cd /ruta/a/tu/proyecto
```

2. **Crear entorno virtual (recomendado)**

```bash
python3 -m venv venv
source venv/bin/activate  # En Linux/Mac
# o
venv\Scripts\activate  # En Windows
```

3. **Instalar dependencias**

```bash
pip install -r goalfeed/requirements.txt
```

4. **Configurar variables de entorno**

Crear archivo `.env` en la raíz del proyecto:

```bash
# Telegram Bot
BOT_TOKEN=tu_token_aqui
CHANNEL_CHAT_ID=@tu_canal_o_id

# Live Match Tracking (opcional pero recomendado)
FOOTBALL_API_KEY=tu_api_key_de_rapidapi

# Opcional
POLL_INTERVAL_SECONDS=300
LIVE_POLL_SECONDS=90
MAX_POSTS_PER_DAY=24
MAX_POSTS_PER_HOUR=3
LOG_LEVEL=INFO
```

5. **Añadir assets**

Colocar los siguientes archivos en `goalfeed/assets/`:
- `logo.png` - Logo para watermark (PNG con transparencia, recomendado ~200x200px)
- `fallback_football.jpg` - Imagen de fallback para fútbol (1280x720px recomendado)
- `fallback_nba.jpg` - Imagen de fallback para NBA
- `fallback_tennis.jpg` - Imagen de fallback para tenis
- `live_ucl.jpg` - Imagen para eventos de Champions League (1280x720px)
- `live_laliga.jpg` - Imagen para eventos de LaLiga (1280x720px)

## 🤖 Configuración del Bot de Telegram

### 1. Crear el Bot

1. Abre Telegram y busca `@BotFather`
2. Envía el comando `/newbot`
3. Sigue las instrucciones para elegir nombre y username
4. BotFather te dará un **token** como: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
5. Guarda este token como `BOT_TOKEN` en tu archivo `.env`

### 2. Crear el Canal

1. En Telegram, crea un nuevo canal (puede ser público o privado)
2. Configura el nombre y la descripción

### 3. Añadir el Bot como Administrador

1. Ve a la configuración del canal
2. Selecciona "Administradores"
3. Busca y añade tu bot
4. Dale permisos de "Publicar mensajes"

### 4. Obtener el Chat ID del Canal

**Para canales públicos:**
- El `CHANNEL_CHAT_ID` es simplemente `@username_del_canal`
- Ejemplo: `@MiCanalDeportivo`

**Para canales privados:**
1. Añade el bot `@getmyid_bot` al canal temporalmente
2. Envía cualquier mensaje al canal
3. El bot te responderá con el ID (será algo como `-1001234567890`)
4. Usa ese número como `CHANNEL_CHAT_ID`
5. Puedes eliminar `@getmyid_bot` del canal después

## 🏃 Ejecución

### Modo normal

```bash
cd goalfeed
python main.py
```

### Como módulo

```bash
python -m goalfeed.main
```

### Con logs detallados

```bash
LOG_LEVEL=DEBUG python goalfeed/main.py
```

### Ejecución en segundo plano (Linux/Mac)

```bash
nohup python goalfeed/main.py > /dev/null 2>&1 &
```

### Con systemd (Linux - producción)

Crear `/etc/systemd/system/goalfeed.service`:

```ini
[Unit]
Description=GoalFeed Telegram Bot
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/a/tu/proyecto
Environment="BOT_TOKEN=tu_token"
Environment="CHANNEL_CHAT_ID=@tu_canal"
ExecStart=/ruta/a/tu/proyecto/venv/bin/python goalfeed/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Luego:
```bash
sudo systemctl daemon-reload
sudo systemctl enable goalfeed
sudo systemctl start goalfeed
```

## ⚙️ Configuración Avanzada

### Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Token del bot de Telegram | (requerido) |
| `CHANNEL_CHAT_ID` | ID o @username del canal | (requerido) |
| `FOOTBALL_API_KEY` | API key de API-Football (RapidAPI) | (opcional) |
| `POLL_INTERVAL_SECONDS` | Intervalo entre ciclos RSS | 300 (5 min) |
| `LIVE_POLL_SECONDS` | Intervalo para partidos en directo | 90 |
| `MAX_POSTS_PER_DAY` | Máximo de posts diarios | 24 |
| `MAX_POSTS_PER_HOUR` | Máximo de posts por hora | 3 |
| `LOG_LEVEL` | Nivel de logging | INFO |

### Configuración en `config.py`

Puedes modificar `goalfeed/config.py` para ajustar:

- **Ventana activa**: Horas de publicación
- **Cooldowns por deporte**: Tiempo mínimo entre posts del mismo deporte
- **Configuración de digest**: Cuándo agrupar noticias
- **Fuentes RSS**: Añadir/modificar feeds
- **Watermark**: Tamaño, posición, opacidad

### Añadir nuevas fuentes RSS

En `config.py`, añade a la lista `rss_sources`:

```python
RSSSource(
    name="Nombre de la Fuente",
    url="https://ejemplo.com/rss/feed.xml",
    sport_hint="football_eu",  # o "nba", "tennis"
    weight=15  # 1-25, mayor = más importante
)
```

## 📁 Estructura del Proyecto

```
goalfeed/
├── main.py              # Punto de entrada principal
├── config.py            # Configuración
├── requirements.txt     # Dependencias
├── README.md           # Esta documentación
│
├── assets/             # Recursos estáticos
│   ├── logo.png
│   ├── fallback_football.jpg
│   ├── fallback_nba.jpg
│   ├── fallback_tennis.jpg
│   ├── live_ucl.jpg        # Imagen para Champions League
│   └── live_laliga.jpg     # Imagen para LaLiga
│
├── db/                 # Capa de base de datos
│   ├── database.py
│   ├── repo.py
│   └── schema.sql
│
├── collector/          # Recopilación de noticias
│   ├── rss_collector.py
│   └── og_image.py
│
├── processor/          # Procesamiento de noticias
│   ├── normalize.py
│   ├── classify.py
│   ├── ranker.py
│   └── dedupe.py
│
├── scheduler/          # Planificación y reglas
│   ├── rules.py
│   └── planner.py
│
├── editorial/          # Generación de contenido
│   └── copywriter.py
│
├── media/              # Procesamiento de imágenes
│   ├── download.py
│   ├── image_prep.py
│   └── watermark.py
│
├── live/               # 🔴 Partidos en directo (NUEVO)
│   ├── live_collector.py   # Obtención de datos de API
│   ├── live_rules.py       # Reglas anti-spam
│   └── live_publisher.py   # Formato y publicación
│
├── publisher/          # Publicación en Telegram
│   └── telegram_publisher.py
│
├── utils/              # Utilidades
│   ├── timeutils.py
│   └── text.py
│
├── logs/               # Archivos de log
│   └── app.log
│
└── data/               # Base de datos SQLite
    └── goalfeed.db
```

## 📊 Base de Datos

GoalFeed usa SQLite para persistencia. Las tablas principales son:

- `sources`: Fuentes RSS configuradas
- `articles`: Todos los artículos recopilados
- `posts`: Posts publicados en Telegram
- `digests`: Resúmenes/digestos publicados
- `daily_stats`: Estadísticas diarias
- `live_matches`: Partidos en seguimiento (NUEVO)
- `live_events`: Eventos de partidos publicados (NUEVO)

## 🔴 Configuración de Partidos en Directo

### Obtener API Key de API-Football

1. Ve a [RapidAPI - API-Football](https://rapidapi.com/api-sports/api/api-football/)
2. Crea una cuenta gratuita
3. Suscríbete al plan gratuito (100 peticiones/día)
4. Copia tu `X-RapidAPI-Key`
5. Añádela como `FOOTBALL_API_KEY` en tu `.env`

### Competiciones Trackeadas

Por defecto, GoalFeed sigue:
- **UEFA Champions League** (ID: 2)
- **LaLiga** (ID: 140)

Puedes modificar esto en `config.py` en `LiveConfig.tracked_leagues`.

### Equipos TOP

Solo se publican eventos de partidos donde juega al menos uno de estos equipos:
- Real Madrid, Barcelona, Atlético Madrid
- Manchester City, Manchester United, Liverpool, Arsenal, Chelsea
- Bayern Munich, Borussia Dortmund
- PSG
- Juventus, Inter, AC Milan

Puedes modificar la lista `TOP_TEAMS` en `config.py`.

### Formato de Mensajes Live

**Gol:**
```
⚽ GOL | Champions League
Real Madrid 1–0 Bayern
Min 34 | Jude Bellingham
🅰️ Asistencia: Vinícius Jr

#UCL #ChampionsLeague #GoalFeed
```

**Final:**
```
🏁 FINAL | LaLiga
Barcelona 2–1 Sevilla
🏆 Victoria local

#LaLiga #FútbolEspañol #GoalFeed
```

**Expulsión:**
```
🟥 EXPULSIÓN | Champions League
Inter 1–1 Manchester City
Min 67 | Jugador
🔴 Roja directa

#UCL #ChampionsLeague #GoalFeed
```

## 🔍 Logs

Los logs se guardan en `goalfeed/logs/app.log` y también se muestran en consola.

Niveles:
- `DEBUG`: Información detallada
- `INFO`: Información general (default)
- `WARNING`: Advertencias
- `ERROR`: Errores

## 🛠️ Solución de Problemas

### "Bot token is required"
Asegúrate de configurar `BOT_TOKEN` en el archivo `.env` o como variable de entorno.

### "Channel chat ID is required"
Configura `CHANNEL_CHAT_ID` con el @username o ID numérico del canal.

### El bot no publica nada
1. Verifica que el bot sea admin del canal con permisos de publicar
2. Revisa los logs para ver si hay errores de las fuentes RSS
3. Verifica que estás dentro de la ventana activa (08:00-23:30)

### No se publican partidos en directo
1. Verifica que `FOOTBALL_API_KEY` está configurada correctamente
2. Revisa los logs para ver si hay errores de la API
3. Asegúrate de que hay partidos activos de equipos TOP
4. El plan gratuito tiene 100 peticiones/día, puede que las hayas agotado

### Imágenes sin watermark
Asegúrate de que `assets/logo.png` existe y es un PNG válido con transparencia.

### Error de conexión a Telegram
Verifica tu conexión a internet y que el token del bot sea correcto.

## 📝 Licencia

Este proyecto es software libre. Puedes modificarlo y distribuirlo según tus necesidades.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request para sugerir mejoras.

---

**GoalFeed** - Mantente informado del mundo del deporte ⚽🏀🎾

*Ahora con resultados en DIRECTO de Champions League y LaLiga* 🔴
