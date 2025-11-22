"""
Dynamic Watchlist Generator using LLM and News Analysis.

IMPORTANT: This module provides ADVISORY stock recommendations only.
It does NOT trigger trades. The watchlist is used to filter which stocks
the strategies will evaluate. Final trading decisions remain deterministic.
"""

from datetime import datetime
from typing import List, Optional

from loguru import logger
from pydantic import BaseModel, Field

from src.llm.llm_client import LLMClient


class StockRecommendation(BaseModel):
    """Stock recommendation from news analysis."""
    symbol: str
    reason: str = Field(description="Why this stock is recommended")
    catalyst: str = Field(description="News catalyst or event")
    confidence: float = Field(ge=0.0, le=1.0)
    expected_direction: str = Field(description="Expected direction: UP, DOWN, or VOLATILE")
    risk_level: str = Field(description="Risk level: LOW, MEDIUM, HIGH")


class WatchlistRecommendation(BaseModel):
    """Complete watchlist recommendation."""
    stocks: List[StockRecommendation]
    market_summary: str
    timestamp: datetime


class DynamicWatchlistGenerator:
    """Generate dynamic watchlist based on news analysis."""
    
    def __init__(self, llm_client: LLMClient, max_stocks: int = 10):
        """
        Initialize dynamic watchlist generator.
        
        Args:
            llm_client: LLM client instance
            max_stocks: Maximum number of stocks in watchlist (default 10)
        """
        self.llm_client = llm_client
        self.max_stocks = max_stocks
    
    def generate_watchlist(
        self,
        news_headlines: List[dict],
        market_indices: Optional[dict] = None,
        sector_filter: Optional[List[str]] = None,
        min_confidence: float = 0.6
    ) -> Optional[WatchlistRecommendation]:
        """
        Generate dynamic watchlist based on news analysis.
        
        Args:
            news_headlines: List of dicts with keys: headline, source, timestamp, url
            market_indices: Optional dict with index data (Nifty, BankNifty levels)
            sector_filter: Optional list of sectors to focus on
            min_confidence: Minimum confidence threshold (default 0.6)
            
        Returns:
            WatchlistRecommendation or None if generation fails
        """
        if not news_headlines:
            logger.warning("No news headlines provided for watchlist generation")
            return None
        
        system_prompt = """You are an expert Indian equity market analyst specializing in intraday trading opportunities.
Your role is to analyze news and recommend stocks for intraday trading based on catalysts and momentum.

CRITICAL: You are providing ADVISORY stock recommendations only. You do NOT trigger trades.
Your output will be used to create a watchlist that strategies will evaluate. Final trading decisions
are made by deterministic strategies and risk management rules.

Focus on:
- Stocks with clear catalysts (earnings, news, events)
- Stocks likely to have intraday volatility and volume
- Stocks suitable for intraday trading (liquid, active)
- Avoid stocks with excessive risk or unclear direction

You must respond with ONLY a JSON object in this exact format:
{
  "stocks": [
    {
      "symbol": "SYMBOL",
      "reason": "Brief reason for recommendation (max 100 chars)",
      "catalyst": "News catalyst or event (max 100 chars)",
      "confidence": 0.0-1.0,
      "expected_direction": "UP" | "DOWN" | "VOLATILE",
      "risk_level": "LOW" | "MEDIUM" | "HIGH"
    }
  ],
  "market_summary": "Brief market overview (max 200 chars)"
}

Provide 5-10 stock recommendations, prioritized by intraday trading potential.
"""
        
        # Format news headlines
        headlines_text = "\n".join([
            f"- [{h.get('source', 'Unknown')}] {h.get('headline', '')} ({h.get('timestamp', 'N/A')})"
            for h in news_headlines[:50]  # Limit to 50 headlines
        ])
        
        # Format market indices if provided
        indices_text = ""
        if market_indices:
            indices_text = "\n\nMarket Indices:\n"
            for index, data in market_indices.items():
                change = data.get('change_pct', 0)
                indices_text += f"- {index}: {data.get('level', 'N/A')} ({change:+.2f}%)\n"
        
        # Format sector filter if provided
        sector_text = ""
        if sector_filter:
            sector_text = f"\n\nFocus Sectors: {', '.join(sector_filter)}"
        
        user_prompt = f"""Analyze today's news and recommend stocks for intraday trading.

News Headlines:
{headlines_text}{indices_text}{sector_text}

Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}

Provide your recommendations in JSON format. Focus on stocks with:
1. Clear intraday catalysts
2. Expected volatility and volume
3. Suitable for the strategies (ORB breakout, EMA trend, VWAP reversion)
4. Liquid and actively traded

Avoid:
- Stocks in trading halt or suspension
- Stocks with unclear direction
- Illiquid stocks
- Stocks with excessive fundamental risk
"""
        
        try:
            response = self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2  # Slightly higher for diversity
            )
            
            if not response:
                logger.error("Empty response from LLM for watchlist generation")
                return None
            
            # Parse stocks
            stocks_data = response.get("stocks", [])
            market_summary = response.get("market_summary", "")
            
            if not stocks_data:
                logger.warning("No stocks recommended by LLM")
                return None
            
            # Validate and filter stocks
            recommendations = []
            for stock_data in stocks_data[:self.max_stocks]:
                try:
                    stock = StockRecommendation(**stock_data)
                    
                    # Filter by confidence
                    if stock.confidence >= min_confidence:
                        recommendations.append(stock)
                    else:
                        logger.debug(
                            f"Filtered out {stock.symbol} due to low confidence: {stock.confidence:.2f}"
                        )
                except Exception as e:
                    logger.warning(f"Invalid stock recommendation: {e}")
                    continue
            
            if not recommendations:
                logger.warning("No stocks passed confidence filter")
                return None
            
            watchlist = WatchlistRecommendation(
                stocks=recommendations,
                market_summary=market_summary,
                timestamp=datetime.now()
            )
            
            logger.info(
                f"Generated dynamic watchlist with {len(recommendations)} stocks: "
                f"{', '.join([s.symbol for s in recommendations])}"
            )
            
            # Log details
            for stock in recommendations:
                logger.info(
                    f"  {stock.symbol}: {stock.reason} | "
                    f"Direction: {stock.expected_direction} | "
                    f"Risk: {stock.risk_level} | "
                    f"Confidence: {stock.confidence:.2f}"
                )
            
            return watchlist
            
        except Exception as e:
            logger.error(f"Error generating dynamic watchlist: {e}")
            return None
    
    def get_symbols_list(self, watchlist: WatchlistRecommendation) -> List[str]:
        """
        Extract just the symbol list from watchlist recommendation.
        
        Args:
            watchlist: WatchlistRecommendation
            
        Returns:
            List of stock symbols
        """
        return [stock.symbol for stock in watchlist.stocks]
    
    def filter_by_direction(
        self,
        watchlist: WatchlistRecommendation,
        direction: str
    ) -> List[str]:
        """
        Filter watchlist by expected direction.
        
        Args:
            watchlist: WatchlistRecommendation
            direction: Expected direction (UP, DOWN, VOLATILE)
            
        Returns:
            List of stock symbols matching direction
        """
        return [
            stock.symbol
            for stock in watchlist.stocks
            if stock.expected_direction == direction.upper()
        ]
    
    def filter_by_risk(
        self,
        watchlist: WatchlistRecommendation,
        max_risk: str = "MEDIUM"
    ) -> List[str]:
        """
        Filter watchlist by risk level.
        
        Args:
            watchlist: WatchlistRecommendation
            max_risk: Maximum risk level (LOW, MEDIUM, HIGH)
            
        Returns:
            List of stock symbols within risk tolerance
        """
        risk_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        max_risk_level = risk_levels.get(max_risk.upper(), 2)
        
        return [
            stock.symbol
            for stock in watchlist.stocks
            if risk_levels.get(stock.risk_level, 3) <= max_risk_level
        ]


