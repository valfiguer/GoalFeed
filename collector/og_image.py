"""
OpenGraph Image Extractor for GoalFeed.
Scrapes og:image meta tags from article URLs.
"""
import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import get_config

logger = logging.getLogger(__name__)


def extract_og_image(url: str, timeout: Optional[int] = None) -> Optional[str]:
    """
    Extract OpenGraph image from an article URL.
    
    Args:
        url: Article URL to scrape
        timeout: Request timeout in seconds
        
    Returns:
        Image URL or None if not found
    """
    config = get_config()
    timeout = timeout or config.request_timeout
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; GoalFeed/1.0; +https://goalfeed.bot)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        }
        
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Try og:image first (most common)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image['content']
            return _resolve_url(url, image_url)
        
        # Try og:image:url
        og_image_url = soup.find('meta', property='og:image:url')
        if og_image_url and og_image_url.get('content'):
            image_url = og_image_url['content']
            return _resolve_url(url, image_url)
        
        # Try twitter:image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            image_url = twitter_image['content']
            return _resolve_url(url, image_url)
        
        # Try twitter:image:src
        twitter_image_src = soup.find('meta', attrs={'name': 'twitter:image:src'})
        if twitter_image_src and twitter_image_src.get('content'):
            image_url = twitter_image_src['content']
            return _resolve_url(url, image_url)
        
        # Try itemprop="image"
        itemprop_image = soup.find('meta', attrs={'itemprop': 'image'})
        if itemprop_image and itemprop_image.get('content'):
            image_url = itemprop_image['content']
            return _resolve_url(url, image_url)
        
        # Try link rel="image_src"
        link_image = soup.find('link', rel='image_src')
        if link_image and link_image.get('href'):
            image_url = link_image['href']
            return _resolve_url(url, image_url)
        
        logger.debug(f"No OG image found for: {url}")
        return None
        
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout extracting OG image from: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request error extracting OG image from {url}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error extracting OG image from {url}: {e}")
        return None


def _resolve_url(base_url: str, image_url: str) -> str:
    """
    Resolve a potentially relative image URL to absolute.
    
    Args:
        base_url: Base page URL
        image_url: Image URL (possibly relative)
        
    Returns:
        Absolute image URL
    """
    if image_url.startswith(('http://', 'https://')):
        return image_url
    
    if image_url.startswith('//'):
        # Protocol-relative URL
        return 'https:' + image_url
    
    # Relative URL - join with base
    return urljoin(base_url, image_url)


def validate_image_url(url: str, timeout: int = 5) -> bool:
    """
    Validate that an image URL is accessible.
    
    Args:
        url: Image URL to check
        timeout: Request timeout
        
    Returns:
        True if image is accessible
    """
    try:
        headers = {
            'User-Agent': 'GoalFeed/1.0 (Image Validator)'
        }
        
        response = requests.head(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True
        )
        
        if response.status_code != 200:
            return False
        
        # Check content type
        content_type = response.headers.get('Content-Type', '').lower()
        valid_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
        
        return any(t in content_type for t in valid_types)
        
    except Exception:
        return False


def get_best_image(
    rss_image_url: Optional[str],
    article_url: str,
    fallback_path: str
) -> str:
    """
    Get the best available image for an article.
    
    Priority:
    1. RSS image URL (if valid)
    2. OpenGraph image from article
    3. Fallback image by sport
    
    Args:
        rss_image_url: Image URL from RSS feed
        article_url: Article URL for OG scraping
        fallback_path: Path to fallback image
        
    Returns:
        Best available image URL or path
    """
    # Try RSS image first
    if rss_image_url:
        if validate_image_url(rss_image_url):
            logger.debug(f"Using RSS image: {rss_image_url}")
            return rss_image_url
        else:
            logger.debug(f"RSS image invalid: {rss_image_url}")
    
    # Try OpenGraph image
    og_image = extract_og_image(article_url)
    if og_image and validate_image_url(og_image):
        logger.debug(f"Using OG image: {og_image}")
        return og_image
    
    # Fall back to local image
    logger.debug(f"Using fallback image: {fallback_path}")
    return fallback_path
