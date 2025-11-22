"""
News fetcher for aggregating news from multiple public sources.

Fetches news from:
- Economic Times RSS feeds
- Google News RSS feeds
- NSE announcements

Includes caching and deduplication to avoid redundant fetches.
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set
from urllib.parse import quote

import feedparser
import requests
from loguru import logger

from src.data.models import NewsArticle, NewsSource


class NewsSourceAdapter:
    """Base class for news source adapters."""
    
    def fetch(self, symbols: Optional[List[str]] = None, max_articles: int = 50) -> List[NewsArticle]:
        """Fetch news articles from the source."""
        raise NotImplementedError


class EconomicTimesAdapter(NewsSourceAdapter):
    """Adapter for Economic Times RSS feeds."""
    
    RSS_FEEDS = {
        "markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "stocks": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    }
    
    def fetch(self, symbols: Optional[List[str]] = None, max_articles: int = 50) -> List[NewsArticle]:
        """Fetch news from Economic Times RSS feeds."""
        articles = []
        
        for feed_name, feed_url in self.RSS_FEEDS.items():
            try:
                logger.debug(f"Fetching Economic Times {feed_name} feed")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:max_articles]:
                    try:
                        # Parse published date
                        published_at = datetime.now()
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published_at = datetime(*entry.published_parsed[:6])
                        
                        # Extract symbols from title/summary if provided
                        extracted_symbols = []
                        if symbols:
                            title_upper = entry.title.upper()
                            summary_upper = entry.get('summary', '').upper()
                            for symbol in symbols:
                                if symbol.upper() in title_upper or symbol.upper() in summary_upper:
                                    extracted_symbols.append(symbol.upper())
                        
                        article = NewsArticle(
                            title=entry.title,
                            source=NewsSource.ECONOMIC_TIMES,
                            url=entry.link,
                            published_at=published_at,
                            summary=entry.get('summary', ''),
                            symbols=extracted_symbols
                        )
                        articles.append(article)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing ET entry: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error fetching Economic Times {feed_name} feed: {e}")
                continue
        
        logger.info(f"Fetched {len(articles)} articles from Economic Times")
        return articles


class GoogleNewsAdapter(NewsSourceAdapter):
    """Adapter for Google News RSS feeds."""
    
    BASE_URL = "https://news.google.com/rss/search"
    
    def fetch(self, symbols: Optional[List[str]] = None, max_articles: int = 50) -> List[NewsArticle]:
        """Fetch news from Google News RSS feeds."""
        articles = []
        
        # Default query for Indian stock market
        queries = ["Indian stock market NSE BSE"]
        
        # Add symbol-specific queries if provided
        if symbols:
            for symbol in symbols[:10]:  # Limit to 10 symbols to avoid too many requests
                queries.append(f"{symbol} stock India")
        
        for query in queries:
            try:
                # Build RSS URL
                encoded_query = quote(query)
                feed_url = f"{self.BASE_URL}?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
                
                logger.debug(f"Fetching Google News for query: {query}")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:max_articles // len(queries)]:
                    try:
                        # Parse published date
                        published_at = datetime.now()
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published_at = datetime(*entry.published_parsed[:6])
                        
                        # Extract symbols from title
                        extracted_symbols = []
                        if symbols:
                            title_upper = entry.title.upper()
                            for symbol in symbols:
                                if symbol.upper() in title_upper:
                                    extracted_symbols.append(symbol.upper())
                        
                        article = NewsArticle(
                            title=entry.title,
                            source=NewsSource.GOOGLE_NEWS,
                            url=entry.link,
                            published_at=published_at,
                            summary=entry.get('summary', ''),
                            symbols=extracted_symbols
                        )
                        articles.append(article)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing Google News entry: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error fetching Google News for query '{query}': {e}")
                continue
        
        logger.info(f"Fetched {len(articles)} articles from Google News")
        return articles


class NSEAnnouncementsAdapter(NewsSourceAdapter):
    """Adapter for NSE corporate announcements."""
    
    # NSE API endpoints (may require headers to work)
    ANNOUNCEMENTS_URL = "https://www.nseindia.com/api/corporate-announcements"
    
    def fetch(self, symbols: Optional[List[str]] = None, max_articles: int = 50) -> List[NewsArticle]:
        """Fetch announcements from NSE."""
        articles = []
        
        try:
            # NSE requires specific headers to prevent blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            logger.debug("Fetching NSE announcements")
            response = requests.get(self.ANNOUNCEMENTS_URL, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # NSE API structure may vary, adjust as needed
                announcements = data.get('data', [])
                
                for announcement in announcements[:max_articles]:
                    try:
                        symbol = announcement.get('symbol', '').upper()
                        
                        # Filter by symbols if provided
                        if symbols and symbol not in [s.upper() for s in symbols]:
                            continue
                        
                        # Parse date
                        published_at = datetime.now()
                        date_str = announcement.get('an_dt', '')
                        if date_str:
                            try:
                                published_at = datetime.strptime(date_str, '%d-%b-%Y')
                            except:
                                pass
                        
                        title = announcement.get('subject', 'NSE Announcement')
                        url = announcement.get('attchmntFile', f"https://www.nseindia.com/companies-listing/corporate-filings-announcements")
                        
                        article = NewsArticle(
                            title=f"{symbol}: {title}",
                            source=NewsSource.NSE_ANNOUNCEMENTS,
                            url=url,
                            published_at=published_at,
                            summary=announcement.get('desc', ''),
                            symbols=[symbol] if symbol else []
                        )
                        articles.append(article)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing NSE announcement: {e}")
                        continue
            else:
                logger.warning(f"NSE API returned status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching NSE announcements: {e}")
        
        logger.info(f"Fetched {len(articles)} announcements from NSE")
        return articles


class NewsFetcher:
    """Main news fetcher that aggregates from multiple sources."""
    
    def __init__(
        self,
        cache_dir: str = "data/news_cache",
        cache_ttl: int = 3600,
        max_age_hours: int = 24,
        enabled_sources: Optional[List[str]] = None
    ):
        """
        Initialize news fetcher.
        
        Args:
            cache_dir: Directory for caching news
            cache_ttl: Cache time-to-live in seconds
            max_age_hours: Maximum age of news articles to fetch
            enabled_sources: List of enabled sources (default: all)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = cache_ttl
        self.max_age_hours = max_age_hours
        
        # Initialize adapters
        self.adapters = {
            "economic_times": EconomicTimesAdapter(),
            "google_news": GoogleNewsAdapter(),
            "nse_announcements": NSEAnnouncementsAdapter(),
        }
        
        # Filter enabled sources
        if enabled_sources:
            self.adapters = {
                k: v for k, v in self.adapters.items()
                if k in enabled_sources
            }
        
        logger.info(f"NewsFetcher initialized with sources: {list(self.adapters.keys())}")
    
    def fetch_news(
        self,
        symbols: Optional[List[str]] = None,
        max_articles_per_source: int = 50,
        use_cache: bool = True
    ) -> List[NewsArticle]:
        """
        Fetch news from all enabled sources.
        
        Args:
            symbols: Optional list of symbols to filter by
            max_articles_per_source: Maximum articles per source
            use_cache: Whether to use cached news
            
        Returns:
            List of deduplicated news articles
        """
        # Check cache first
        if use_cache:
            cached_news = self._load_from_cache(symbols)
            if cached_news is not None:
                logger.info(f"Loaded {len(cached_news)} articles from cache")
                return cached_news
        
        # Fetch from all sources
        all_articles = []
        for source_name, adapter in self.adapters.items():
            try:
                articles = adapter.fetch(symbols, max_articles_per_source)
                all_articles.extend(articles)
            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
                continue
        
        # Deduplicate by URL
        deduplicated = self._deduplicate(all_articles)
        
        # Filter by age
        filtered = self._filter_by_age(deduplicated)
        
        # Sort by published date (newest first)
        filtered.sort(key=lambda x: x.published_at, reverse=True)
        
        # Cache the results
        if use_cache:
            self._save_to_cache(filtered, symbols)
        
        logger.info(f"Fetched {len(filtered)} articles total (after deduplication and filtering)")
        return filtered
    
    def fetch_stock_news(
        self,
        symbol: str,
        max_articles: int = 20,
        use_cache: bool = True
    ) -> List[NewsArticle]:
        """
        Fetch news for a specific stock symbol.
        
        Args:
            symbol: Stock symbol
            max_articles: Maximum number of articles
            use_cache: Whether to use cached news
            
        Returns:
            List of news articles for the symbol
        """
        all_news = self.fetch_news([symbol], use_cache=use_cache)
        
        # Filter for articles mentioning the symbol
        symbol_news = [
            article for article in all_news
            if symbol.upper() in article.symbols or symbol.upper() in article.title.upper()
        ]
        
        return symbol_news[:max_articles]
    
    def _deduplicate(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Remove duplicate articles based on URL."""
        seen_urls: Set[str] = set()
        unique_articles = []
        
        for article in articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)
        
        logger.debug(f"Deduplicated {len(articles)} -> {len(unique_articles)} articles")
        return unique_articles
    
    def _filter_by_age(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Filter articles by maximum age."""
        cutoff_time = datetime.now() - timedelta(hours=self.max_age_hours)
        filtered = [
            article for article in articles
            if article.published_at >= cutoff_time
        ]
        
        logger.debug(f"Filtered by age {len(articles)} -> {len(filtered)} articles")
        return filtered
    
    def _get_cache_key(self, symbols: Optional[List[str]]) -> str:
        """Generate cache key."""
        if symbols:
            symbols_str = "_".join(sorted(symbols))
            key_hash = hashlib.md5(symbols_str.encode()).hexdigest()[:8]
            return f"news_{key_hash}.json"
        return "news_all.json"
    
    def _load_from_cache(self, symbols: Optional[List[str]]) -> Optional[List[NewsArticle]]:
        """Load news from cache if available and fresh."""
        cache_file = self.cache_dir / self._get_cache_key(symbols)
        
        if not cache_file.exists():
            return None
        
        # Check if cache is still fresh
        cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if cache_age > self.cache_ttl:
            logger.debug(f"Cache expired (age: {cache_age:.0f}s)")
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            articles = []
            for item in data:
                article = NewsArticle(
                    title=item['title'],
                    source=NewsSource(item['source']),
                    url=item['url'],
                    published_at=datetime.fromisoformat(item['published_at']),
                    summary=item.get('summary'),
                    symbols=item.get('symbols', []),
                    content=item.get('content')
                )
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.warning(f"Error loading cache: {e}")
            return None
    
    def _save_to_cache(self, articles: List[NewsArticle], symbols: Optional[List[str]]) -> None:
        """Save news to cache."""
        cache_file = self.cache_dir / self._get_cache_key(symbols)
        
        try:
            data = []
            for article in articles:
                data.append({
                    'title': article.title,
                    'source': article.source.value,
                    'url': article.url,
                    'published_at': article.published_at.isoformat(),
                    'summary': article.summary,
                    'symbols': article.symbols,
                    'content': article.content
                })
            
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Cached {len(articles)} articles to {cache_file}")
            
        except Exception as e:
            logger.warning(f"Error saving cache: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cached news."""
        for cache_file in self.cache_dir.glob("news_*.json"):
            cache_file.unlink()
            logger.info(f"Deleted cache file: {cache_file}")
