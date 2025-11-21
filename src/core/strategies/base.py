"""
Base strategy interface and common utilities.
All strategies must inherit from BaseStrategy.
"""

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from src.data.models import TradeInstruction, StrategySignal, MarketRegime, Sentiment


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""
    
    def __init__(self, name: str):
        """
        Initialize strategy.
        
        Args:
            name: Strategy name
        """
        self.name = name
    
    @abstractmethod
    def evaluate(
        self,
        df: pd.DataFrame,
        current_position: Optional[str] = None,
        regime: Optional[MarketRegime] = None,
        sentiment: Optional[Sentiment] = None
    ) -> TradeInstruction:
        """
        Evaluate strategy and generate trade instruction.
        
        Args:
            df: DataFrame with OHLCV data and indicators
            current_position: Current position state ("long", "short", or None)
            regime: Current market regime (from LLM)
            sentiment: Current sentiment (from LLM)
            
        Returns:
            TradeInstruction with signal and parameters
        """
        pass
    
    @abstractmethod
    def get_parameters(self) -> dict:
        """
        Get strategy parameters.
        
        Returns:
            Dictionary of parameter names and values
        """
        pass
    
    def _create_no_trade_instruction(self, symbol: str, reason: str = "No signal") -> TradeInstruction:
        """
        Create a NO_TRADE instruction.
        
        Args:
            symbol: Trading symbol
            reason: Reason for no trade
            
        Returns:
            TradeInstruction with NO_TRADE signal
        """
        return TradeInstruction(
            signal=StrategySignal.NO_TRADE,
            symbol=symbol,
            quantity=0,
            reason=reason,
            strategy_name=self.name
        )
    
    def _calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss: float,
        max_risk_pct: float = 0.02
    ) -> int:
        """
        Calculate position size based on risk management.
        
        Args:
            capital: Available capital
            entry_price: Entry price
            stop_loss: Stop loss price
            max_risk_pct: Maximum risk as percentage of capital (default 2%)
            
        Returns:
            Number of shares to trade
        """
        if entry_price <= 0 or stop_loss <= 0:
            return 0
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            return 0
        
        # Calculate maximum loss amount
        max_loss = capital * max_risk_pct
        
        # Calculate quantity
        quantity = int(max_loss / risk_per_share)
        
        return max(1, quantity)  # At least 1 share
    
    def _calculate_atr_stop_loss(
        self,
        current_price: float,
        atr: float,
        multiplier: float = 2.0,
        is_long: bool = True
    ) -> float:
        """
        Calculate ATR-based stop loss.
        
        Args:
            current_price: Current price
            atr: Average True Range value
            multiplier: ATR multiplier (default 2.0)
            is_long: True for long position, False for short
            
        Returns:
            Stop loss price
        """
        if is_long:
            return current_price - (atr * multiplier)
        else:
            return current_price + (atr * multiplier)
    
    def _calculate_target(
        self,
        entry_price: float,
        stop_loss: float,
        reward_ratio: float = 1.5,
        is_long: bool = True
    ) -> float:
        """
        Calculate target price based on risk-reward ratio.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            reward_ratio: Reward-to-risk ratio (default 1.5)
            is_long: True for long position, False for short
            
        Returns:
            Target price
        """
        risk = abs(entry_price - stop_loss)
        reward = risk * reward_ratio
        
        if is_long:
            return entry_price + reward
        else:
            return entry_price - reward
