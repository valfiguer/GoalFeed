"""
Text utilities for GoalFeed.
String manipulation, cleaning, hashing, etc.
"""
import re
import hashlib
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Optional
import unicodedata


def normalize_title(title: str) -> str:
    """
    Normalize a title for comparison and deduplication.
    
    Args:
        title: Original title string
        
    Returns:
        Normalized title
    """
    if not title:
        return ""
    
    # Convert to lowercase
    text = title.lower()
    
    # Normalize unicode (convert accents etc.)
    text = unicodedata.normalize('NFKD', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common punctuation that doesn't affect meaning
    text = re.sub(r'["""\'\'\`\´]', '', text)
    text = re.sub(r'[:\-–—|/\\]', ' ', text)
    text = re.sub(r'[!?¡¿.,;]+', '', text)
    
    # Remove common prefixes/suffixes that news sites add
    prefixes_to_remove = [
        r'^(breaking|urgente|última hora|exclusive|exclusiva):?\s*',
        r'^(oficial|official):?\s*',
        r'^(video|vídeo|foto|gallery):?\s*',
        r'^(live|en vivo|directo):?\s*',
    ]
    for prefix in prefixes_to_remove:
        text = re.sub(prefix, '', text, flags=re.IGNORECASE)
    
    # Clean up
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    
    return text


def canonicalize_url(url: str) -> str:
    """
    Canonicalize a URL by removing tracking parameters.
    
    Args:
        url: Original URL
        
    Returns:
        Canonical URL without tracking params
    """
    if not url:
        return ""
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Parse query parameters
    params = parse_qs(parsed.query, keep_blank_values=False)
    
    # Parameters to remove (tracking, session, etc.)
    params_to_remove = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'utm_id', 'utm_cid', 'utm_reader', 'utm_name', 'utm_social-type',
        'fbclid', 'gclid', 'gclsrc', 'dclid',
        'msclkid', 'zanpid', 'igshid',
        'ref', 'source', 'from', 's', 'share',
        'ncid', 'sr_share', 'ns_campaign', 'ns_mchannel',
        'mc_cid', 'mc_eid', 'mkt_tok',
        'oly_enc_id', 'oly_anon_id', 'vero_id',
        'spm', 'scm', '_t', 'track'
    }
    
    # Filter out tracking params
    filtered_params = {
        k: v for k, v in params.items()
        if k.lower() not in params_to_remove
    }
    
    # Rebuild query string
    new_query = urlencode(filtered_params, doseq=True)
    
    # Rebuild URL
    canonical = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip('/'),
        parsed.params,
        new_query,
        ''  # Remove fragment
    ))
    
    return canonical


def get_domain(url: str) -> str:
    """
    Extract the domain from a URL.
    
    Args:
        url: Full URL
        
    Returns:
        Domain (e.g., 'marca.com')
    """
    if not url:
        return ""
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    except Exception:
        return ""


def generate_article_hash(title: str, domain: str, date_bucket: str) -> str:
    """
    Generate a hash for article deduplication.
    
    Args:
        title: Normalized article title
        domain: Source domain
        date_bucket: Date bucket string
        
    Returns:
        SHA256 hash string
    """
    content = f"{title}|{domain}|{date_bucket}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    # Try to truncate at word boundary
    truncated = text[:max_length - len(suffix)]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.7:
        truncated = truncated[:last_space]
    
    return truncated.rstrip() + suffix


def clean_html(text: str) -> str:
    """
    Remove HTML tags from text.
    
    Args:
        text: Text possibly containing HTML
        
    Returns:
        Clean text
    """
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decode common HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&apos;', "'")
    text = text.replace('&mdash;', '—')
    text = text.replace('&ndash;', '–')
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def extract_first_sentence(text: str, max_length: int = 200) -> str:
    """
    Extract the first sentence from text.
    
    Args:
        text: Source text
        max_length: Maximum length
        
    Returns:
        First sentence
    """
    if not text:
        return ""
    
    # Clean HTML first
    text = clean_html(text)
    
    # Find first sentence ending
    sentence_endings = re.finditer(r'[.!?]+\s', text)
    
    for match in sentence_endings:
        end_pos = match.end()
        if 20 < end_pos <= max_length:
            return text[:end_pos].strip()
    
    # No sentence found, truncate
    return truncate_text(text, max_length)


def extract_keywords(text: str, min_length: int = 3) -> list[str]:
    """
    Extract keywords from text.
    
    Args:
        text: Source text
        min_length: Minimum keyword length
        
    Returns:
        List of keywords
    """
    if not text:
        return []
    
    # Clean and lowercase
    text = clean_html(text).lower()
    
    # Extract words
    words = re.findall(r'\b[a-záéíóúñü]+\b', text)
    
    # Filter by length
    keywords = [w for w in words if len(w) >= min_length]
    
    return list(set(keywords))


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL.
    
    Args:
        url: String to check
        
    Returns:
        True if valid URL
    """
    if not url:
        return False
    
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


def make_telegram_safe(text: str, max_length: int = 1024) -> str:
    """
    Make text safe for Telegram captions.
    
    Args:
        text: Original text
        max_length: Maximum caption length (Telegram limit is 1024)
        
    Returns:
        Telegram-safe text
    """
    if not text:
        return ""
    
    # Remove or replace problematic characters
    # Telegram supports most Unicode, but let's clean up
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    
    # Remove null bytes and other control characters (except newlines)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Truncate if needed
    if len(text) > max_length:
        text = truncate_text(text, max_length - 3)
    
    return text
