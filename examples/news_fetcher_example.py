"""Example usage of news fetcher."""

from src.config import get_config
from src.data.news_fetcher import NewsFetcher


def main():
    """Example of using news fetcher."""
    # Load configuration
    config = get_config()
    
    # Create news fetcher
    news_fetcher = NewsFetcher(
        cache_dir=config.news.cache_dir,
        cache_ttl=config.news.cache_ttl,
        max_age_hours=config.news.max_age_hours,
        enabled_sources=config.news.sources
    )
    
    print("="*80)
    print("NEWS FETCHER EXAMPLE")
    print("="*80)
    
    # Fetch general market news
    print("\n1. Fetching general market news...")
    news = news_fetcher.fetch_news(max_articles_per_source=10)
    
    print(f"\nFetched {len(news)} articles total")
    print("\nRecent headlines:")
    for i, article in enumerate(news[:10], 1):
        print(f"\n{i}. [{article.source.value}] {article.title}")
        print(f"   Published: {article.published_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"   URL: {article.url}")
    
    # Fetch news for specific stocks
    print("\n" + "="*80)
    print("\n2. Fetching news for specific stocks...")
    symbols = ["RELIANCE", "TCS", "INFY"]
    
    for symbol in symbols:
        stock_news = news_fetcher.fetch_stock_news(symbol, max_articles=5)
        print(f"\n{symbol}: {len(stock_news)} articles")
        
        for article in stock_news[:3]:
            print(f"  - {article.title[:80]}...")
    
    # Demonstrate caching
    print("\n" + "="*80)
    print("\n3. Demonstrating cache...")
    print("Fetching again (should use cache)...")
    
    import time
    start = time.time()
    cached_news = news_fetcher.fetch_news(max_articles_per_source=10)
    elapsed = time.time() - start
    
    print(f"Fetched {len(cached_news)} articles in {elapsed:.3f}s (from cache)")
    
    # Clear cache
    print("\n4. Clearing cache...")
    news_fetcher.clear_cache()
    print("Cache cleared!")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
