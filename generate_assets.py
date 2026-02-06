#!/usr/bin/env python3
"""
Utility script to generate placeholder assets for GoalFeed.
Run this once to create the fallback images, live images, and a placeholder logo.
"""
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)


def _get_font(size: int):
    """Try to load a nice font, fallback to default."""
    font_paths = [
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_gradient(draw, width, height, color_top, color_bottom):
    """Draw a vertical gradient."""
    for y in range(height):
        ratio = y / height
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def create_fallback_image(output_path: str, sport_name: str, emoji: str):
    """Create the main fallback image for football posts."""
    width, height = 1280, 720
    img = Image.new('RGB', (width, height), (20, 25, 35))
    draw = ImageDraw.Draw(img)

    # Dark green gradient background
    _draw_gradient(draw, width, height, (15, 40, 25), (10, 20, 15))

    # Accent stripe at top
    draw.rectangle([(0, 0), (width, 6)], fill=(46, 204, 113))

    # Subtle field lines
    draw.ellipse(
        [(width // 2 - 150, height // 2 - 150),
         (width // 2 + 150, height // 2 + 150)],
        outline=(255, 255, 255, 15), width=2
    )
    draw.line([(width // 2, 100), (width // 2, height - 100)],
              fill=(255, 255, 255, 15), width=2)

    # Main text
    font_large = _get_font(68)
    font_medium = _get_font(32)
    font_small = _get_font(24)

    text = "GoalFeed"
    bbox = draw.textbbox((0, 0), text, font=font_large)
    tw = bbox[2] - bbox[0]
    x = (width - tw) // 2
    y = height // 2 - 80
    draw.text((x + 2, y + 2), text, fill=(0, 0, 0), font=font_large)
    draw.text((x, y), text, fill=(46, 204, 113), font=font_large)

    subtitle = "Football News & Rumors"
    bbox = draw.textbbox((0, 0), subtitle, font=font_medium)
    sw = bbox[2] - bbox[0]
    draw.text(((width - sw) // 2, y + 85), subtitle, fill=(200, 200, 200), font=font_medium)

    # Bottom accent
    draw.rectangle([(0, height - 6), (width, height)], fill=(46, 204, 113))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'JPEG', quality=92)
    print(f"  Created: {output_path}")


def create_live_image(output_path: str, league_name: str, color_top: tuple, color_bottom: tuple, accent: tuple):
    """Create a live match image for a specific league."""
    width, height = 1280, 720
    img = Image.new('RGB', (width, height), color_top)
    draw = ImageDraw.Draw(img)

    # Gradient background
    _draw_gradient(draw, width, height, color_top, color_bottom)

    # Accent stripe
    draw.rectangle([(0, 0), (width, 5)], fill=accent)
    draw.rectangle([(0, height - 5), (width, height)], fill=accent)

    # Side accents
    draw.rectangle([(0, 0), (5, height)], fill=accent)
    draw.rectangle([(width - 5, 0), (width, height)], fill=accent)

    font_large = _get_font(60)
    font_medium = _get_font(36)
    font_small = _get_font(28)

    # LIVE badge
    badge_text = "LIVE"
    bbox = draw.textbbox((0, 0), badge_text, font=font_medium)
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    bx = (width - bw) // 2
    by = height // 2 - 100
    # Red pill background
    draw.rounded_rectangle(
        [(bx - 20, by - 10), (bx + bw + 20, by + bh + 10)],
        radius=8, fill=(220, 30, 30)
    )
    draw.text((bx, by), badge_text, fill=(255, 255, 255), font=font_medium)

    # League name
    bbox = draw.textbbox((0, 0), league_name, font=font_large)
    lw = bbox[2] - bbox[0]
    lx = (width - lw) // 2
    ly = height // 2 - 20
    draw.text((lx + 2, ly + 2), league_name, fill=(0, 0, 0), font=font_large)
    draw.text((lx, ly), league_name, fill=(255, 255, 255), font=font_large)

    # GoalFeed branding
    brand = "GoalFeed"
    bbox = draw.textbbox((0, 0), brand, font=font_small)
    draw.text(((width - (bbox[2] - bbox[0])) // 2, ly + 80),
              brand, fill=accent, font=font_small)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'JPEG', quality=92)
    print(f"  Created: {output_path}")


def create_logo(output_path: str, size: int = 200):
    """Create a placeholder logo."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Circular green background
    margin = 10
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(46, 204, 113, 230)
    )

    font = _get_font(80)
    text = "GF"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((size - tw) // 2, (size - th) // 2 - 10),
              text, fill=(255, 255, 255), font=font)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'PNG')
    print(f"  Created: {output_path}")


def main():
    """Generate all placeholder assets."""
    print("Generating GoalFeed assets...\n")

    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')

    # 1. Main fallback
    print("[Fallback]")
    create_fallback_image(
        os.path.join(assets_dir, 'fallback_football.jpg'),
        'Futbol', '⚽'
    )

    # 2. Live images per league
    print("\n[Live images]")
    live_leagues = [
        # (filename, display_name, color_top, color_bottom, accent)
        ('live_ucl.jpg', 'UEFA Champions League',
         (10, 15, 50), (5, 5, 25), (0, 80, 170)),
        ('live_laliga.jpg', 'LaLiga',
         (15, 25, 10), (10, 15, 5), (255, 87, 34)),
        ('live_premier.jpg', 'Premier League',
         (55, 0, 60), (30, 0, 35), (150, 60, 180)),
        ('live_seriea.jpg', 'Serie A',
         (0, 35, 60), (0, 15, 35), (0, 140, 200)),
        ('live_bundesliga.jpg', 'Bundesliga',
         (50, 10, 10), (25, 5, 5), (220, 50, 50)),
        ('live_ligue1.jpg', 'Ligue 1',
         (0, 30, 15), (0, 15, 10), (0, 170, 80)),
        ('live_europa.jpg', 'UEFA Europa League',
         (50, 30, 0), (30, 15, 0), (255, 140, 0)),
        ('live_football.jpg', 'Football',
         (15, 30, 15), (5, 15, 5), (46, 204, 113)),
    ]

    for filename, name, ct, cb, accent in live_leagues:
        create_live_image(os.path.join(assets_dir, filename), name, ct, cb, accent)

    # 3. Logo
    print("\n[Logo]")
    create_logo(os.path.join(assets_dir, 'logo.png'))

    print("\nAll assets generated!")


if __name__ == "__main__":
    main()
