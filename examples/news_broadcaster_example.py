"""Example of using the news broadcaster."""

from src.config import get_config
from src.data.news_fetcher import NewsFetcher
from src.notifications.telegram_notifier import TelegramNotifier
from src.notifications.news_broadcaster import NewsBroadcaster


def main():
    """Example of broadcasting news to Telegram."""
    # Load configuration
    config = get_config()
    
    # Create components
    news_fetcher = NewsFetcher(
        cache_dir=config.news.cache_dir,
        cache_ttl=config.news.cache_ttl,
        max_age_hours=config.news.max_age_hours,
        enabled_sources=config.news.sources
    )
    
    telegram = TelegramNotifier(
        bot_token=config.telegram.bot_token,
        chat_id=config.telegram.chat_id
    )
    
    broadcaster = NewsBroadcaster(
        news_fetcher=news_fetcher,
        telegram_notifier=telegram
    )
    
    print("="*80)
    print("NEWS BROADCASTER EXAMPLE")
    print("="*80)
    
    # Example 1: Broadcast latest news
    print("\n1. Broadcasting latest news (max 5 articles)...")
    sent = broadcaster.broadcast_news(max_articles=5)
    print(f"Sent {sent} articles")
    
    # Example 2: Broadcast news for specific stocks
    print("\n2. Broadcasting news for RELIANCE and TCS...")
    sent = broadcaster.broadcast_news(
        symbols=["RELIANCE", "TCS"],
        max_articles=3
    )
    print(f"Sent {sent} articles")
    
    # Example 3: Get statistics
    print("\n3. Broadcaster statistics:")
    stats = broadcaster.get_stats()
    print(f"Total articles sent: {stats['total_sent']}")
    print(f"History file: {stats['history_file']}")
    
    print("\n" + "="*80)
    print("Note: Only NEW articles are sent. Run again to see deduplication in action!")
    print("="*80)


if __name__ == "__main__":
    main()
