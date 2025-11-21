"""
Market Regime Classifier using LLM.

IMPORTANT: This module provides ADVISORY information only.
It does NOT trigger trades. Strategies use regime to enable/disable themselves.
"""

from typing import Optional

from loguru import logger

from src.data.models import RegimeClassification, MarketRegime
from src.llm.llm_client import LLMClient


class RegimeClassifier:
    """Classify market regime using LLM."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize regime classifier.
        
        Args:
            llm_client: LLM client instance
        """
        self.llm_client = llm_client
    
    def classify(
        self,
        index_atr: float,
        index_volatility: float,
        advance_decline_ratio: float,
        gap_pct: float,
        intraday_range_pct: float,
        volume_ratio: float
    ) -> Optional[RegimeClassification]:
        """
        Classify market regime based on market data.
        
        Args:
            index_atr: Index ATR value
            index_volatility: Realized volatility
            advance_decline_ratio: Advance/decline ratio
            gap_pct: Gap up/down percentage at open
            intraday_range_pct: Intraday range as percentage
            volume_ratio: Current volume vs average
            
        Returns:
            RegimeClassification or None if classification fails
        """
        system_prompt = """You are a market regime classifier for Indian equity markets.
Your role is to classify the current market regime based on technical indicators.

CRITICAL: You are providing ADVISORY information only. You do NOT trigger trades.
Your output will be used by strategies to enable/disable themselves.

You must respond with ONLY a JSON object in this exact format:
{
  "regime": "TRENDING_UP" | "TRENDING_DOWN" | "RANGE_BOUND" | "HIGH_VOLATILITY_NOISE",
  "confidence": 0.0-1.0,
  "comment": "short human-readable note (max 100 chars)"
}

Regime definitions:
- TRENDING_UP: Strong upward momentum, low volatility, positive breadth
- TRENDING_DOWN: Strong downward momentum, low volatility, negative breadth
- RANGE_BOUND: Sideways movement, moderate volatility, mixed breadth
- HIGH_VOLATILITY_NOISE: High volatility, unpredictable movements, avoid mean reversion
"""
        
        user_prompt = f"""Classify the current market regime based on these indicators:

Index ATR: {index_atr:.2f}
Realized Volatility: {index_volatility:.2f}%
Advance/Decline Ratio: {advance_decline_ratio:.2f}
Gap at Open: {gap_pct:+.2f}%
Intraday Range: {intraday_range_pct:.2f}%
Volume Ratio: {volume_ratio:.2f}x

Provide your classification in JSON format."""
        
        try:
            response = self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0
            )
            
            if not response:
                logger.error("Empty response from LLM for regime classification")
                return None
            
            # Validate and parse response
            regime_str = response.get("regime", "").upper()
            
            # Map string to enum
            regime_map = {
                "TRENDING_UP": MarketRegime.TRENDING_UP,
                "TRENDING_DOWN": MarketRegime.TRENDING_DOWN,
                "RANGE_BOUND": MarketRegime.RANGE_BOUND,
                "HIGH_VOLATILITY_NOISE": MarketRegime.HIGH_VOLATILITY_NOISE
            }
            
            if regime_str not in regime_map:
                logger.error(f"Invalid regime from LLM: {regime_str}")
                return None
            
            regime = regime_map[regime_str]
            confidence = float(response.get("confidence", 0.0))
            comment = response.get("comment", "")
            
            classification = RegimeClassification(
                regime=regime,
                confidence=confidence,
                comment=comment
            )
            
            logger.info(
                f"Market regime classified: {regime.value} "
                f"(confidence: {confidence:.2f}, comment: {comment})"
            )
            
            return classification
            
        except Exception as e:
            logger.error(f"Error classifying regime: {e}")
            return None
    
    def classify_simple(
        self,
        index_data: dict
    ) -> Optional[RegimeClassification]:
        """
        Simplified classification interface.
        
        Args:
            index_data: Dictionary with keys: atr, volatility, adv_dec_ratio, gap_pct, range_pct, volume_ratio
            
        Returns:
            RegimeClassification or None
        """
        return self.classify(
            index_atr=index_data.get("atr", 0.0),
            index_volatility=index_data.get("volatility", 0.0),
            advance_decline_ratio=index_data.get("adv_dec_ratio", 1.0),
            gap_pct=index_data.get("gap_pct", 0.0),
            intraday_range_pct=index_data.get("range_pct", 0.0),
            volume_ratio=index_data.get("volume_ratio", 1.0)
        )
