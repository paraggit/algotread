#!/usr/bin/env python3
"""
Command-line tool to fetch news and broadcast to Telegram.

Usage:
    uv run -m scripts.broadcast_news --help
    uv run -m scripts.broadcast_news
    uv run -m scripts.broadcast_news --symbols RELIANCE,TCS
    uv run -m scripts.broadcast_news --max 5
    uv run -m scripts.broadcast_news --force  # Send all, ignore deduplication
    uv run -m scripts.broadcast_news --clear-history  # Clear sent news history
"""

import argparse
import os
import sys
from pathlib import Path

from loguru import logger

from src.config import get_config
from src.data.news_fetcher import NewsFetcher
from src.notifications.telegram_notifier import TelegramNotifier
from src.notifications.news_broadcaster import NewsBroadcaster


def setup_logging():
    """Setup logging configuration."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch news and broadcast to Telegram channel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Broadcast latest news
  uv run -m scripts.broadcast_news
  
  # Broadcast news for specific stocks
  uv run -m scripts.broadcast_news --symbols RELIANCE,TCS,INFY
  
  # Limit to 5 articles
  uv run -m scripts.broadcast_news --max 5
  
  # Force send all articles (ignore deduplication)
  uv run -m scripts.broadcast_news --force
  
  # Clear sent news history
  uv run -m scripts.broadcast_news --clear-history
  
  # Get statistics
  uv run -m scripts.broadcast_news --stats
        """
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        help='Comma-separated list of stock symbols to filter news'
    )
    
    parser.add_argument(
        '--max',
        type=int,
        default=10,
        help='Maximum number of articles to send (default: 10)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Send all articles, ignoring deduplication'
    )
    
    parser.add_argument(
        '--clear-history',
        action='store_true',
        help='Clear the history of sent news'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics about sent news'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    if args.verbose:
        logger.remove()
        logger.add(
            sys.stderr,
            level="DEBUG",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <level>{message}</level>"
        )
    
    logger.info("=" * 60)
    logger.info("News to Telegram Broadcaster")
    logger.info("=" * 60)
    
    # Load configuration
    try:
        config = get_config()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        logger.error("Please ensure .env file is properly configured")
        sys.exit(1)
    
    # Check if news is enabled
    if not config.news.enabled:
        logger.error("News fetching is disabled in configuration")
        logger.error("Set NEWS_ENABLED=true in .env file")
        sys.exit(1)
    
    # Check if Telegram is configured
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    telegram_enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
    
    if not telegram_enabled:
        logger.error("Telegram notifications are disabled in configuration")
        logger.error("Set TELEGRAM_ENABLED=true in .env file")
        sys.exit(1)
    
    if not telegram_bot_token or not telegram_chat_id:
        logger.error("Telegram credentials not configured")
        logger.error("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file")
        sys.exit(1)
    
    # Initialize components
    logger.info("Initializing components...")
    
    try:
        # News fetcher
        news_fetcher = NewsFetcher(
            cache_dir=config.news.cache_dir,
            cache_ttl=config.news.cache_ttl,
            max_age_hours=config.news.max_age_hours,
            enabled_sources=config.news.sources
        )
        
        # Telegram notifier
        telegram = TelegramNotifier(
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id
        )
        
        # News broadcaster
        broadcaster = NewsBroadcaster(
            news_fetcher=news_fetcher,
            telegram_notifier=telegram
        )
        
        logger.info("Components initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        sys.exit(1)
    
    # Handle commands
    if args.clear_history:
        logger.warning("Clearing sent news history...")
        broadcaster.clear_sent_history()
        logger.info("History cleared successfully")
        return
    
    if args.stats:
        stats = broadcaster.get_stats()
        logger.info("=" * 60)
        logger.info("News Broadcaster Statistics")
        logger.info("=" * 60)
        logger.info(f"Total articles sent: {stats['total_sent']}")
        logger.info(f"History file: {stats['history_file']}")
        logger.info(f"File exists: {stats['file_exists']}")
        logger.info("=" * 60)
        return
    
    # Parse symbols if provided
    symbols = None
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
        logger.info(f"Filtering news for symbols: {', '.join(symbols)}")
    
    # Broadcast news
    logger.info("=" * 60)
    
    try:
        sent_count = broadcaster.broadcast_news(
            symbols=symbols,
            max_articles=args.max,
            force_all=args.force
        )
        
        logger.info("=" * 60)
        logger.info(f"✅ Successfully sent {sent_count} articles to Telegram")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error broadcasting news: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()
