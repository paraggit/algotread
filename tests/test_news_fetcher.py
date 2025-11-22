"""Unit tests for news fetcher module."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.data.models import NewsArticle, NewsSource
from src.data.news_fetcher import (
    NewsFetcher,
    EconomicTimesAdapter,
    GoogleNewsAdapter,
    NSEAnnouncementsAdapter
)


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory."""
    cache_dir = tmp_path / "news_cache"
    cache_dir.mkdir()
    return str(cache_dir)


@pytest.fixture
def news_fetcher(temp_cache_dir):
    """Create news fetcher instance."""
    return NewsFetcher(
        cache_dir=temp_cache_dir,
        cache_ttl=3600,
        max_age_hours=24
    )


class TestEconomicTimesAdapter:
    """Tests for Economic Times adapter."""
    
    @patch('feedparser.parse')
    def test_fetch_success(self, mock_parse):
        """Test successful news fetching."""
        # Create mock entry objects with attributes
        entry1 = MagicMock()
        entry1.title = 'Test headline 1'
        entry1.link = 'https://example.com/1'
        entry1.get = MagicMock(side_effect=lambda key, default='': {'summary': 'Test summary 1'}.get(key, default))
        entry1.published_parsed = (2024, 1, 15, 10, 30, 0, 0, 0, 0)
        
        entry2 = MagicMock()
        entry2.title = 'Test headline 2'
        entry2.link = 'https://example.com/2'
        entry2.get = MagicMock(side_effect=lambda key, default='': {'summary': 'Test summary 2'}.get(key, default))
        entry2.published_parsed = (2024, 1, 15, 11, 0, 0, 0, 0, 0)
        
        # Mock RSS feed response
        mock_parse.return_value = MagicMock(entries=[entry1, entry2])
        
        adapter = EconomicTimesAdapter()
        articles = adapter.fetch(max_articles=10)
        
        assert len(articles) > 0
        assert all(isinstance(a, NewsArticle) for a in articles)
        assert all(a.source == NewsSource.ECONOMIC_TIMES for a in articles)
    
    def test_fetch_with_symbol_filter(self):
        """Test fetching with symbol filtering."""
        adapter = EconomicTimesAdapter()
        
        with patch('feedparser.parse') as mock_parse:
            # Create mock entry with attributes
            entry = MagicMock()
            entry.title = 'RELIANCE stock surges'
            entry.link = 'https://example.com/1'
            entry.get = MagicMock(side_effect=lambda key, default='': {'summary': 'RELIANCE gains 5%'}.get(key, default))
            entry.published_parsed = (2024, 1, 15, 10, 30, 0, 0, 0, 0)
            
            mock_parse.return_value = MagicMock(entries=[entry])
            
            articles = adapter.fetch(symbols=['RELIANCE'], max_articles=10)
            
            assert len(articles) > 0
            assert 'RELIANCE' in articles[0].symbols


class TestGoogleNewsAdapter:
    """Tests for Google News adapter."""
    
    @patch('feedparser.parse')
    def test_fetch_success(self, mock_parse):
        """Test successful news fetching."""
        # Create mock entry with attributes
        entry = MagicMock()
        entry.title = 'Indian market news'
        entry.link = 'https://news.google.com/1'
        entry.get = MagicMock(side_effect=lambda key, default='': {'summary': 'Market summary'}.get(key, default))
        entry.published_parsed = (2024, 1, 15, 10, 30, 0, 0, 0, 0)
        
        mock_parse.return_value = MagicMock(entries=[entry])
        
        adapter = GoogleNewsAdapter()
        articles = adapter.fetch(max_articles=10)
        
        assert len(articles) > 0
        assert all(a.source == NewsSource.GOOGLE_NEWS for a in articles)


