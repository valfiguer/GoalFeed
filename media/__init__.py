"""Media module for GoalFeed."""
from .download import (
    download_image,
    download_to_file,
    download_to_temp,
    download_to_bytesio,
    get_image_from_source
)
from .image_prep import (
    load_image,
    convert_to_rgb,
    resize_image,
    prepare_image,
    get_image_dimensions,
    create_placeholder_image
)
from .watermark import (
    load_logo,
    apply_opacity,
    add_watermark,
    process_image_with_watermark
)

__all__ = [
    # Download
    'download_image',
    'download_to_file',
    'download_to_temp',
    'download_to_bytesio',
    'get_image_from_source',
    # Image prep
    'load_image',
    'convert_to_rgb',
    'resize_image',
    'prepare_image',
    'get_image_dimensions',
    'create_placeholder_image',
    # Watermark
    'load_logo',
    'apply_opacity',
    'add_watermark',
    'process_image_with_watermark'
]
