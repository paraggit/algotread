"""
Risk Management Module.

Enforces hard-coded risk rules:
- Position sizing (1-2% risk per trade)
- Daily loss limits
- Time filters
- Kill switch

CRITICAL: This module must NEVER be influenced by LLM outputs.
All risk decisions are deterministic and rule-based.
"""

from datetime import datetime, time
from typing import Optional

from loguru import logger

from src.config import RiskConfig
from src.data.models import TradeInstruction, Portfolio, StrategySignal


class RiskManager:
    """Risk management and position sizing."""
    
    def __init__(self, config: RiskConfig, initial_capital: float):
        """
        Initialize risk manager.
        
        Args:
            config: Risk configuration
            initial_capital: Initial capital amount
        """
        self.config = config
        self.initial_capital = initial_capital
        self.kill_switch_active = False
        self.kill_switch_reason = ""
    
    def validate_trade(
        self,
        instruction: TradeInstruction,
        portfolio: Portfolio,
        current_time: Optional[datetime] = None
    ) -> tuple[bool, str]:
        """
        Validate if trade is allowed based on risk rules.
        
        Args:
            instruction: Trade instruction from strategy
            portfolio: Current portfolio state
            current_time: Current time (default: now)
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Check kill switch
        if self.kill_switch_active:
            return False, f"Kill switch active: {self.kill_switch_reason}"
        
        # Only validate entry signals
        if instruction.signal not in [StrategySignal.ENTRY_LONG, StrategySignal.ENTRY_SHORT]:
            return True, "Not an entry signal"
        
        # Check daily loss limit
        daily_loss_limit = self.initial_capital * self.config.max_daily_loss
        if portfolio.daily_pnl < -daily_loss_limit:
            self._activate_kill_switch(
                f"Daily loss limit breached: {portfolio.daily_pnl:.2f} < -{daily_loss_limit:.2f}"
            )
            return False, self.kill_switch_reason
        
        # Check max losing trades per day
        if portfolio.daily_losing_trades >= self.config.max_losing_trades_per_day:
            self._activate_kill_switch(
                f"Max losing trades per day reached: {portfolio.daily_losing_trades}"
            )
            return False, self.kill_switch_reason
        
        # Check time filters
        time_allowed, time_reason = self._check_time_filters(current_time)
        if not time_allowed:
            return False, time_reason
        
        # Check if already have position in this symbol
        if instruction.symbol in portfolio.positions:
            return False, f"Already have position in {instruction.symbol}"
        
        # All checks passed
        return True, "Trade allowed"
    
    def calculate_position_size(
        self,
        instruction: TradeInstruction,
        portfolio: Portfolio
    ) -> int:
        """
        Calculate position size based on risk management rules.
        
        Args:
            instruction: Trade instruction with entry price and stop loss
            portfolio: Current portfolio state
            
        Returns:
            Number of shares to trade
        """
        if instruction.entry_price is None or instruction.stop_loss is None:
            logger.warning(f"Cannot calculate position size: missing entry_price or stop_loss")
            return 0
        
        # Calculate risk per share
        risk_per_share = abs(instruction.entry_price - instruction.stop_loss)
        
        if risk_per_share == 0:
            logger.warning(f"Cannot calculate position size: risk_per_share is 0")
            return 0
        
        # Calculate available capital (cash + unrealized P&L)
        available_capital = portfolio.get_total_value()
        
        # Calculate maximum loss amount
        max_loss = available_capital * self.config.max_risk_per_trade
        
        # Calculate quantity
        quantity = int(max_loss / risk_per_share)
        
        # Ensure we have enough cash for the trade
        required_capital = instruction.entry_price * quantity
        if required_capital > portfolio.cash:
            # Reduce quantity to fit available cash
            quantity = int(portfolio.cash / instruction.entry_price)
        
        # Ensure at least 1 share
        quantity = max(1, quantity)
        
        logger.info(
            f"Position sizing for {instruction.symbol}: "
            f"risk_per_share={risk_per_share:.2f}, "
            f"max_loss={max_loss:.2f}, "
            f"quantity={quantity}"
        )
        
        return quantity
    
    def _check_time_filters(self, current_time: datetime) -> tuple[bool, str]:
        """
        Check if trading is allowed at current time.
        
        Args:
            current_time: Current time
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        # Market hours for NSE: 9:15 AM to 3:30 PM IST
        market_open = time(9, 15)
        market_close = time(15, 30)
        
        current_time_only = current_time.time()
        
        # Check if market is open
        if current_time_only < market_open or current_time_only > market_close:
            return False, f"Market closed: current time {current_time_only}"
        
        # Check min minutes after open
        minutes_after_open = (
            current_time_only.hour * 60 + current_time_only.minute -
            (market_open.hour * 60 + market_open.minute)
        )
        
        if minutes_after_open < self.config.min_minutes_after_open:
            return False, (
                f"Too early: {minutes_after_open} minutes after open, "
                f"minimum {self.config.min_minutes_after_open}"
            )
        
        # Check cutoff time
        cutoff_parts = self.config.cutoff_time.split(":")
        cutoff = time(int(cutoff_parts[0]), int(cutoff_parts[1]))
        
        if current_time_only >= cutoff:
            return False, f"Past cutoff time: {current_time_only} >= {cutoff}"
        
        return True, "Time filters passed"
    
    def _activate_kill_switch(self, reason: str) -> None:
        """
        Activate kill switch to stop all trading.
        
        Args:
            reason: Reason for activation
        """
        self.kill_switch_active = True
        self.kill_switch_reason = reason
        logger.critical(f"KILL SWITCH ACTIVATED: {reason}")
    
    def reset_kill_switch(self) -> None:
        """Reset kill switch (use with caution)."""
        logger.warning("Kill switch reset")
        self.kill_switch_active = False
        self.kill_switch_reason = ""
    
    def reset_daily_limits(self) -> None:
        """Reset daily limits (call at start of new trading day)."""
        logger.info("Daily risk limits reset")
        # Note: Portfolio daily stats should also be reset separately
    
    def get_risk_metrics(self, portfolio: Portfolio) -> dict:
        """
        Get current risk metrics.
        
        Args:
            portfolio: Current portfolio state
            
        Returns:
            Dictionary of risk metrics
        """
        daily_loss_limit = self.initial_capital * self.config.max_daily_loss
        daily_loss_used_pct = (abs(portfolio.daily_pnl) / daily_loss_limit * 100) if portfolio.daily_pnl < 0 else 0
        
        return {
            "kill_switch_active": self.kill_switch_active,
            "kill_switch_reason": self.kill_switch_reason,
            "daily_pnl": portfolio.daily_pnl,
            "daily_loss_limit": daily_loss_limit,
            "daily_loss_used_pct": daily_loss_used_pct,
            "daily_trades": portfolio.daily_trades,
            "daily_losing_trades": portfolio.daily_losing_trades,
            "max_losing_trades": self.config.max_losing_trades_per_day,
            "max_risk_per_trade_pct": self.config.max_risk_per_trade * 100,
            "max_daily_loss_pct": self.config.max_daily_loss * 100
        }