class TestNSEAnnouncementsAdapter:
    """Tests for NSE announcements adapter."""
    
    @patch('requests.get')
    def test_fetch_success(self, mock_get):
        """Test successful announcement fetching."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    'symbol': 'RELIANCE',
                    'subject': 'Board Meeting',
                    'an_dt': '15-Jan-2024',
                    'desc': 'Board meeting announcement',
                    'attchmntFile': 'https://nseindia.com/file1'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        adapter = NSEAnnouncementsAdapter()
        articles = adapter.fetch(max_articles=10)
        
        assert len(articles) > 0
        assert all(a.source == NewsSource.NSE_ANNOUNCEMENTS for a in articles)


class TestNewsFetcher:
    """Tests for main news fetcher."""
    
    def test_initialization(self, news_fetcher):
        """Test fetcher initialization."""
        assert news_fetcher is not None
        assert Path(news_fetcher.cache_dir).exists()
    
    def test_deduplication(self, news_fetcher):
        """Test article deduplication."""
        articles = [
            NewsArticle(
                title="Test 1",
                source=NewsSource.ECONOMIC_TIMES,
                url="https://example.com/1",
                published_at=datetime.now()
            ),
            NewsArticle(
                title="Test 2",
                source=NewsSource.GOOGLE_NEWS,
                url="https://example.com/1",  # Same URL
                published_at=datetime.now()
            ),
            NewsArticle(
                title="Test 3",
                source=NewsSource.ECONOMIC_TIMES,
                url="https://example.com/2",
                published_at=datetime.now()
            )
        ]
        
        deduplicated = news_fetcher._deduplicate(articles)
        
        assert len(deduplicated) == 2  # Should remove one duplicate
        assert len(set(a.url for a in deduplicated)) == 2
    
    def test_filter_by_age(self, news_fetcher):
        """Test filtering by article age."""
        now = datetime.now()
        articles = [
            NewsArticle(
                title="Recent",
                source=NewsSource.ECONOMIC_TIMES,
                url="https://example.com/1",
                published_at=now - timedelta(hours=1)
            ),
            NewsArticle(
                title="Old",
                source=NewsSource.ECONOMIC_TIMES,
                url="https://example.com/2",
                published_at=now - timedelta(hours=48)  # Too old
            )
        ]
        
        filtered = news_fetcher._filter_by_age(articles)
        
        assert len(filtered) == 1
        assert filtered[0].title == "Recent"
    
    def test_cache_save_and_load(self, news_fetcher):
        """Test caching mechanism."""
        articles = [
            NewsArticle(
                title="Test Article",
                source=NewsSource.ECONOMIC_TIMES,
                url="https://example.com/test",
                published_at=datetime.now(),
                summary="Test summary",
                symbols=["RELIANCE"]
            )
        ]
        
        # Save to cache
        news_fetcher._save_to_cache(articles, None)
        
        # Load from cache
        loaded = news_fetcher._load_from_cache(None)
        
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].title == "Test Article"
        assert loaded[0].symbols == ["RELIANCE"]
    
    def test_clear_cache(self, news_fetcher):
        """Test cache clearing."""
        articles = [
            NewsArticle(
                title="Test",
                source=NewsSource.ECONOMIC_TIMES,
                url="https://example.com/test",
                published_at=datetime.now()
            )
        ]
        
        news_fetcher._save_to_cache(articles, None)
        assert len(list(Path(news_fetcher.cache_dir).glob("news_*.json"))) > 0
        
        news_fetcher.clear_cache()
        assert len(list(Path(news_fetcher.cache_dir).glob("news_*.json"))) == 0


class TestNewsArticleModel:
    """Tests for NewsArticle model."""
    
    def test_hash_and_equality(self):
        """Test hash and equality based on URL."""
        article1 = NewsArticle(
            title="Test 1",
            source=NewsSource.ECONOMIC_TIMES,
            url="https://example.com/1",
            published_at=datetime.now()
        )
        
        article2 = NewsArticle(
            title="Test 2",  # Different title
            source=NewsSource.GOOGLE_NEWS,  # Different source
            url="https://example.com/1",  # Same URL
            published_at=datetime.now()
        )
        
        assert article1 == article2  # Should be equal (same URL)
        assert hash(article1) == hash(article2)
