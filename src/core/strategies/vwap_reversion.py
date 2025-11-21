"""
VWAP Mean Reversion Strategy.

Only active in RANGE_BOUND regime.
Entry conditions:
- Price deviates significantly from VWAP
- RSI is overbought (for short) or oversold (for long)

Stop loss: Tight, based on recent swing
Target: Return to VWAP or small profit
"""

from typing import Optional

import pandas as pd

from src.core.indicators import calculate_swing_levels
from src.core.strategies.base import BaseStrategy
from src.data.models import (
    TradeInstruction,
    StrategySignal,
    OrderType,
    MarketRegime,
    Sentiment
)


class VWAPReversionStrategy(BaseStrategy):
    """VWAP mean reversion strategy for range-bound markets."""
    
    def __init__(
        self,
        vwap_deviation_pct: float = 1.0,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        atr_sl_multiplier: float = 1.0,
        reward_ratio: float = 1.0,
        max_risk_pct: float = 0.01  # Lower risk for mean reversion
    ):
        """
        Initialize VWAP reversion strategy.
        
        Args:
            vwap_deviation_pct: Required deviation from VWAP in % (default 1.0)
            rsi_oversold: RSI oversold threshold (default 30)
            rsi_overbought: RSI overbought threshold (default 70)
            atr_sl_multiplier: ATR multiplier for stop loss (default 1.0, tighter)
            reward_ratio: Risk-reward ratio (default 1.0)
            max_risk_pct: Maximum risk per trade (default 0.01, lower for mean reversion)
        """
        super().__init__("vwap_reversion")
        self.vwap_deviation_pct = vwap_deviation_pct
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
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
        """Evaluate VWAP reversion strategy."""
        if len(df) == 0:
            return self._create_no_trade_instruction(
                symbol=df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN",
                reason="No data available"
            )
        
        symbol = df["symbol"].iloc[-1] if "symbol" in df.columns else "UNKNOWN"
        
        # Only trade in range-bound regime
        if regime and regime != MarketRegime.RANGE_BOUND:
            return self._create_no_trade_instruction(
                symbol,
                f"Strategy only active in RANGE_BOUND regime, current: {regime.value}"
            )
        
        current_price = df["close"].iloc[-1]
        
        # If we have a position, check exit conditions
        if current_position == "long":
            return self._check_exit_long(df, symbol, current_price)
        elif current_position == "short":
            return self._check_exit_short(df, symbol, current_price)
        
        # Check entry conditions
        long_signal = self._check_entry_long(df, symbol, current_price, sentiment)
        if long_signal.signal != StrategySignal.NO_TRADE:
            return long_signal
        
        short_signal = self._check_entry_short(df, symbol, current_price, sentiment)
        return short_signal
    
    def _check_entry_long(
        self,
        df: pd.DataFrame,
        symbol: str,
        current_price: float,
        sentiment: Optional[Sentiment]
    ) -> TradeInstruction:
        """Check long entry conditions (price below VWAP, RSI oversold)."""
        # Check VWAP
        if "vwap" not in df.columns:
            return self._create_no_trade_instruction(
                symbol,
                "VWAP not calculated"
            )
        
        current_vwap = df["vwap"].iloc[-1]
        if pd.isna(current_vwap):
            return self._create_no_trade_instruction(
                symbol,
                "VWAP is NaN"
            )
        
        # Check if price is significantly below VWAP
        deviation_pct = ((current_price - current_vwap) / current_vwap) * 100
        if deviation_pct >= -self.vwap_deviation_pct:
            return self._create_no_trade_instruction(
                symbol,
                f"Price deviation {deviation_pct:.2f}% not below -{self.vwap_deviation_pct}%"
            )
        
        # Check RSI oversold
        if "rsi" not in df.columns:
            return self._create_no_trade_instruction(
                symbol,
                "RSI not calculated"
            )
        
        current_rsi = df["rsi"].iloc[-1]
        if pd.isna(current_rsi) or current_rsi > self.rsi_oversold:
            return self._create_no_trade_instruction(
                symbol,
                f"RSI {current_rsi:.2f} not oversold (threshold {self.rsi_oversold})"
            )
        
        # Check sentiment
        if sentiment and sentiment.is_event_risky:
            return self._create_no_trade_instruction(
                symbol,
                f"Risky event detected: {sentiment.rationale}"
            )
        
        # Calculate stop loss and target
        atr = df["atr"].iloc[-1] if "atr" in df.columns else 0.0
        swing_high, swing_low = calculate_swing_levels(df, lookback=3)
        
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
        
        # Target is VWAP or risk-reward based
        target = min(
            current_vwap,
            self._calculate_target(current_price, stop_loss, self.reward_ratio, is_long=True)
        )
        
        return TradeInstruction(
            signal=StrategySignal.ENTRY_LONG,
            symbol=symbol,
            quantity=0,
            stop_loss=stop_loss,
            target=target,
            reason=(
                f"VWAP reversion long: price {current_price:.2f} is {deviation_pct:.2f}% "
                f"below VWAP {current_vwap:.2f}, RSI oversold at {current_rsi:.2f}"
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
        """Check short entry conditions (price above VWAP, RSI overbought)."""
        # Check VWAP
        if "vwap" not in df.columns:
            return self._create_no_trade_instruction(
                symbol,
                "VWAP not calculated"
            )
        
        current_vwap = df["vwap"].iloc[-1]
        if pd.isna(current_vwap):
            return self._create_no_trade_instruction(
                symbol,
                "VWAP is NaN"
            )
        
        # Check if price is significantly above VWAP
        deviation_pct = ((current_price - current_vwap) / current_vwap) * 100
        if deviation_pct <= self.vwap_deviation_pct:
            return self._create_no_trade_instruction(
                symbol,
                f"Price deviation {deviation_pct:.2f}% not above {self.vwap_deviation_pct}%"
            )
        
        # Check RSI overbought
        if "rsi" not in df.columns:
            return self._create_no_trade_instruction(
                symbol,
                "RSI not calculated"
            )
        
        current_rsi = df["rsi"].iloc[-1]
        if pd.isna(current_rsi) or current_rsi < self.rsi_overbought:
            return self._create_no_trade_instruction(
                symbol,
                f"RSI {current_rsi:.2f} not overbought (threshold {self.rsi_overbought})"
            )
        
        # Check sentiment
        if sentiment and sentiment.is_event_risky:
            return self._create_no_trade_instruction(
                symbol,
                f"Risky event detected: {sentiment.rationale}"
            )
        
        # Calculate stop loss and target
        atr = df["atr"].iloc[-1] if "atr" in df.columns else 0.0
        swing_high, swing_low = calculate_swing_levels(df, lookback=3)
        
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
        
        # Target is VWAP or risk-reward based
        target = max(
            current_vwap,
            self._calculate_target(current_price, stop_loss, self.reward_ratio, is_long=False)
        )
        
        return TradeInstruction(
            signal=StrategySignal.ENTRY_SHORT,
            symbol=symbol,
            quantity=0,
            stop_loss=stop_loss,
            target=target,
            reason=(
                f"VWAP reversion short: price {current_price:.2f} is {deviation_pct:.2f}% "
                f"above VWAP {current_vwap:.2f}, RSI overbought at {current_rsi:.2f}"
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
        # Exit if price reached VWAP
        if "vwap" in df.columns:
            current_vwap = df["vwap"].iloc[-1]
            if not pd.isna(current_vwap) and current_price >= current_vwap:
                return TradeInstruction(
                    signal=StrategySignal.EXIT_LONG,
                    symbol=symbol,
                    quantity=0,
                    reason="Price reached VWAP",
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
        # Exit if price reached VWAP
        if "vwap" in df.columns:
            current_vwap = df["vwap"].iloc[-1]
            if not pd.isna(current_vwap) and current_price <= current_vwap:
                return TradeInstruction(
                    signal=StrategySignal.EXIT_SHORT,
                    symbol=symbol,
                    quantity=0,
                    reason="Price reached VWAP",
                    strategy_name=self.name,
                    entry_price=current_price,
                    order_type=OrderType.MARKET
                )
        
        return self._create_no_trade_instruction(symbol, "Holding position")
    
    def get_parameters(self) -> dict:
        """Get strategy parameters."""
        return {
            "vwap_deviation_pct": self.vwap_deviation_pct,
            "rsi_oversold": self.rsi_oversold,
            "rsi_overbought": self.rsi_overbought,
            "atr_sl_multiplier": self.atr_sl_multiplier,
            "reward_ratio": self.reward_ratio,
            "max_risk_pct": self.max_risk_pct
        }
