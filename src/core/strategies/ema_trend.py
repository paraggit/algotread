"""
EMA Trend Strategy.

Entry conditions (Long):
- EMA(9) crosses above EMA(21)
- Price > VWAP
- Optional: RSI confirmation

Stop loss: ATR-based or below recent swing low
Target: Risk-reward ratio based
"""

from typing import Optional

import pandas as pd

from src.core.indicators import (
    is_ema_crossover_bullish,
    is_ema_crossover_bearish,
    calculate_swing_levels
)
from src.core.strategies.base import BaseStrategy
from src.data.models import (
    TradeInstruction,
    StrategySignal,
    OrderType,
    MarketRegime,
    Sentiment
)


class EMATrendStrategy(BaseStrategy):
    """EMA trend following strategy."""
    
    def __init__(
        self,
        ema_fast: int = 9,
        ema_slow: int = 21,
        use_vwap_filter: bool = True,
        use_rsi_filter: bool = False,
        rsi_threshold: float = 50.0,
        atr_sl_multiplier: float = 2.0,
        reward_ratio: float = 1.5,
        max_risk_pct: float = 0.02,
        allow_short: bool = False
    ):
        """
        Initialize EMA trend strategy.
        
        Args:
            ema_fast: Fast EMA period (default 9)
            ema_slow: Slow EMA period (default 21)
            use_vwap_filter: Require price > VWAP for long (default True)
            use_rsi_filter: Use RSI confirmation (default False)
            rsi_threshold: RSI threshold if filter enabled (default 50)
            atr_sl_multiplier: ATR multiplier for stop loss (default 2.0)
            reward_ratio: Risk-reward ratio (default 1.5)
            max_risk_pct: Maximum risk per trade (default 0.02)
            allow_short: Allow short trades (default False)
        """
        super().__init__("ema_trend")
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.use_vwap_filter = use_vwap_filter
        self.use_rsi_filter = use_rsi_filter
        self.rsi_threshold = rsi_threshold
        self.atr_sl_multiplier = atr_sl_multiplier
        self.reward_ratio = reward_ratio
        self.max_risk_pct = max_risk_pct
        self.allow_short = allow_short
    
    def evaluate(
        self,
        df: pd.DataFrame,
        current_position: Optional[str] = None,
        regime: Optional[MarketRegime] = None,
        sentiment: Optional[Sentiment] = None
    ) -> TradeInstruction:
        """Evaluate EMA trend strategy."""
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
        elif current_position == "short" and self.allow_short:
            return self._check_exit_short(df, symbol, current_price)
        
        # Check entry conditions
        long_signal = self._check_entry_long(df, symbol, current_price, sentiment)
        if long_signal.signal != StrategySignal.NO_TRADE:
            return long_signal
        
        if self.allow_short:
            short_signal = self._check_entry_short(df, symbol, current_price, sentiment)
            return short_signal
        
        return self._create_no_trade_instruction(symbol, "No signal")
    
    def _check_entry_long(
        self,
        df: pd.DataFrame,
        symbol: str,
        current_price: float,
        sentiment: Optional[Sentiment]
    ) -> TradeInstruction:
        """Check long entry conditions."""
        # Check EMA crossover
        if not is_ema_crossover_bullish(df, lookback=2):
            return self._create_no_trade_instruction(
                symbol,
                "No bullish EMA crossover"
            )
        
        # Check VWAP filter
        if self.use_vwap_filter:
            if "vwap" not in df.columns:
                return self._create_no_trade_instruction(
                    symbol,
                    "VWAP not calculated"
                )
            
            current_vwap = df["vwap"].iloc[-1]
            if pd.isna(current_vwap) or current_price <= current_vwap:
                return self._create_no_trade_instruction(
                    symbol,
                    f"Price {current_price:.2f} not above VWAP {current_vwap:.2f}"
                )
        
        # Check RSI filter
        if self.use_rsi_filter:
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
        
        # Check sentiment
        if sentiment and sentiment.is_event_risky:
            return self._create_no_trade_instruction(
                symbol,
                f"Risky event detected: {sentiment.rationale}"
            )
        
        # Calculate stop loss and target
        atr = df["atr"].iloc[-1] if "atr" in df.columns else 0.0
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
        
        target = self._calculate_target(
            current_price,
            stop_loss,
            self.reward_ratio,
            is_long=True
        )
        
        ema_fast_val = df["ema_fast"].iloc[-1]
        ema_slow_val = df["ema_slow"].iloc[-1]
        
        return TradeInstruction(
            signal=StrategySignal.ENTRY_LONG,
            symbol=symbol,
            quantity=0,  # Will be calculated by risk manager
            stop_loss=stop_loss,
            target=target,
            reason=(
                f"Bullish EMA crossover: EMA({self.ema_fast})={ema_fast_val:.2f} "
                f"> EMA({self.ema_slow})={ema_slow_val:.2f}, price > VWAP"
            ),
            strategy_name=self.name,
            entry_price=current_price,
            order_type=OrderType.MARKET
        )
    
    def _check_entry_short(
        self,
        df: pd.DataFrame,
        symbol: str,
        current_price: float,
        sentiment: Optional[Sentiment]
    ) -> TradeInstruction:
        """Check short entry conditions."""
        # Check EMA crossover
        if not is_ema_crossover_bearish(df, lookback=2):
            return self._create_no_trade_instruction(
                symbol,
                "No bearish EMA crossover"
            )
        
        # Check VWAP filter (price should be below VWAP for short)
        if self.use_vwap_filter:
            if "vwap" not in df.columns:
                return self._create_no_trade_instruction(
                    symbol,
                    "VWAP not calculated"
                )
            
            current_vwap = df["vwap"].iloc[-1]
            if pd.isna(current_vwap) or current_price >= current_vwap:
                return self._create_no_trade_instruction(
                    symbol,
                    f"Price {current_price:.2f} not below VWAP {current_vwap:.2f}"
                )
        
        # Check RSI filter (RSI should be below threshold for short)
        if self.use_rsi_filter:
            if "rsi" not in df.columns:
                return self._create_no_trade_instruction(
                    symbol,
                    "RSI not calculated"
                )
            
            current_rsi = df["rsi"].iloc[-1]
            if pd.isna(current_rsi) or current_rsi > (100 - self.rsi_threshold):
                return self._create_no_trade_instruction(
                    symbol,
                    f"RSI {current_rsi:.2f} above threshold {100 - self.rsi_threshold}"
                )
        
        # Check sentiment
        if sentiment and sentiment.is_event_risky:
            return self._create_no_trade_instruction(
                symbol,
                f"Risky event detected: {sentiment.rationale}"
            )
        
        # Calculate stop loss and target
        atr = df["atr"].iloc[-1] if "atr" in df.columns else 0.0
        swing_high, swing_low = calculate_swing_levels(df, lookback=5)
        
        if swing_high > 0 and swing_high > current_price:
            stop_loss = swing_high
        elif atr > 0:
            stop_loss = self._calculate_atr_stop_loss(
                current_price,
                atr,
                self.atr_sl_multiplier,
                is_long=False
            )
        else:
            return self._create_no_trade_instruction(
                symbol,
                "Cannot calculate stop loss"
            )
        
        target = self._calculate_target(
            current_price,
            stop_loss,
            self.reward_ratio,
            is_long=False
        )
        
        ema_fast_val = df["ema_fast"].iloc[-1]
        ema_slow_val = df["ema_slow"].iloc[-1]
        
        return TradeInstruction(
            signal=StrategySignal.ENTRY_SHORT,
            symbol=symbol,
            quantity=0,  # Will be calculated by risk manager
            stop_loss=stop_loss,
            target=target,
            reason=(
                f"Bearish EMA crossover: EMA({self.ema_fast})={ema_fast_val:.2f} "
                f"< EMA({self.ema_slow})={ema_slow_val:.2f}, price < VWAP"
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
        # Exit if bearish crossover
        if is_ema_crossover_bearish(df, lookback=2):
            return TradeInstruction(
                signal=StrategySignal.EXIT_LONG,
                symbol=symbol,
                quantity=0,
                reason="Bearish EMA crossover",
                strategy_name=self.name,
                entry_price=current_price,
                order_type=OrderType.MARKET
            )
        
        return self._create_no_trade_instruction(symbol, "Holding position")
    
    def _check_exit_short(
        self,
        df: pd.DataFrame,
        symbol: str,
        current_price: float
    ) -> TradeInstruction:
        """Check short exit conditions."""
        # Exit if bullish crossover
        if is_ema_crossover_bullish(df, lookback=2):
            return TradeInstruction(
                signal=StrategySignal.EXIT_SHORT,
                symbol=symbol,
                quantity=0,
                reason="Bullish EMA crossover",
                strategy_name=self.name,
                entry_price=current_price,
                order_type=OrderType.MARKET
            )
        
        return self._create_no_trade_instruction(symbol, "Holding position")
    
    def get_parameters(self) -> dict:
        """Get strategy parameters."""
        return {
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "use_vwap_filter": self.use_vwap_filter,
            "use_rsi_filter": self.use_rsi_filter,
            "rsi_threshold": self.rsi_threshold,
            "atr_sl_multiplier": self.atr_sl_multiplier,
            "reward_ratio": self.reward_ratio,
            "max_risk_pct": self.max_risk_pct,
            "allow_short": self.allow_short
        }
