# News Integration Guide

## Overview

The AlgoTread trading system now includes comprehensive news integration to enhance stock research and dynamic watchlist generation. News data is fetched from multiple public sources and used **ONLY** for advisory purposes - it does NOT directly trigger trades.

> [!IMPORTANT]
> **Data Source Compliance**: All news sources use legitimate, publicly available data.
> See [DATA_SOURCE_COMPLIANCE.md](DATA_SOURCE_COMPLIANCE.md) for detailed information about:
> - Legitimacy of each data source
> - Terms of service compliance
> - How to disable sources if needed
> - Best practices for respectful data usage

## News Sources

The system supports the following news sources:

### 1. Economic Times RSS
- **Source**: Economic Times RSS feeds
- **Coverage**: Indian stock market news, company announcements
- **Update Frequency**: Real-time via RSS
- **Cost**: Free

### 2. Google News RSS
- **Source**: Google News search results
- **Coverage**: Global and Indian market news
- **Update Frequency**: Real-time via RSS
- **Cost**: Free

### 3. NSE Announcements
- **Source**: NSE corporate announcements API
- **Coverage**: Official company announcements, corporate actions
- **Update Frequency**: Real-time
- **Cost**: Free
- **Note**: May require specific headers to avoid blocking

## Configuration

Add the following to your `.env` file:

```bash
# News Configuration
NEWS_ENABLED=true
NEWS_SOURCES=economic_times,google_news,nse_announcements
NEWS_CACHE_DIR=data/news_cache
NEWS_CACHE_TTL=3600  # 1 hour
NEWS_MAX_AGE_HOURS=24
NEWS_FETCH_INTERVAL=60  # minutes
NEWS_MAX_ARTICLES_PER_SOURCE=50
```

### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `NEWS_ENABLED` | Enable/disable news fetching | `true` |
| `NEWS_SOURCES` | Comma-separated list of sources | `economic_times,google_news` |
| `NEWS_CACHE_DIR` | Directory for caching news | `data/news_cache` |
| `NEWS_CACHE_TTL` | Cache time-to-live (seconds) | `3600` |
| `NEWS_MAX_AGE_HOURS` | Maximum age of articles | `24` |
| `NEWS_FETCH_INTERVAL` | Fetch interval (minutes) | `60` |
| `NEWS_MAX_ARTICLES_PER_SOURCE` | Max articles per source | `50` |

## Usage

### Basic News Fetching

```python
from src.config import get_config
from src.data.news_fetcher import NewsFetcher

# Initialize
config = get_config()
news_fetcher = NewsFetcher(
    cache_dir=config.news.cache_dir,
    cache_ttl=config.news.cache_ttl,
    max_age_hours=config.news.max_age_hours,
    enabled_sources=config.news.sources
)

# Fetch general market news
news = news_fetcher.fetch_news(max_articles_per_source=20)

# Fetch news for specific stocks
stock_news = news_fetcher.fetch_stock_news("RELIANCE", max_articles=10)
```

### Stock Research

```python
from src.llm.llm_client import create_llm_client
from src.llm.stock_research import StockResearcher

# Initialize
llm_client = create_llm_client(config.llm)
researcher = StockResearcher(news_fetcher, llm_client)

# Research a stock
research = researcher.research_stock("RELIANCE", max_articles=15)

# Generate report
report = researcher.generate_report(research)
print(report)
```

### Dynamic Watchlist with News

```python
from src.llm.dynamic_watchlist import (
    DynamicWatchlistGenerator,
    fetch_news_headlines,
    fetch_market_indices
)

# Initialize
watchlist_gen = DynamicWatchlistGenerator(llm_client, max_stocks=10)

# Fetch news and generate watchlist
news = fetch_news_headlines()
indices = fetch_market_indices()

watchlist = watchlist_gen.generate_watchlist(
    news_headlines=news,
    market_indices=indices,
    min_confidence=0.6
)

# Get symbols
symbols = watchlist_gen.get_symbols_list(watchlist)
```

## Features

### Caching
- News articles are cached to avoid redundant API calls
- Cache TTL is configurable (default: 1 hour)
- Cache is automatically invalidated when expired

### Deduplication
- Duplicate articles (same URL) are automatically removed
- Works across different sources

### Age Filtering
- Only articles within the configured age limit are returned
- Default: 24 hours

### Symbol Extraction
- Automatically extracts stock symbols from news titles
- Useful for filtering news by stock

## Rate Limiting

The news fetcher implements respectful rate limiting:
- Uses caching to minimize requests
- Configurable fetch intervals
- Graceful fallback when sources are unavailable

## Error Handling

The system handles errors gracefully:
- If a news source fails, others continue to work
- Placeholder data is used when real data is unavailable
- All errors are logged for debugging

## Examples

Run the example scripts to see news integration in action:

```bash
# News fetcher example
uv run -m examples.news_fetcher_example

# Stock research example
uv run -m examples.stock_research_example

# Dynamic watchlist with news
uv run -m examples.dynamic_watchlist_example
```

## Testing

Run the test suite:

```bash
# Test news fetcher
uv run pytest tests/test_news_fetcher.py -v

# Test stock research
uv run pytest tests/test_stock_research.py -v

# All tests
uv run pytest tests/ -v
```

## Troubleshooting

### No News Fetched

**Problem**: `fetch_news()` returns empty list

**Solutions**:
1. Check internet connection
2. Verify RSS feeds are accessible
3. Check cache TTL - may be using stale cache
4. Clear cache: `news_fetcher.clear_cache()`

### NSE API Blocked

**Problem**: NSE announcements return empty

**Solutions**:
1. NSE may block certain user agents
2. Try disabling NSE source: `NEWS_SOURCES=economic_times,google_news`
3. Check NSE website is accessible

### Slow Performance

**Problem**: News fetching is slow

**Solutions**:
1. Increase cache TTL to reduce fetches
2. Reduce `NEWS_MAX_ARTICLES_PER_SOURCE`
3. Disable slower sources
4. Use cache more aggressively

## Best Practices

1. **Cache Wisely**: Set appropriate TTL based on trading frequency
2. **Limit Sources**: Enable only needed sources to improve performance
3. **Monitor Logs**: Check logs for errors and warnings
4. **Test First**: Use examples to verify configuration
5. **Respect Rate Limits**: Don't set fetch interval too low

## Safety Reminders

> [!IMPORTANT]
> News data is used **ONLY** for advisory purposes:
> - Dynamic watchlist generation
> - Sentiment analysis
> - Stock research reports
> 
> News does **NOT** directly trigger trades. All trading decisions remain deterministic and rule-based.

## Future Enhancements

Potential improvements:
- MoneyControl API integration (if available)
- Twitter/X sentiment analysis
- Historical news tracking
- News-based alerts
- Custom news sources
