"""
Sentiment Analyzer using LLM.

IMPORTANT: This module provides ADVISORY information only.
It does NOT trigger trades. Sentiment is used to adjust position size or block trades.
"""

from typing import List, Optional

from loguru import logger

from src.data.models import SentimentAnalysis, Sentiment
from src.llm.llm_client import LLMClient


class SentimentAnalyzer:
    """Analyze news sentiment using LLM."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize sentiment analyzer.
        
        Args:
            llm_client: LLM client instance
        """
        self.llm_client = llm_client
    
    def analyze(
        self,
        ticker: str,
        headlines: List[str],
        price_change_pct: Optional[float] = None
    ) -> Optional[SentimentAnalysis]:
        """
        Analyze sentiment for a ticker based on news.
        
        Args:
            ticker: Stock ticker symbol
            headlines: List of news headlines
            price_change_pct: Recent price change percentage (optional)
            
        Returns:
            SentimentAnalysis or None if analysis fails
        """
        if not headlines:
            logger.warning(f"No headlines provided for {ticker}")
            return None
        
        system_prompt = """You are a financial news sentiment analyzer for Indian equity markets.
Your role is to analyze news sentiment and identify risky events.

CRITICAL: You are providing ADVISORY information only. You do NOT trigger trades.
Your output will be used to adjust position sizing or block trades, NOT to initiate them.

You must respond with ONLY a JSON object in this exact format:
{
  "ticker": "SYMBOL",
  "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
  "confidence": 0.0-1.0,
  "is_event_risky": true | false,
  "rationale": "1 sentence explanation (max 150 chars)"
}

Risky events include:
- Earnings announcements
- Regulatory actions
- Major corporate actions (mergers, acquisitions)
- Unexpected management changes
- Legal issues
- Geopolitical events affecting the company
"""
        
        headlines_text = "\n".join([f"- {h}" for h in headlines[:10]])  # Limit to 10 headlines
        
        price_info = ""
        if price_change_pct is not None:
            price_info = f"\nRecent price change: {price_change_pct:+.2f}%"
        
        user_prompt = f"""Analyze sentiment for {ticker} based on these headlines:

{headlines_text}{price_info}

Provide your analysis in JSON format."""
        
        try:
            response = self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0
            )
            
            if not response:
                logger.error(f"Empty response from LLM for sentiment analysis of {ticker}")
                return None
            
            # Validate and parse response
            sentiment_str = response.get("sentiment", "").upper()
            
            # Map string to enum
            sentiment_map = {
                "POSITIVE": Sentiment.POSITIVE,
                "NEGATIVE": Sentiment.NEGATIVE,
                "NEUTRAL": Sentiment.NEUTRAL
            }
            
            if sentiment_str not in sentiment_map:
                logger.error(f"Invalid sentiment from LLM: {sentiment_str}")
                return None
            
            sentiment = sentiment_map[sentiment_str]
            confidence = float(response.get("confidence", 0.0))
            is_event_risky = bool(response.get("is_event_risky", False))
            rationale = response.get("rationale", "")
            
            analysis = SentimentAnalysis(
                ticker=ticker,
                sentiment=sentiment,
                confidence=confidence,
                is_event_risky=is_event_risky,
                rationale=rationale
            )
            
            logger.info(
                f"Sentiment for {ticker}: {sentiment.value} "
                f"(confidence: {confidence:.2f}, risky: {is_event_risky}, "
                f"rationale: {rationale})"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment for {ticker}: {e}")
            return None
    
    def analyze_batch(
        self,
        tickers_data: List[dict]
    ) -> List[SentimentAnalysis]:
        """
        Analyze sentiment for multiple tickers.
        
        Args:
            tickers_data: List of dicts with keys: ticker, headlines, price_change_pct
            
        Returns:
            List of SentimentAnalysis results
        """
        results = []
        
        for data in tickers_data:
            ticker = data.get("ticker", "")
            headlines = data.get("headlines", [])
            price_change_pct = data.get("price_change_pct")
            
            analysis = self.analyze(ticker, headlines, price_change_pct)
            if analysis:
                results.append(analysis)
        
        return results
