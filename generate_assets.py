#!/usr/bin/env python3
"""
Utility script to generate placeholder assets for GoalFeed.
Run this once to create the fallback images and a placeholder logo.
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


def create_fallback_image(
    output_path: str,
    sport_name: str,
    emoji: str,
    color: tuple = (30, 35, 45)
):
    """Create a fallback image for a sport."""
    width, height = 1280, 720
    
    # Create image with gradient-like background
    img = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(img)
    
    # Add some visual interest with rectangles
    accent_color = {
        'Fútbol': (0, 100, 0),      # Dark green
        'NBA': (139, 0, 0),          # Dark red
        'Tenis': (0, 100, 100),      # Dark cyan
    }.get(sport_name, (50, 50, 80))
    
    # Draw accent bars
    draw.rectangle([(0, 0), (width, 80)], fill=accent_color)
    draw.rectangle([(0, height-80), (width, height)], fill=accent_color)
    
    # Draw GoalFeed text
    try:
        # Try to use a larger font
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
    
    # Center text
    text = f"GoalFeed | {sport_name}"
    
    # Get text size
    bbox = draw.textbbox((0, 0), text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2 - 30
    
    # Draw text with shadow
    draw.text((x+2, y+2), text, fill=(0, 0, 0), font=font_large)
    draw.text((x, y), text, fill=(255, 255, 255), font=font_large)
    
    # Draw subtitle
    subtitle = "Noticias deportivas en tiempo real"
    bbox = draw.textbbox((0, 0), subtitle, font=font_medium)
    sub_width = bbox[2] - bbox[0]
    
    x_sub = (width - sub_width) // 2
    draw.text((x_sub, y + text_height + 20), subtitle, fill=(180, 180, 180), font=font_medium)
    
    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'JPEG', quality=90)
    print(f"✅ Created: {output_path}")


def create_logo(output_path: str, size: int = 200):
    """Create a simple placeholder logo."""
    # Create transparent image
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw circular background
    margin = 10
    circle_bbox = [margin, margin, size - margin, size - margin]
    draw.ellipse(circle_bbox, fill=(46, 204, 113, 230))  # Green with slight transparency
    
    # Draw "GF" text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()
    
    text = "GF"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 10
    
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    
    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'PNG')
    print(f"✅ Created: {output_path}")


def main():
    """Generate all placeholder assets."""
    print("🎨 Generating GoalFeed placeholder assets...\n")
    
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
    
    # Create fallback images
    sports = [
        ('fallback_football.jpg', 'Fútbol', '⚽'),
        ('fallback_nba.jpg', 'NBA', '🏀'),
        ('fallback_tennis.jpg', 'Tenis', '🎾'),
    ]
    
    for filename, sport_name, emoji in sports:
        create_fallback_image(
            os.path.join(assets_dir, filename),
            sport_name,
            emoji
        )
    
    # Create logo
    create_logo(os.path.join(assets_dir, 'logo.png'))
    
    print("\n✨ All assets created successfully!")
    print("\nNote: These are placeholder images. Replace them with your own")
    print("branded images for a better look.")


if __name__ == "__main__":
    main()
