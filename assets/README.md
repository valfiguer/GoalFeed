# GoalFeed Assets

Este directorio debe contener los siguientes archivos:

## Requeridos

### logo.png
- Logo para watermark
- Formato: PNG con transparencia (RGBA)
- Tamaño recomendado: 200x200 píxeles o similar
- Se escalará automáticamente al 16% del ancho de la imagen

### fallback_football.jpg
- Imagen de respaldo para noticias de fútbol
- Formato: JPEG
- Tamaño recomendado: 1280x720 píxeles (16:9)
- Se usa cuando no hay imagen en la noticia

### fallback_nba.jpg
- Imagen de respaldo para noticias de NBA
- Formato: JPEG
- Tamaño recomendado: 1280x720 píxeles (16:9)

### fallback_tennis.jpg
- Imagen de respaldo para noticias de tenis
- Formato: JPEG
- Tamaño recomendado: 1280x720 píxeles (16:9)

## Para Partidos en Directo (NUEVO)

### live_ucl.jpg
- Imagen para eventos de UEFA Champions League
- Formato: JPEG
- Tamaño recomendado: 1280x720 píxeles (16:9)
- Sugerencia: Fondo oscuro con logo de UCL, texto "LIVE"

### live_laliga.jpg
- Imagen para eventos de LaLiga
- Formato: JPEG
- Tamaño recomendado: 1280x720 píxeles (16:9)
- Sugerencia: Fondo con colores de LaLiga, texto "EN DIRECTO"

### live_football.jpg (opcional)
- Imagen genérica para otras competiciones de fútbol
- Formato: JPEG
- Tamaño recomendado: 1280x720 píxeles (16:9)

## Notas

- Si no existen las imágenes de fallback, el sistema generará imágenes placeholder grises
- El logo debe tener transparencia para que el watermark se vea bien
- Las imágenes se redimensionarán automáticamente a 1280px de ancho manteniendo la proporción
