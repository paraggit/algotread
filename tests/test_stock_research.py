"""Unit tests for stock research module."""

from datetime import datetime
from unittest.mock import Mock, MagicMock

import pytest

from src.data.models import NewsArticle, NewsSource, SentimentAnalysis, Sentiment
from src.llm.stock_research import StockResearcher


@pytest.fixture
def mock_news_fetcher():
    """Create mock news fetcher."""
    fetcher = Mock()
    fetcher.fetch_stock_news.return_value = [
        NewsArticle(
            title="RELIANCE announces Q3 results",
            source=NewsSource.ECONOMIC_TIMES,
            url="https://example.com/1",
            published_at=datetime.now(),
            summary="Strong quarterly results",
            symbols=["RELIANCE"]
        ),
        NewsArticle(
            title="RELIANCE stock surges on positive news",
            source=NewsSource.GOOGLE_NEWS,
            url="https://example.com/2",
            published_at=datetime.now(),
            summary="Stock gains 5%",
            symbols=["RELIANCE"]
        )
    ]
    return fetcher


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = Mock()
    client.generate.return_value = {
        "opportunity_score": 0.85,
        "key_catalysts": ["Strong Q3 results", "Positive market sentiment"],
        "risk_factors": ["High valuation", "Market volatility"],
        "recommendation": "Strong buy for intraday trading based on momentum"
    }
    return client


@pytest.fixture
def mock_sentiment_analyzer():
    """Create mock sentiment analyzer."""
    analyzer = Mock()
    analyzer.analyze.return_value = SentimentAnalysis(
        ticker="RELIANCE",
        sentiment=Sentiment.POSITIVE,
        confidence=0.9,
        is_event_risky=False,
        rationale="Positive earnings announcement"
    )
    return analyzer


@pytest.fixture
def stock_researcher(mock_news_fetcher, mock_llm_client, mock_sentiment_analyzer):
    """Create stock researcher instance."""
    return StockResearcher(
        news_fetcher=mock_news_fetcher,
        llm_client=mock_llm_client,
        sentiment_analyzer=mock_sentiment_analyzer
    )


class TestStockResearcher:
    """Tests for stock researcher."""
    
    def test_research_stock_success(self, stock_researcher):
        """Test successful stock research."""
        research = stock_researcher.research_stock("RELIANCE", max_articles=10)
        
        assert research is not None
        assert research.symbol == "RELIANCE"
        assert len(research.news_articles) > 0
        assert research.sentiment is not None
        assert 0.0 <= research.opportunity_score <= 1.0
        assert len(research.key_catalysts) > 0
        assert len(research.risk_factors) > 0
        assert research.recommendation != ""
    
    def test_research_stock_no_news(self, stock_researcher, mock_news_fetcher):
        """Test research when no news is available."""
        mock_news_fetcher.fetch_stock_news.return_value = []
        
        research = stock_researcher.research_stock("UNKNOWN", max_articles=10)
        
        assert research is None
    
    def test_research_batch(self, stock_researcher):
        """Test batch research."""
        symbols = ["RELIANCE", "TCS", "INFY"]
        results = stock_researcher.research_batch(symbols, max_articles_per_stock=5)
        
        assert len(results) > 0
        assert all(r.symbol in symbols for r in results)
    
    def test_generate_report(self, stock_researcher):
        """Test report generation."""
        research = stock_researcher.research_stock("RELIANCE", max_articles=10)
        
        assert research is not None
        
        report = stock_researcher.generate_report(research)
        
        assert "RELIANCE" in report
        assert "OPPORTUNITY SCORE" in report
        assert "SENTIMENT ANALYSIS" in report
        assert "KEY CATALYSTS" in report
        assert "RISK FACTORS" in report
        assert "RECOMMENDATION" in report
        assert "RECENT NEWS" in report
    
    def test_generate_insights_invalid_response(self, stock_researcher, mock_llm_client):
        """Test handling of invalid LLM response."""
        # Mock invalid response (missing required keys)
        mock_llm_client.generate.return_value = {
            "opportunity_score": 0.5
            # Missing other required keys
        }
        
        news_articles = [
            NewsArticle(
                title="Test",
                source=NewsSource.ECONOMIC_TIMES,
                url="https://example.com/1",
                published_at=datetime.now()
            )
        ]
        
        insights = stock_researcher._generate_insights("TEST", news_articles, None)
        
        assert insights is None
    
    def test_generate_insights_with_sentiment(self, stock_researcher):
        """Test insights generation with sentiment data."""
        news_articles = [
            NewsArticle(
                title="Positive news",
                source=NewsSource.ECONOMIC_TIMES,
                url="https://example.com/1",
                published_at=datetime.now(),
                summary="Good news summary"
            )
        ]
        
        sentiment = SentimentAnalysis(
            ticker="TEST",
            sentiment=Sentiment.POSITIVE,
            confidence=0.8,
            is_event_risky=False,
            rationale="Positive earnings"
        )
        
        insights = stock_researcher._generate_insights("TEST", news_articles, sentiment)
        
        assert insights is not None
        assert "opportunity_score" in insights
        assert "key_catalysts" in insights
        assert "risk_factors" in insights
        assert "recommendation" in insights
