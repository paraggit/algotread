"""
Global Market Analyzer.

Analyzes overnight global market trends (US, Singapore, Asian markets) to provide
context for Indian market trading. This helps in:
- Pre-market strategy selection
- Risk adjustment based on global sentiment
- Identifying potential gap up/down scenarios
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List

from loguru import logger
from pydantic import BaseModel, Field

from src.llm.llm_client import LLMClient


class GlobalMarketTrend(str, Enum):
    """Global market trend classification."""
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"
    VOLATILE = "volatile"


class MarketData(BaseModel):
    """Market data for a single index."""
    index_name: str
    close: float
    change_pct: float
    volume_ratio: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None


class GlobalMarketAnalysis(BaseModel):
    """Analysis of global markets."""
    overall_trend: GlobalMarketTrend
    confidence: float = Field(ge=0.0, le=1.0)
    us_markets_summary: str
    asian_markets_summary: str
    key_drivers: List[str]
    indian_market_outlook: str
    recommended_strategy_bias: str  # "aggressive", "moderate", "conservative", "defensive"
    expected_gap: str  # "gap_up", "gap_down", "flat"
    risk_level: str  # "low", "medium", "high"
    timestamp: datetime


class GlobalMarketAnalyzer:
    """Analyze global markets for Indian trading context."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize global market analyzer.
        
        Args:
            llm_client: LLM client instance
        """
        self.llm_client = llm_client
    
    def analyze_global_markets(
        self,
        us_markets: Dict[str, MarketData],
        asian_markets: Dict[str, MarketData],
        news_headlines: Optional[List[str]] = None
    ) -> Optional[GlobalMarketAnalysis]:
        """
        Analyze global markets and provide trading context.
        
        Args:
            us_markets: Dict of US market data (SPY, QQQ, DIA, etc.)
            asian_markets: Dict of Asian market data (Nikkei, HSI, STI, etc.)
            news_headlines: Optional global news headlines
            
        Returns:
            GlobalMarketAnalysis or None if analysis fails
        """
        system_prompt = """You are a global markets analyst specializing in overnight market analysis for Indian equity trading.
Your role is to analyze US and Asian market trends to provide context for Indian market trading.

CRITICAL: You are providing ADVISORY analysis only. You do NOT trigger trades.
Your output helps traders understand global context and adjust their strategy bias.

You must respond with ONLY a JSON object in this exact format:
{
  "overall_trend": "strong_bullish" | "bullish" | "neutral" | "bearish" | "strong_bearish" | "volatile",
  "confidence": 0.0-1.0,
  "us_markets_summary": "Brief summary of US markets (max 150 chars)",
  "asian_markets_summary": "Brief summary of Asian markets (max 150 chars)",
  "key_drivers": ["driver1", "driver2", "driver3"],
  "indian_market_outlook": "Expected impact on Indian markets (max 200 chars)",
  "recommended_strategy_bias": "aggressive" | "moderate" | "conservative" | "defensive",
  "expected_gap": "gap_up" | "gap_down" | "flat",
  "risk_level": "low" | "medium" | "high"
}

Strategy bias guidelines:
- aggressive: Strong global trends, high confidence, favor breakout strategies
- moderate: Normal conditions, balanced approach
- conservative: Mixed signals, reduce position sizes
- defensive: Negative trends, focus on risk management, consider staying out
"""
        
        # Format US markets data
        us_text = "US Markets:\n"
        for name, data in us_markets.items():
            us_text += f"- {name}: {data.change_pct:+.2f}%\n"
        
        # Format Asian markets data
        asian_text = "Asian Markets:\n"
        for name, data in asian_markets.items():
            asian_text += f"- {name}: {data.change_pct:+.2f}%\n"
        
        # Format news if provided
        news_text = ""
        if news_headlines:
            news_text = "\n\nGlobal News Headlines:\n"
            news_text += "\n".join([f"- {h}" for h in news_headlines[:10]])
        
        user_prompt = f"""Analyze overnight global markets for Indian trading context:

{us_text}
{asian_text}{news_text}

Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}
Indian Market Opens: 09:15 IST

