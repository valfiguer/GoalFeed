"""
Watermark module for GoalFeed.
Adds logo watermark to images.
"""
import logging
import os
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image

from config import get_config

logger = logging.getLogger(__name__)


def load_logo(logo_path: Optional[str] = None) -> Optional[Image.Image]:
    """
    Load the logo image for watermarking.
    
    Args:
        logo_path: Path to logo file (uses config if None)
        
    Returns:
        PIL Image in RGBA mode or None
    """
    config = get_config()
    logo_path = logo_path or config.watermark.path
    
    # Handle relative paths
    if not os.path.isabs(logo_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(base_dir, logo_path)
    
    if not os.path.exists(logo_path):
        logger.warning(f"Logo file not found: {logo_path}")
        return None
    
    try:
        logo = Image.open(logo_path)
        
        # Ensure RGBA mode for transparency
        if logo.mode != 'RGBA':
            logo = logo.convert('RGBA')
        
        return logo
        
    except Exception as e:
        logger.error(f"Error loading logo: {e}")
        return None


def apply_opacity(logo: Image.Image, opacity: float = 0.65) -> Image.Image:
    """
    Apply opacity to a logo image.
    
    Args:
        logo: PIL Image in RGBA mode
        opacity: Opacity value (0.0 to 1.0)
        
    Returns:
        Logo with adjusted opacity
    """
    # Ensure RGBA
    if logo.mode != 'RGBA':
        logo = logo.convert('RGBA')
    
    # Split channels
    r, g, b, a = logo.split()
    
    # Apply opacity to alpha channel
    a = a.point(lambda x: int(x * opacity))
    
    # Merge back
    logo = Image.merge('RGBA', (r, g, b, a))
    
    return logo


def calculate_watermark_position(
    image_size: Tuple[int, int],
    logo_size: Tuple[int, int],
    margin_ratio: float = 0.04
) -> Tuple[int, int]:
    """
    Calculate watermark position (bottom-right corner).
    
    Args:
        image_size: (width, height) of base image
        logo_size: (width, height) of logo
        margin_ratio: Margin as ratio of image width
        
    Returns:
        (x, y) position for watermark
    """
    img_width, img_height = image_size
    logo_width, logo_height = logo_size
    
    margin = int(img_width * margin_ratio)
    
    x = img_width - logo_width - margin
    y = img_height - logo_height - margin
    
    return (x, y)


def scale_logo(
    logo: Image.Image,
    image_width: int,
    size_ratio: float = 0.16
) -> Image.Image:
    """
    Scale logo relative to image width.
    
    Args:
        logo: Logo PIL Image
        image_width: Width of base image
        size_ratio: Logo width as ratio of image width
        
    Returns:
        Scaled logo
    """
    target_width = int(image_width * size_ratio)
    
    # Calculate height maintaining aspect ratio
    logo_width, logo_height = logo.size
    ratio = target_width / logo_width
    target_height = int(logo_height * ratio)
    
    # Resize with high quality
    scaled = logo.resize(
        (target_width, target_height),
        Image.Resampling.LANCZOS
    )
    
    return scaled


def add_watermark(
    image_data: bytes,
    logo_path: Optional[str] = None,
    size_ratio: Optional[float] = None,
    margin_ratio: Optional[float] = None,
    opacity: Optional[float] = None
) -> Optional[bytes]:
    """
    Add watermark logo to an image.
    
    Args:
        image_data: Base image bytes
        logo_path: Path to logo file
        size_ratio: Logo size as ratio of image width
        margin_ratio: Margin as ratio of image width
        opacity: Logo opacity (0.0 to 1.0)
        
    Returns:
        Image bytes with watermark or None on error
    """
    config = get_config()
    
    # Use config values if not provided
    size_ratio = size_ratio or config.watermark.size_ratio
    margin_ratio = margin_ratio or config.watermark.margin_ratio
    opacity = opacity or config.watermark.opacity
    
    try:
        # Load base image
        base_image = Image.open(BytesIO(image_data))
        
        # Convert to RGBA for compositing
        if base_image.mode != 'RGBA':
            base_image = base_image.convert('RGBA')
        
        # Load and prepare logo
        logo = load_logo(logo_path)
        if logo is None:
            logger.warning("No logo available, returning image without watermark")
            # Return original as JPEG
            output = BytesIO()
            rgb_image = base_image.convert('RGB')
            rgb_image.save(output, format='JPEG', quality=85)
            output.seek(0)
            return output.getvalue()
        
        # Scale logo
        logo = scale_logo(logo, base_image.width, size_ratio)
        
        # Apply opacity
        logo = apply_opacity(logo, opacity)
        
        # Calculate position
        position = calculate_watermark_position(
            base_image.size,
            logo.size,
            margin_ratio
        )
        
        # Composite images
        # Create a copy to avoid modifying original
        result = base_image.copy()
        result.paste(logo, position, logo)  # Use logo as mask for transparency
        
        # Convert to RGB for JPEG output
        result = result.convert('RGB')
        
        # Save to bytes
        output = BytesIO()
        result.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        logger.debug(f"Added watermark to image")
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error adding watermark: {e}")
        return None


def process_image_with_watermark(
    image_data: bytes,
    target_width: Optional[int] = None
) -> Optional[bytes]:
    """
    Full image processing pipeline: resize and add watermark.
    
    Args:
        image_data: Raw image bytes
        target_width: Target width for resizing
        
    Returns:
        Processed image bytes or None
    """
    from media.image_prep import prepare_image
    
    # First prepare (resize, convert)
    prepared = prepare_image(image_data, target_width)
    
    if prepared is None:
        return None
    
    # Then add watermark
    watermarked = add_watermark(prepared)
    
    return watermarked
