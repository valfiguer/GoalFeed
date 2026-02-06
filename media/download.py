"""
Image download module for GoalFeed.
Downloads images from URLs with proper error handling.
"""
import logging
import os
import tempfile
from typing import Optional, Tuple
from pathlib import Path
from io import BytesIO

import requests

from config import get_config

logger = logging.getLogger(__name__)


def download_image(
    url: str,
    timeout: Optional[int] = None,
    max_size_mb: int = 10
) -> Optional[bytes]:
    """
    Download an image from URL.
    
    Args:
        url: Image URL
        timeout: Request timeout in seconds
        max_size_mb: Maximum file size in MB
        
    Returns:
        Image bytes or None if download failed
    """
    config = get_config()
    timeout = timeout or config.request_timeout
    max_size_bytes = max_size_mb * 1024 * 1024
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; GoalFeed/1.0)',
            'Accept': 'image/*'
        }
        
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            stream=True,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('Content-Type', '').lower()
        valid_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
        
        if not any(t in content_type for t in valid_types):
            # Try to infer from URL
            url_lower = url.lower()
            if not any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                logger.warning(f"Invalid content type: {content_type}")
                return None
        
        # Check content length
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > max_size_bytes:
            logger.warning(f"Image too large: {content_length} bytes")
            return None
        
        # Download with size limit
        chunks = []
        total_size = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            chunks.append(chunk)
            total_size += len(chunk)
            
            if total_size > max_size_bytes:
                logger.warning(f"Image exceeded max size during download")
                return None
        
        image_data = b''.join(chunks)
        
        logger.debug(f"Downloaded image: {len(image_data)} bytes from {url[:50]}")
        return image_data
        
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout downloading image: {url[:50]}")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error downloading image from {url[:50]}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading image: {e}")
        return None


def download_to_file(
    url: str,
    output_path: str,
    timeout: Optional[int] = None
) -> bool:
    """
    Download an image to a file.
    
    Args:
        url: Image URL
        output_path: Output file path
        timeout: Request timeout
        
    Returns:
        True if successful
    """
    image_data = download_image(url, timeout)
    
    if not image_data:
        return False
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(image_data)
        
        logger.debug(f"Saved image to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving image to {output_path}: {e}")
        return False


def download_to_temp(url: str, timeout: Optional[int] = None) -> Optional[str]:
    """
    Download an image to a temporary file.
    
    Args:
        url: Image URL
        timeout: Request timeout
        
    Returns:
        Temporary file path or None
    """
    image_data = download_image(url, timeout)
    
    if not image_data:
        return None
    
    try:
        # Determine extension from URL
        url_lower = url.lower()
        if '.png' in url_lower:
            suffix = '.png'
        elif '.gif' in url_lower:
            suffix = '.gif'
        elif '.webp' in url_lower:
            suffix = '.webp'
        else:
            suffix = '.jpg'
        
        # Create temp file
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix='goalfeed_')
        
        with os.fdopen(fd, 'wb') as f:
            f.write(image_data)
        
        logger.debug(f"Saved image to temp: {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"Error creating temp file: {e}")
        return None


def download_to_bytesio(url: str, timeout: Optional[int] = None) -> Optional[BytesIO]:
    """
    Download an image to a BytesIO object.
    
    Args:
        url: Image URL
        timeout: Request timeout
        
    Returns:
        BytesIO object or None
    """
    image_data = download_image(url, timeout)
    
    if not image_data:
        return None
    
    return BytesIO(image_data)


def get_image_from_source(
    image_url: Optional[str],
    fallback_path: str
) -> Tuple[bytes, str]:
    """
    Get image data from URL or fallback to local file.
    
    Args:
        image_url: Remote image URL (can be None)
        fallback_path: Local fallback image path
        
    Returns:
        Tuple of (image_bytes, source_type)
        source_type is 'remote' or 'fallback'
    """
    # Try remote URL first
    if image_url:
        image_data = download_image(image_url)
        if image_data:
            return image_data, 'remote'
    
    # Fall back to local file
    try:
        # Handle relative paths
        if not os.path.isabs(fallback_path):
            # Look in project directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            fallback_path = os.path.join(base_dir, fallback_path)
        
        if os.path.exists(fallback_path):
            with open(fallback_path, 'rb') as f:
                image_data = f.read()
            return image_data, 'fallback'
        else:
            logger.warning(f"Fallback image not found: {fallback_path}")
            
    except Exception as e:
        logger.error(f"Error reading fallback image: {e}")
    
    # Return empty bytes if all else fails
    return b'', 'none'