Provide your analysis in JSON format. Consider:
1. Overall global market sentiment
2. Correlation with Indian markets (Nifty/Sensex)
3. Sector-specific impacts (IT follows US tech, etc.)
4. Expected gap and volatility
5. Recommended trading approach for the day
"""
        
        try:
            response = self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            if not response:
                logger.error("Empty response from LLM for global market analysis")
                return None
            
            # Parse and validate
            analysis = GlobalMarketAnalysis(
                overall_trend=GlobalMarketTrend(response.get("overall_trend", "neutral")),
                confidence=float(response.get("confidence", 0.5)),
                us_markets_summary=response.get("us_markets_summary", ""),
                asian_markets_summary=response.get("asian_markets_summary", ""),
                key_drivers=response.get("key_drivers", []),
                indian_market_outlook=response.get("indian_market_outlook", ""),
                recommended_strategy_bias=response.get("recommended_strategy_bias", "moderate"),
                expected_gap=response.get("expected_gap", "flat"),
                risk_level=response.get("risk_level", "medium"),
                timestamp=datetime.now()
            )
            
            logger.info(
                f"Global market analysis: {analysis.overall_trend.value} "
                f"(confidence: {analysis.confidence:.2f}, bias: {analysis.recommended_strategy_bias})"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing global markets: {e}")
            return None
    
    def get_strategy_adjustments(
        self,
        analysis: GlobalMarketAnalysis
    ) -> Dict[str, any]:
        """
        Get recommended strategy adjustments based on global analysis.
        
        Args:
            analysis: GlobalMarketAnalysis
            
        Returns:
            Dictionary of strategy adjustments
        """
        adjustments = {
            "position_size_multiplier": 1.0,
            "enable_short_trades": False,
            "preferred_strategies": [],
            "risk_multiplier": 1.0,
            "max_positions": 3
        }
        
        # Adjust based on strategy bias
        if analysis.recommended_strategy_bias == "aggressive":
            adjustments["position_size_multiplier"] = 1.2
            adjustments["preferred_strategies"] = ["orb_supertrend", "ema_trend"]
            adjustments["max_positions"] = 4
            
        elif analysis.recommended_strategy_bias == "moderate":
            adjustments["position_size_multiplier"] = 1.0
            adjustments["preferred_strategies"] = ["orb_supertrend", "ema_trend", "vwap_reversion"]
            adjustments["max_positions"] = 3
            
        elif analysis.recommended_strategy_bias == "conservative":
            adjustments["position_size_multiplier"] = 0.7
            adjustments["preferred_strategies"] = ["vwap_reversion"]
            adjustments["risk_multiplier"] = 0.8
            adjustments["max_positions"] = 2
            
        elif analysis.recommended_strategy_bias == "defensive":
            adjustments["position_size_multiplier"] = 0.5
            adjustments["preferred_strategies"] = []  # Consider staying out
            adjustments["risk_multiplier"] = 0.5
            adjustments["max_positions"] = 1
        
        # Adjust based on expected gap
        if analysis.expected_gap == "gap_up":
            # Favor long strategies
            adjustments["enable_short_trades"] = False
        elif analysis.expected_gap == "gap_down":
            # Be cautious with longs
            adjustments["position_size_multiplier"] *= 0.8
            adjustments["enable_short_trades"] = True
        
        # Adjust based on risk level
        if analysis.risk_level == "high":
            adjustments["position_size_multiplier"] *= 0.7
            adjustments["risk_multiplier"] *= 0.8
        
        logger.info(f"Strategy adjustments: {adjustments}")
        return adjustments


def fetch_us_markets() -> Dict[str, MarketData]:
    """
    Fetch US market data (previous day's close).
    
    TODO: Implement actual data fetching from:
    - Yahoo Finance API
    - Alpha Vantage
    - Twelve Data
    - IEX Cloud
    
    Returns:
        Dictionary of US market data
    """
    # Placeholder implementation
    logger.warning("US market data fetching not yet implemented - using placeholder")
    
    return {
        "S&P 500": MarketData(index_name="S&P 500", close=4500.0, change_pct=0.5),
        "Nasdaq": MarketData(index_name="Nasdaq", close=14000.0, change_pct=0.8),
        "Dow Jones": MarketData(index_name="Dow Jones", close=35000.0, change_pct=0.3),
        "VIX": MarketData(index_name="VIX", close=15.0, change_pct=-2.0)
    }


def fetch_asian_markets() -> Dict[str, MarketData]:
    """
    Fetch Asian market data (current or previous close).
    
    TODO: Implement actual data fetching from:
    - Yahoo Finance API
    - Investing.com API
    - TradingView API
    
    Returns:
        Dictionary of Asian market data
    """
    # Placeholder implementation
    logger.warning("Asian market data fetching not yet implemented - using placeholder")
    
    return {
        "Nikkei 225": MarketData(index_name="Nikkei 225", close=33000.0, change_pct=0.4),
        "Hang Seng": MarketData(index_name="Hang Seng", close=18000.0, change_pct=-0.2),
        "Singapore STI": MarketData(index_name="Singapore STI", close=3200.0, change_pct=0.1),
        "KOSPI": MarketData(index_name="KOSPI", close=2500.0, change_pct=0.3)
    }


def fetch_global_news() -> List[str]:
    """
    Fetch global financial news headlines.
    
    TODO: Implement actual news fetching from:
    - Bloomberg API
    - Reuters API
    - Financial Times
    - CNBC
    
    Returns:
        List of news headlines
    """
    # Placeholder implementation
    logger.warning("Global news fetching not yet implemented - using placeholder")
    
    return [
        "Fed signals potential rate cut in Q2",
        "Tech stocks rally on strong earnings",
        "Oil prices surge on supply concerns",
        "Asian markets mixed on China data"
    ]
