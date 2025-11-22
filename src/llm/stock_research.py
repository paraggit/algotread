"""
Stock Research Module - Comprehensive stock analysis combining news and sentiment.

Provides detailed research reports for stocks by aggregating:
- News articles from multiple sources
- Sentiment analysis
- LLM-generated insights and recommendations
"""

from datetime import datetime
from typing import List, Optional

from loguru import logger

from src.config import NewsConfig
from src.data.models import NewsArticle, StockResearch, SentimentAnalysis
from src.data.news_fetcher import NewsFetcher
from src.llm.llm_client import LLMClient
from src.llm.sentiment_analyzer import SentimentAnalyzer


class StockResearcher:
    """Comprehensive stock research combining news and sentiment analysis."""
    
    def __init__(
        self,
        news_fetcher: NewsFetcher,
        llm_client: LLMClient,
        sentiment_analyzer: Optional[SentimentAnalyzer] = None
    ):
        """
        Initialize stock researcher.
        
        Args:
            news_fetcher: News fetcher instance
            llm_client: LLM client instance
            sentiment_analyzer: Optional sentiment analyzer (will create if not provided)
        """
        self.news_fetcher = news_fetcher
        self.llm_client = llm_client
        self.sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer(llm_client)
    
    def research_stock(
        self,
        symbol: str,
        max_articles: int = 20
    ) -> Optional[StockResearch]:
        """
        Perform comprehensive research on a stock.
        
        Args:
            symbol: Stock symbol
            max_articles: Maximum number of news articles to analyze
            
        Returns:
            StockResearch object or None if research fails
        """
        logger.info(f"Researching stock: {symbol}")
        
        # Fetch news for the stock
        news_articles = self.news_fetcher.fetch_stock_news(symbol, max_articles)
        
        if not news_articles:
            logger.warning(f"No news found for {symbol}")
            return None
        
        logger.info(f"Found {len(news_articles)} news articles for {symbol}")
        
        # Perform sentiment analysis
        headlines = [article.title for article in news_articles]
        sentiment = self.sentiment_analyzer.analyze(symbol, headlines)
        
        # Generate LLM insights
        insights = self._generate_insights(symbol, news_articles, sentiment)
        
        if not insights:
            logger.warning(f"Failed to generate insights for {symbol}")
            return None
        
        # Create research object
        research = StockResearch(
            symbol=symbol,
            timestamp=datetime.now(),
            news_articles=news_articles,
            sentiment=sentiment,
            opportunity_score=insights.get('opportunity_score', 0.5),
            key_catalysts=insights.get('key_catalysts', []),
            risk_factors=insights.get('risk_factors', []),
            recommendation=insights.get('recommendation', '')
        )
        
        logger.info(
            f"Research complete for {symbol}: "
            f"Score={research.opportunity_score:.2f}, "
            f"Sentiment={sentiment.sentiment.value if sentiment else 'N/A'}"
        )
        
        return research
    
    def research_batch(
        self,
        symbols: List[str],
        max_articles_per_stock: int = 10
    ) -> List[StockResearch]:
        """
        Research multiple stocks.
        
        Args:
            symbols: List of stock symbols
            max_articles_per_stock: Maximum articles per stock
            
        Returns:
            List of StockResearch objects
        """
        results = []
        
        for symbol in symbols:
            research = self.research_stock(symbol, max_articles_per_stock)
            if research:
                results.append(research)
        
        logger.info(f"Batch research complete: {len(results)}/{len(symbols)} stocks")
        return results
    
    def _generate_insights(
        self,
        symbol: str,
        news_articles: List[NewsArticle],
        sentiment: Optional[SentimentAnalysis]
    ) -> Optional[dict]:
        """
        Generate LLM insights from news and sentiment.
        
        Args:
            symbol: Stock symbol
            news_articles: List of news articles
            sentiment: Sentiment analysis result
            
        Returns:
            Dictionary with insights or None if generation fails
        """
        system_prompt = """You are an expert stock market analyst specializing in Indian equities.
Analyze the provided news and sentiment to generate comprehensive research insights.

CRITICAL: You are providing ADVISORY information only. You do NOT trigger trades.
Your analysis will be used to inform trading decisions, but final decisions are made by deterministic strategies.

You must respond with ONLY a JSON object in this exact format:
{
  "opportunity_score": 0.0-1.0,
  "key_catalysts": ["catalyst1", "catalyst2", ...],
  "risk_factors": ["risk1", "risk2", ...],
  "recommendation": "Brief recommendation summary (max 200 chars)"
}

Opportunity score should reflect the overall trading opportunity (0.0 = no opportunity, 1.0 = strong opportunity).
Key catalysts are positive news/events driving the stock.
Risk factors are concerns or negative aspects.
Recommendation is a concise summary of your analysis.
"""
        
        # Format news articles
        news_text = f"News articles for {symbol} ({len(news_articles)} total):\n\n"
        for i, article in enumerate(news_articles[:10], 1):  # Limit to 10 for context
            news_text += f"{i}. [{article.source.value}] {article.title}\n"
            news_text += f"   Published: {article.published_at.strftime('%Y-%m-%d %H:%M')}\n"
            if article.summary:
                news_text += f"   Summary: {article.summary[:150]}...\n"
            news_text += "\n"
        
        # Add sentiment if available
        sentiment_text = ""
        if sentiment:
            sentiment_text = f"""
Sentiment Analysis:
- Sentiment: {sentiment.sentiment.value}
- Confidence: {sentiment.confidence:.2f}
- Risky Event: {sentiment.is_event_risky}
- Rationale: {sentiment.rationale}
"""
        
        user_prompt = f"""Analyze {symbol} based on the following information:

{news_text}{sentiment_text}

Provide your analysis in JSON format. Consider:
1. Overall news sentiment and momentum
2. Key catalysts that could drive intraday movement
3. Risk factors or concerns
4. Opportunity for intraday trading strategies

Focus on actionable insights for intraday trading (not long-term investing).
"""
        
        try:
            response = self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            if not response:
                logger.error(f"Empty response from LLM for {symbol} insights")
                return None
            
            # Validate response
            required_keys = ['opportunity_score', 'key_catalysts', 'risk_factors', 'recommendation']
            if not all(key in response for key in required_keys):
                logger.error(f"Invalid response format from LLM for {symbol}")
                return None
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating insights for {symbol}: {e}")
            return None
    
    def generate_report(self, research: StockResearch) -> str:
        """
        Generate a human-readable research report.
        
        Args:
            research: StockResearch object
            
        Returns:
            Formatted report string
        """
        report = f"""
{'='*80}
STOCK RESEARCH REPORT: {research.symbol}
{'='*80}
Generated: {research.timestamp.strftime('%Y-%m-%d %H:%M:%S IST')}

OPPORTUNITY SCORE: {research.opportunity_score:.2f}/1.00
{'█' * int(research.opportunity_score * 20)}{'░' * (20 - int(research.opportunity_score * 20))}

SENTIMENT ANALYSIS:
"""
        
        if research.sentiment:
            report += f"""  Sentiment: {research.sentiment.sentiment.value.upper()}
  Confidence: {research.sentiment.confidence:.0%}
  Risky Event: {'Yes' if research.sentiment.is_event_risky else 'No'}
  Rationale: {research.sentiment.rationale}
"""
        else:
            report += "  No sentiment data available\n"
        
        report += f"""
KEY CATALYSTS:
"""
        for i, catalyst in enumerate(research.key_catalysts, 1):
            report += f"  {i}. {catalyst}\n"
        
        report += f"""
RISK FACTORS:
"""
        for i, risk in enumerate(research.risk_factors, 1):
            report += f"  {i}. {risk}\n"
        
        report += f"""
RECOMMENDATION:
{research.recommendation}

RECENT NEWS ({len(research.news_articles)} articles):
"""
        
        for i, article in enumerate(research.news_articles[:5], 1):
            report += f"""
  {i}. [{article.source.value}] {article.title}
     Published: {article.published_at.strftime('%Y-%m-%d %H:%M')}
     URL: {article.url}
"""
        
        if len(research.news_articles) > 5:
            report += f"\n  ... and {len(research.news_articles) - 5} more articles\n"
        
        report += f"\n{'='*80}\n"
        
        return report
