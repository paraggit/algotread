"""
ORB (Opening Range Breakout) + Supertrend Strategy.

Entry conditions (Long):
- Price breaks above ORB high
- Supertrend is bullish
- Volume > threshold × recent average
- RSI > threshold

Stop loss: ATR-based or last swing low
Target: Risk-reward ratio based
"""

from typing import Optional

import pandas as pd

from src.core.indicators import (
    calculate_orb_levels,
    calculate_swing_levels,
    is_bullish_supertrend
)
from src.core.strategies.base import BaseStrategy
from src.data.models import (
    TradeInstruction,
    StrategySignal,
    OrderType,
    MarketRegime,
    Sentiment
)


class ORBSupertrendStrategy(BaseStrategy):
    """ORB + Supertrend breakout strategy."""
    
    def __init__(
        self,
        orb_period_minutes: int = 15,
        interval_minutes: int = 5,
        volume_multiplier: float = 1.5,
        rsi_threshold: float = 55.0,
        supertrend_period: int = 7,
        supertrend_multiplier: float = 3.0,
        atr_sl_multiplier: float = 2.0,
        reward_ratio: float = 1.5,
        max_risk_pct: float = 0.02
    ):
        """
        Initialize ORB + Supertrend strategy.
        
        Args:
            orb_period_minutes: ORB period in minutes (default 15)
            interval_minutes: Candle interval in minutes (default 5)
            volume_multiplier: Volume threshold multiplier (default 1.5)
            rsi_threshold: RSI threshold for entry (default 55)
            supertrend_period: Supertrend period (default 7)
            supertrend_multiplier: Supertrend multiplier (default 3.0)
            atr_sl_multiplier: ATR multiplier for stop loss (default 2.0)
            reward_ratio: Risk-reward ratio (default 1.5)
            max_risk_pct: Maximum risk per trade (default 0.02)
        """
        super().__init__("orb_supertrend")
        self.orb_period_minutes = orb_period_minutes
        self.interval_minutes = interval_minutes
        self.volume_multiplier = volume_multiplier
        self.rsi_threshold = rsi_threshold
        self.supertrend_period = supertrend_period
        self.supertrend_multiplier = supertrend_multiplier
        self.atr_sl_multiplier = atr_sl_multiplier
        self.reward_ratio = reward_ratio
        self.max_risk_pct = max_risk_pct
    
    def evaluate(
        self,
        df: pd.DataFrame,
        current_position: Optional[str] = None,
        regime: Optional[MarketRegime] = None,
        sentiment: Optional[Sentiment] = None
    ) -> TradeInstruction:
        """Evaluate ORB + Supertrend strategy."""
        if len(df) == 0:
            return self._create_no_trade_instruction(
                symbol=df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN",
                reason="No data available"
            )
        
        symbol = df["symbol"].iloc[-1] if "symbol" in df.columns else "UNKNOWN"
        current_price = df["close"].iloc[-1]
        
        # If we have a position, check exit conditions
        if current_position == "long":
            return self._check_exit_long(df, symbol, current_price)
        
        # Check entry conditions for long
        return self._check_entry_long(df, symbol, current_price, sentiment)
    
    def _check_entry_long(
        self,
        df: pd.DataFrame,
        symbol: str,
        current_price: float,
        sentiment: Optional[Sentiment]
    ) -> TradeInstruction:
        """Check long entry conditions."""
        # Calculate ORB levels
        orb_high, orb_low = calculate_orb_levels(
            df,
            self.orb_period_minutes,
            self.interval_minutes
        )
        
        if orb_high == 0.0 or orb_low == 0.0:
            return self._create_no_trade_instruction(
                symbol,
                "ORB levels not yet established"
            )
        
        # Check if price broke above ORB high
        if current_price <= orb_high:
            return self._create_no_trade_instruction(
                symbol,
                f"Price {current_price:.2f} has not broken ORB high {orb_high:.2f}"
            )
        
        # Check Supertrend is bullish
        if not is_bullish_supertrend(df, self.supertrend_period, self.supertrend_multiplier):
            return self._create_no_trade_instruction(
                symbol,
                "Supertrend is not bullish"
            )
        
        # Check volume
        if "volume_ratio" not in df.columns:
            return self._create_no_trade_instruction(
                symbol,
                "Volume ratio not calculated"
            )
        
        current_volume_ratio = df["volume_ratio"].iloc[-1]
        if pd.isna(current_volume_ratio) or current_volume_ratio < self.volume_multiplier:
            return self._create_no_trade_instruction(
                symbol,
                f"Volume ratio {current_volume_ratio:.2f} below threshold {self.volume_multiplier}"
            )
        
        # Check RSI
        if "rsi" not in df.columns:
            return self._create_no_trade_instruction(
                symbol,
                "RSI not calculated"
            )
        
        current_rsi = df["rsi"].iloc[-1]
        if pd.isna(current_rsi) or current_rsi < self.rsi_threshold:
            return self._create_no_trade_instruction(
                symbol,
                f"RSI {current_rsi:.2f} below threshold {self.rsi_threshold}"
            )
        
        # Check sentiment (if risky event, reduce position or skip)
        if sentiment and sentiment.is_event_risky:
            return self._create_no_trade_instruction(
                symbol,
                f"Risky event detected: {sentiment.rationale}"
            )
        
        # All conditions met - calculate entry parameters
        atr = df["atr"].iloc[-1] if "atr" in df.columns else 0.0
        
        # Calculate stop loss (use swing low or ATR-based)
        swing_high, swing_low = calculate_swing_levels(df, lookback=5)
        
        if swing_low > 0 and swing_low < current_price:
            stop_loss = swing_low
        elif atr > 0:
            stop_loss = self._calculate_atr_stop_loss(
                current_price,
                atr,
                self.atr_sl_multiplier,
                is_long=True
            )
        else:
            return self._create_no_trade_instruction(
                symbol,
                "Cannot calculate stop loss"
            )
        
        # Calculate target
        target = self._calculate_target(
            current_price,
            stop_loss,
            self.reward_ratio,
            is_long=True
        )
        
        # Calculate position size (will be done by risk manager, but provide estimate)
        # For now, set quantity to 0 and let risk manager calculate
        
        return TradeInstruction(
            signal=StrategySignal.ENTRY_LONG,
            symbol=symbol,
            quantity=0,  # Will be calculated by risk manager
            stop_loss=stop_loss,
            target=target,
            reason=(
                f"ORB breakout: price {current_price:.2f} > ORB high {orb_high:.2f}, "
                f"Supertrend bullish, volume ratio {current_volume_ratio:.2f}, "
                f"RSI {current_rsi:.2f}"
            ),
            strategy_name=self.name,
            entry_price=current_price,
            order_type=OrderType.MARKET
        )
    
    def _check_exit_long(
        self,
        df: pd.DataFrame,
        symbol: str,
        current_price: float
    ) -> TradeInstruction:
        """Check long exit conditions."""
        # Check if Supertrend turned bearish
        if not is_bullish_supertrend(df, self.supertrend_period, self.supertrend_multiplier):
            return TradeInstruction(
                signal=StrategySignal.EXIT_LONG,
                symbol=symbol,
                quantity=0,  # Will be filled by position manager
                reason="Supertrend turned bearish",
                strategy_name=self.name,
                entry_price=current_price,
                order_type=OrderType.MARKET
            )
        
        # Otherwise, hold position (SL and target will be managed by position manager)
        return self._create_no_trade_instruction(
            symbol,
            "Holding position"
        )
    
    def get_parameters(self) -> dict:
        """Get strategy parameters."""
        return {
            "orb_period_minutes": self.orb_period_minutes,
            "interval_minutes": self.interval_minutes,
            "volume_multiplier": self.volume_multiplier,
            "rsi_threshold": self.rsi_threshold,
            "supertrend_period": self.supertrend_period,
            "supertrend_multiplier": self.supertrend_multiplier,
            "atr_sl_multiplier": self.atr_sl_multiplier,
            "reward_ratio": self.reward_ratio,
            "max_risk_pct": self.max_risk_pct
        }