def fetch_news_headlines(
    news_fetcher: Optional['NewsFetcher'] = None,
    symbols: Optional[List[str]] = None,
    sources: Optional[List[str]] = None
) -> List[dict]:
    """
    Fetch news headlines from various sources.
    
    Args:
        news_fetcher: Optional NewsFetcher instance (will create if not provided)
        symbols: Optional list of symbols to filter by
        sources: Optional list of news sources to fetch from
        
    Returns:
        List of news headline dicts compatible with DynamicWatchlistGenerator
    """
    from src.data.news_fetcher import NewsFetcher
    from src.config import get_config
    
    if news_fetcher is None:
        config = get_config()
        news_fetcher = NewsFetcher(
            cache_dir=config.news.cache_dir,
            cache_ttl=config.news.cache_ttl,
            max_age_hours=config.news.max_age_hours,
            enabled_sources=sources or config.news.sources
        )
    
    try:
        articles = news_fetcher.fetch_news(symbols=symbols)
        
        # Convert NewsArticle objects to dict format expected by watchlist generator
        headlines = []
        for article in articles:
            headlines.append({
                "headline": article.title,
                "source": article.source.value,
                "timestamp": article.published_at.isoformat(),
                "url": article.url,
                "summary": article.summary or ""
            })
        
        logger.info(f"Fetched {len(headlines)} news headlines")
        return headlines
        
    except Exception as e:
        logger.error(f"Error fetching news headlines: {e}")
        return []


def fetch_market_indices(kite_client: Optional['KiteConnect'] = None) -> dict:
    """
    Fetch current market indices data.
    
    Args:
        kite_client: Optional KiteConnect client (will create if not provided)
        
    Returns:
        Dictionary of index data
    """
    from kiteconnect import KiteConnect
    from src.config import get_config
    
    if kite_client is None:
        try:
            config = get_config()
            kite_client = KiteConnect(api_key=config.kite.api_key)
            kite_client.set_access_token(config.kite.access_token)
        except Exception as e:
            logger.warning(f"Could not initialize Kite client: {e}")
            return _get_placeholder_indices()
    
    try:
        # Fetch index quotes from Kite
        # NSE index instrument tokens
        index_tokens = {
            "NIFTY50": "NSE:NIFTY 50",
            "BANKNIFTY": "NSE:NIFTY BANK",
            "NIFTYIT": "NSE:NIFTY IT"
        }
        
        indices_data = {}
        quotes = kite_client.quote(list(index_tokens.values()))
        
        for index_name, symbol in index_tokens.items():
            if symbol in quotes:
                quote = quotes[symbol]
                indices_data[index_name] = {
                    "level": quote.get('last_price', 0),
                    "change_pct": quote.get('change', 0)
                }
        
        logger.info(f"Fetched data for {len(indices_data)} indices")
        return indices_data
        
    except Exception as e:
        logger.warning(f"Error fetching market indices: {e}, using placeholder data")
        return _get_placeholder_indices()


def _get_placeholder_indices() -> dict:
    """Get placeholder index data when real data is unavailable."""
    logger.debug("Using placeholder index data")
    return {
        "NIFTY50": {"level": 19500, "change_pct": 0.0},
        "BANKNIFTY": {"level": 44000, "change_pct": 0.0},
        "NIFTYIT": {"level": 30000, "change_pct": 0.0}
    }
