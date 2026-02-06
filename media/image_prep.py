"""
Image preparation module for GoalFeed.
Resizes and prepares images for Telegram.
"""
import logging
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image

from config import get_config

logger = logging.getLogger(__name__)


def load_image(image_data: bytes) -> Optional[Image.Image]:
    """
    Load image from bytes.
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        PIL Image or None
    """
    try:
        img = Image.open(BytesIO(image_data))
        return img
    except Exception as e:
        logger.error(f"Error loading image: {e}")
        return None


def convert_to_rgb(img: Image.Image) -> Image.Image:
    """
    Convert image to RGB mode (required for JPEG).
    
    Args:
        img: PIL Image
        
    Returns:
        RGB Image
    """
    if img.mode == 'RGBA':
        # Create white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        return background
    elif img.mode != 'RGB':
        return img.convert('RGB')
    return img


def resize_image(
    img: Image.Image,
    target_width: Optional[int] = None,
    max_height: Optional[int] = None
) -> Image.Image:
    """
    Resize image while maintaining aspect ratio.
    
    Args:
        img: PIL Image
        target_width: Target width (uses config default if None)
        max_height: Maximum height (optional)
        
    Returns:
        Resized Image
    """
    config = get_config()
    target_width = target_width or config.image_width
    
    # Calculate new dimensions
    original_width, original_height = img.size
    
    # Only resize if larger than target
    if original_width <= target_width:
        return img
    
    ratio = target_width / original_width
    new_height = int(original_height * ratio)
    
    # Check max height
    if max_height and new_height > max_height:
        ratio = max_height / original_height
        target_width = int(original_width * ratio)
        new_height = max_height
    
    # Resize with high-quality resampling
    resized = img.resize(
        (target_width, new_height),
        Image.Resampling.LANCZOS
    )
    
    logger.debug(
        f"Resized image: {original_width}x{original_height} -> "
        f"{target_width}x{new_height}"
    )
    
    return resized


def prepare_image(
    image_data: bytes,
    target_width: Optional[int] = None,
    max_height: int = 2000
) -> Optional[bytes]:
    """
    Prepare image for Telegram (resize, convert, optimize).
    
    Args:
        image_data: Raw image bytes
        target_width: Target width (uses config if None)
        max_height: Maximum height
        
    Returns:
        Processed image bytes (JPEG) or None
    """
    # Load image
    img = load_image(image_data)
    if img is None:
        return None
    
    try:
        # Resize
        img = resize_image(img, target_width, max_height)
        
        # Convert to RGB
        img = convert_to_rgb(img)
        
        # Save to bytes
        output = BytesIO()
        img.save(
            output,
            format='JPEG',
            quality=85,
            optimize=True
        )
        output.seek(0)
        
        result = output.getvalue()
        logger.debug(f"Prepared image: {len(result)} bytes")
        
        return result
        
    except Exception as e:
        logger.error(f"Error preparing image: {e}")
        return None


def get_image_dimensions(image_data: bytes) -> Tuple[int, int]:
    """
    Get dimensions of an image.
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Tuple of (width, height) or (0, 0) on error
    """
    img = load_image(image_data)
    if img is None:
        return (0, 0)
    return img.size


def create_placeholder_image(
    width: int = 1280,
    height: int = 720,
    color: Tuple[int, int, int] = (30, 30, 30),
    text: Optional[str] = None
) -> bytes:
    """
    Create a placeholder image.
    
    Args:
        width: Image width
        height: Image height
        color: Background RGB color
        text: Optional text to display
        
    Returns:
        Image bytes (JPEG)
    """
    from PIL import ImageDraw
    
    # Create image
    img = Image.new('RGB', (width, height), color)
    
    # Add text if provided
    if text:
        draw = ImageDraw.Draw(img)
        # Use default font (no external font needed)
        text_bbox = draw.textbbox((0, 0), text)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), text, fill=(200, 200, 200))
    
    # Save to bytes
    output = BytesIO()
    img.save(output, format='JPEG', quality=85)
    output.seek(0)
    
    return output.getvalue()
