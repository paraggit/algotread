"""
News to Telegram broadcaster.

Fetches news from configured sources and sends to Telegram channel,
with deduplication to avoid repeating news.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Set

from loguru import logger

from src.config import get_config
from src.data.models import NewsArticle
from src.data.news_fetcher import NewsFetcher
from src.notifications.telegram_notifier import TelegramNotifier


class NewsBroadcaster:
    """Broadcasts news to Telegram with deduplication."""
    
    def __init__(
        self,
        news_fetcher: NewsFetcher,
        telegram_notifier: TelegramNotifier,
        sent_news_file: str = "data/sent_news.json"
    ):
        """
        Initialize news broadcaster.
        
        Args:
            news_fetcher: NewsFetcher instance
            telegram_notifier: TelegramNotifier instance
            sent_news_file: Path to file tracking sent news URLs
        """
        self.news_fetcher = news_fetcher
        self.telegram = telegram_notifier
        self.sent_news_file = Path(sent_news_file)
        self.sent_news_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load previously sent news URLs
        self.sent_urls: Set[str] = self._load_sent_urls()
    
    def _load_sent_urls(self) -> Set[str]:
        """Load previously sent news URLs from file."""
        if not self.sent_news_file.exists():
            return set()
        
        try:
            with open(self.sent_news_file, 'r') as f:
                data = json.load(f)
                return set(data.get('sent_urls', []))
        except Exception as e:
            logger.warning(f"Error loading sent news file: {e}")
            return set()
    
    def _save_sent_urls(self) -> None:
        """Save sent news URLs to file."""
        try:
            data = {
                'sent_urls': list(self.sent_urls),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.sent_news_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving sent news file: {e}")
    
    def _format_news_message(self, article: NewsArticle) -> str:
        """Format news article for Telegram."""
        # Emoji based on source
        source_emoji = {
            'economic_times': '📰',
            'google_news': '🌐',
            'nse_announcements': '📢',
            'moneycontrol': '💼'
        }
        
        emoji = source_emoji.get(article.source.value, '📰')
        
        # Format message
        message = f"{emoji} **{article.title}**\n\n"
        
        if article.summary:
            # Limit summary to 200 characters
            summary = article.summary[:200]
            if len(article.summary) > 200:
                summary += "..."
            message += f"{summary}\n\n"
        
        # Add symbols if available
        if article.symbols:
            symbols_str = ", ".join(f"#{symbol}" for symbol in article.symbols)
            message += f"📊 {symbols_str}\n\n"
        
        # Add source and link
        message += f"🔗 [{article.source.value.replace('_', ' ').title()}]({article.url})\n"
        message += f"🕐 {article.published_at.strftime('%Y-%m-%d %H:%M')}"
        
        return message
    
    def broadcast_news(
        self,
        symbols: List[str] = None,
        max_articles: int = 10,
        force_all: bool = False
    ) -> int:
        """
        Fetch and broadcast news to Telegram.
        
        Args:
            symbols: Optional list of symbols to filter by
            max_articles: Maximum number of articles to send
            force_all: If True, send all articles regardless of deduplication
            
        Returns:
            Number of articles sent
        """
        logger.info("Fetching news for broadcast...")
        
        # Fetch news
        articles = self.news_fetcher.fetch_news(
            symbols=symbols,
            max_articles_per_source=50
        )
        
        if not articles:
            logger.info("No news articles found")
            return 0
        
        logger.info(f"Found {len(articles)} articles")
        
        # Filter out already sent articles
        if not force_all:
            new_articles = [
                article for article in articles
                if article.url not in self.sent_urls
            ]
            logger.info(f"Filtered to {len(new_articles)} new articles")
        else:
            new_articles = articles
            logger.info("Force mode: sending all articles")
        
        if not new_articles:
            logger.info("No new articles to send")
            return 0
        
        # Limit to max_articles
        articles_to_send = new_articles[:max_articles]
        
        # Send each article
        sent_count = 0
        for article in articles_to_send:
            try:
                message = self._format_news_message(article)
                
                # Send to Telegram (using sync wrapper)
                success = self.telegram.send_message_sync(message, parse_mode='Markdown')
                
                if not success:
                    logger.warning(f"Failed to send article: {article.title[:50]}...")
                    continue
                
                # Mark as sent
                self.sent_urls.add(article.url)
                sent_count += 1
                
                logger.info(f"Sent: {article.title[:50]}...")
                
                # Small delay to avoid rate limiting
                import time
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error sending article: {e}")
                continue
        
        # Save sent URLs
        self._save_sent_urls()
        
        logger.info(f"Successfully sent {sent_count} articles to Telegram")
        return sent_count
    
    def clear_sent_history(self) -> None:
        """Clear the history of sent news (use with caution)."""
        self.sent_urls.clear()
        self._save_sent_urls()
        logger.info("Cleared sent news history")
    
    def get_stats(self) -> dict:
        """Get statistics about sent news."""
        return {
            'total_sent': len(self.sent_urls),
            'history_file': str(self.sent_news_file),
            'file_exists': self.sent_news_file.exists()
        }
