"""Editorial module for GoalFeed."""
from .copywriter import (
    Copywriter,
    get_copywriter,
    generate_caption,
    generate_digest_caption
)

__all__ = [
    'Copywriter',
    'get_copywriter',
    'generate_caption',
    'generate_digest_caption'
]
