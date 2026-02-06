"""
Telegram Publisher module for GoalFeed.
Handles sending messages to Telegram channel using aiogram.
"""
import logging
import asyncio
from typing import Optional, List
from io import BytesIO

from aiogram import Bot
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.exceptions import TelegramAPIError

from config import get_config

logger = logging.getLogger(__name__)


class TelegramPublisher:
    """
    Publishes content to Telegram channel.
    """
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize publisher.
        
        Args:
            bot_token: Telegram bot token (uses config if None)
            chat_id: Channel chat ID (uses config if None)
        """
        config = get_config()
        
        self.bot_token = bot_token or config.bot_token
        self.chat_id = chat_id or config.channel_chat_id
        
        if not self.bot_token:
            raise ValueError("Bot token is required")
        if not self.chat_id:
            raise ValueError("Channel chat ID is required")
        
        # Don't create bot instance here - create fresh for each operation
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    def _create_bot(self) -> Bot:
        """Create a fresh bot instance."""
        return Bot(token=self.bot_token)
    
    def _create_source_keyboard(
        self,
        source_url: str,
        source_name: Optional[str] = None
    ) -> InlineKeyboardMarkup:
        """
        Create inline keyboard with source link.
        
        Args:
            source_url: URL to the source article
            source_name: Name of the source
            
        Returns:
            InlineKeyboardMarkup
        """
        button_text = f"📖 Leer en {source_name}" if source_name else "📖 Leer fuente"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=button_text, url=source_url)]
            ]
        )
        
        return keyboard
    
    def _create_multi_source_keyboard(
        self,
        sources: List[tuple]  # List of (url, name)
    ) -> InlineKeyboardMarkup:
        """
        Create inline keyboard with multiple source links.
        
        Args:
            sources: List of (url, name) tuples
            
        Returns:
            InlineKeyboardMarkup
        """
        buttons = []
        
        for i, (url, name) in enumerate(sources[:5], 1):  # Max 5 buttons
            button_text = f"📖 {i}. {name}" if name else f"📖 Fuente {i}"
            buttons.append([InlineKeyboardButton(text=button_text, url=url)])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    async def send_photo_async(
        self,
        image_data: bytes,
        caption: str,
        source_url: Optional[str] = None,
        source_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Send a photo with caption to the channel.
        
        Args:
            image_data: Image bytes
            caption: Message caption
            source_url: URL for "Read source" button
            source_name: Name of the source
            
        Returns:
            Message ID or None on failure
        """
        bot = self._create_bot()
        try:
            for attempt in range(self.max_retries):
                try:
                    # Create photo input
                    photo = BufferedInputFile(
                        file=image_data,
                        filename="image.jpg"
                    )
                    
                    # Create keyboard if source URL provided
                    reply_markup = None
                    if source_url:
                        reply_markup = self._create_source_keyboard(source_url, source_name)
                    
                    # Send photo with HTML formatting
                    message = await bot.send_photo(
                        chat_id=self.chat_id,
                        photo=photo,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode="HTML"  # Enable bold, italic, etc.
                    )
                    
                    logger.info(f"Published photo message: {message.message_id}")
                    return message.message_id
                    
                except TelegramAPIError as e:
                    logger.error(f"Telegram API error (attempt {attempt + 1}): {e}")
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    else:
                        return None
                        
                except Exception as e:
                    logger.error(f"Error sending photo (attempt {attempt + 1}): {e}")
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    else:
                        return None
            
            return None
        finally:
            await bot.session.close()
    
    async def send_digest_async(
        self,
        image_data: bytes,
        caption: str,
        sources: List[tuple]  # List of (url, name)
    ) -> Optional[int]:
        """
        Send a digest photo with multiple source links.
        
        Args:
            image_data: Image bytes
            caption: Digest caption
            sources: List of (url, name) tuples
            
        Returns:
            Message ID or None on failure
        """
        bot = self._create_bot()
        try:
            for attempt in range(self.max_retries):
                try:
                    # Create photo input
                    photo = BufferedInputFile(
                        file=image_data,
                        filename="digest.jpg"
                    )
                    
                    # For MVP, use single button to first source
                    # (Multiple buttons can be added later)
                    reply_markup = None
                    if sources:
                        # Use first source for main button
                        url, name = sources[0]
                        reply_markup = self._create_source_keyboard(url, name)
                    
                    # Send photo with HTML formatting
                    message = await bot.send_photo(
                        chat_id=self.chat_id,
                        photo=photo,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode="HTML"  # Enable bold, italic, etc.
                    )
                    
                    logger.info(f"Published digest message: {message.message_id}")
                    return message.message_id
                    
                except TelegramAPIError as e:
                    logger.error(f"Telegram API error (attempt {attempt + 1}): {e}")
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    else:
                        return None
                        
                except Exception as e:
                    logger.error(f"Error sending digest (attempt {attempt + 1}): {e}")
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    else:
                        return None
            
            return None
        finally:
            await bot.session.close()
    
    def send_photo(
        self,
        image_data: bytes,
        caption: str,
        source_url: Optional[str] = None,
        source_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Synchronous wrapper for send_photo_async.
        
        Args:
            image_data: Image bytes
            caption: Message caption
            source_url: URL for "Read source" button
            source_name: Name of the source
            
        Returns:
            Message ID or None on failure
        """
        # Create a fresh event loop for this call
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.send_photo_async(image_data, caption, source_url, source_name)
            )
        finally:
            loop.close()
    
    def send_digest(
        self,
        image_data: bytes,
        caption: str,
        sources: List[tuple]
    ) -> Optional[int]:
        """
        Synchronous wrapper for send_digest_async.
        
        Args:
            image_data: Image bytes
            caption: Digest caption
            sources: List of (url, name) tuples
            
        Returns:
            Message ID or None on failure
        """
        # Create a fresh event loop for this call
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.send_digest_async(image_data, caption, sources)
            )
        finally:
            loop.close()


# Singleton instance
_publisher_instance: Optional[TelegramPublisher] = None


def get_publisher() -> TelegramPublisher:
    """
    Get or create the global TelegramPublisher instance.
    
    Returns:
        TelegramPublisher instance
    """
    global _publisher_instance
    
    if _publisher_instance is None:
        _publisher_instance = TelegramPublisher()
    
    return _publisher_instance


async def publish_article_async(
    image_data: bytes,
    caption: str,
    source_url: str,
    source_name: Optional[str] = None
) -> Optional[int]:
    """
    Convenience function to publish an article.
    
    Args:
        image_data: Image bytes
        caption: Article caption
        source_url: URL to source
        source_name: Source name
        
    Returns:
        Message ID or None
    """
    publisher = get_publisher()
    return await publisher.send_photo_async(
        image_data, caption, source_url, source_name
    )


def publish_article(
    image_data: bytes,
    caption: str,
    source_url: str,
    source_name: Optional[str] = None
) -> Optional[int]:
    """
    Synchronous convenience function to publish an article.
    
    Args:
        image_data: Image bytes
        caption: Article caption
        source_url: URL to source
        source_name: Source name
        
    Returns:
        Message ID or None
    """
    publisher = get_publisher()
    return publisher.send_photo(
        image_data, caption, source_url, source_name
    )


async def publish_digest_async(
    image_data: bytes,
    caption: str,
    sources: List[tuple]
) -> Optional[int]:
    """
    Convenience function to publish a digest.
    
    Args:
        image_data: Image bytes
        caption: Digest caption
        sources: List of (url, name) tuples
        
    Returns:
        Message ID or None
    """
    publisher = get_publisher()
    return await publisher.send_digest_async(image_data, caption, sources)


def publish_digest(
    image_data: bytes,
    caption: str,
    sources: List[tuple]
) -> Optional[int]:
    """
    Synchronous convenience function to publish a digest.
    
    Args:
        image_data: Image bytes
        caption: Digest caption
        sources: List of (url, name) tuples
        
    Returns:
        Message ID or None
    """
    publisher = get_publisher()
    return publisher.send_digest(image_data, caption, sources)
