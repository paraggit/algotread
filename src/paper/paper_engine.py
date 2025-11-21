"""
Paper trading engine for real-time trading simulation.

Processes live market data and simulates trade execution without real money.
"""

from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict
from queue import Queue
from threading import Lock

from loguru import logger

from src.data.models import (
    OHLCVBar, Position, Trade, Portfolio, TradeInstruction,
    StrategySignal
)
from src.core.strategies.base import BaseStrategy
from src.core.risk import RiskManager
from src.core.indicators import calculate_all_indicators
import pandas as pd


class PaperOrder:
    """Represents a simulated order."""
    
    def __init__(
        self,
        symbol: str,
        quantity: int,
        order_type: str,  # 'market', 'limit'
        side: str,  # 'buy', 'sell'
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        strategy_name: str = "",
        reason: str = ""
    ):
        self.symbol = symbol
        self.quantity = quantity
        self.order_type = order_type
        self.side = side
        self.price = price
        self.stop_loss = stop_loss
        self.target = target
        self.strategy_name = strategy_name
        self.reason = reason
        self.status = "pending"  # pending, filled, cancelled
        self.filled_price: Optional[float] = None
        self.filled_time: Optional[datetime] = None
        self.created_time = datetime.now()


class PaperTradingEngine:
    """
    Real-time paper trading engine.
    
    Processes live OHLCV bars, evaluates strategies, and simulates trades.
    """
    
    def __init__(
        self,
        strategies: List[BaseStrategy],
        risk_manager: RiskManager,
        initial_capital: float,
        interval_minutes: int = 5
    ):
        """
        Initialize paper trading engine.
        
        Args:
            strategies: List of strategy instances
            risk_manager: Risk manager instance
            initial_capital: Starting capital
            interval_minutes: Bar interval in minutes
        """
        self.strategies = strategies
        self.risk_manager = risk_manager
        self.initial_capital = initial_capital
        self.interval_minutes = interval_minutes
        
        # Portfolio state
        self.portfolio = Portfolio(cash=initial_capital)
        
        # Trade history
        self.trades: List[Trade] = []
        
        # Pending orders
        self.pending_orders: List[PaperOrder] = []
        
        # Historical bars for each symbol (for indicator calculation)
        self.symbol_data: Dict[str, List[OHLCVBar]] = defaultdict(list)
        self.max_bars_history = 200  # Keep last 200 bars
        
        # Thread safety
        self.lock = Lock()
        
        # Current regime and sentiment (placeholder for LLM)
        self.current_regime = None
        self.current_sentiment: Dict[str, Optional] = {}
        
        logger.info(f"PaperTradingEngine initialized with {len(strategies)} strategies")
        logger.info(f"Initial capital: ₹{initial_capital:,.2f}")
    
    def on_bar(self, bar: OHLCVBar) -> None:
        """
        Process new OHLCV bar.
        
        Args:
            bar: New completed bar
        """
        with self.lock:
            symbol = bar.symbol
            
            # Add to history
            self.symbol_data[symbol].append(bar)
            
            # Trim history if too long
            if len(self.symbol_data[symbol]) > self.max_bars_history:
                self.symbol_data[symbol] = self.symbol_data[symbol][-self.max_bars_history:]
            
            logger.debug(
                f"New bar: {symbol} | "
                f"O:{bar.open:.2f} H:{bar.high:.2f} L:{bar.low:.2f} C:{bar.close:.2f} V:{bar.volume}"
            )
            
            # Process pending orders (simulate fills)
            self._process_pending_orders(bar)
            
            # Update positions with current price
            if symbol in self.portfolio.positions:
                position = self.portfolio.positions[symbol]
                position.update_pnl(bar.close)
                
                # Check exit conditions
                self._check_exit_conditions(symbol, position, bar)
            
            # Update portfolio unrealized P&L
            self.portfolio.update_unrealized_pnl()
            
            # Check if we can take new positions
            if not self._can_trade():
                return
            
            # Skip if already in position or have pending order
            if symbol in self.portfolio.positions or self._has_pending_order(symbol):
                return
            
            # Need minimum bars for indicators
            if len(self.symbol_data[symbol]) < 50:
                return
            
            # Evaluate strategies
            self._evaluate_strategies(symbol)
    
    def _process_pending_orders(self, bar: OHLCVBar) -> None:
        """
        Process pending orders and simulate fills.
        
        Args:
            bar: Current bar
        """
        for order in list(self.pending_orders):
            if order.symbol != bar.symbol:
                continue
            
            # Simulate market order fill at bar open
            if order.status == "pending":
                fill_price = bar.open
                order.filled_price = fill_price
                order.filled_time = bar.timestamp
                order.status = "filled"
                
                # Create position
                if order.side == "buy":
                    self._execute_entry(order, fill_price, bar.timestamp)
                
                # Remove from pending
                self.pending_orders.remove(order)
    
    def _execute_entry(
        self,
        order: PaperOrder,
        fill_price: float,
        timestamp: datetime
    ) -> None:
        """
        Execute entry order.
        
        Args:
            order: Paper order
            fill_price: Fill price
            timestamp: Fill timestamp
        """
        symbol = order.symbol
        
        # Create position
        position = Position(
            symbol=symbol,
            quantity=order.quantity,
            average_price=fill_price,
            current_price=fill_price,
            stop_loss=order.stop_loss,
            target=order.target,
            entry_time=timestamp,
            strategy_name=order.strategy_name,
            unrealized_pnl=0.0
        )
        
        # Update portfolio
        cost = fill_price * order.quantity
        self.portfolio.cash -= cost
        self.portfolio.add_position(position)
        
        logger.info(
            f"ENTRY: {symbol} | Qty: {order.quantity} | "
            f"Price: ₹{fill_price:.2f} | SL: ₹{order.stop_loss:.2f} | "
            f"Target: ₹{order.target:.2f} | Strategy: {order.strategy_name}"
        )
        logger.info(f"Reason: {order.reason}")
    
    def _check_exit_conditions(
        self,
        symbol: str,
        position: Position,
        bar: OHLCVBar
    ) -> None:
        """
        Check if position should be exited.
        
        Args:
            symbol: Trading symbol
            position: Current position
            bar: Current bar
        """
        current_price = bar.close
        exit_reason = None
        
        # Check stop loss
        if position.stop_loss and current_price <= position.stop_loss:
            exit_reason = "stop_loss"
            logger.info(f"Stop loss hit for {symbol} at ₹{current_price:.2f}")
        
        # Check target
        elif position.target and current_price >= position.target:
            exit_reason = "target_hit"
            logger.info(f"Target hit for {symbol} at ₹{current_price:.2f}")
        
        # Check strategy exit signal
        else:
            df = self._get_dataframe(symbol)
            if df is not None and len(df) >= 50:
                df = calculate_all_indicators(df)
                
                # Find the strategy that opened this position
                for strategy in self.strategies:
                    if strategy.name == position.strategy_name:
                        instruction = strategy.evaluate(
                            df=df,
                            current_position="long" if position.quantity > 0 else "short",
                            regime=self.current_regime,
                            sentiment=self.current_sentiment.get(symbol)
                        )
                        
                        if instruction.signal == StrategySignal.EXIT_LONG:
                            exit_reason = "strategy_exit"
                            logger.info(f"Strategy exit signal for {symbol}")
                        break
        
        # Execute exit if needed
        if exit_reason:
            self._execute_exit(symbol, current_price, exit_reason, bar.timestamp)
    
    def _execute_exit(
        self,
        symbol: str,
        exit_price: float,
        exit_reason: str,
        timestamp: datetime
    ) -> None:
        """
        Execute exit order.
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price
            exit_reason: Reason for exit
            timestamp: Exit timestamp
        """
        trade = self.portfolio.close_position(symbol, exit_price)
        
        if trade:
            trade.exit_reason = exit_reason
            trade.exit_time = timestamp
            trade.regime = self.current_regime
            trade.sentiment = self.current_sentiment.get(symbol)
            
            self.trades.append(trade)
            
            logger.info(
                f"EXIT: {symbol} | Price: ₹{exit_price:.2f} | "
                f"P&L: ₹{trade.pnl:,.2f} ({trade.pnl_percent:.2f}%) | "
                f"Reason: {exit_reason}"
            )
    
    def _can_trade(self) -> bool:
        """
        Check if we can take new positions.
        
        Returns:
            True if trading is allowed
        """
        # Check kill switch
        if self.risk_manager.kill_switch_active:
            return False
        
        # Check daily loss limit
        daily_loss_limit = self.risk_manager.initial_capital * self.risk_manager.config.max_daily_loss
        if self.portfolio.daily_pnl < -daily_loss_limit:
            logger.warning(f"Daily loss limit reached: ₹{self.portfolio.daily_pnl:,.2f}")
            return False
        
        # Check max losing trades
        if self.portfolio.daily_losing_trades >= self.risk_manager.config.max_losing_trades_per_day:
            logger.warning(f"Max losing trades per day reached: {self.portfolio.daily_losing_trades}")
            return False
        
        return True
    
    def _has_pending_order(self, symbol: str) -> bool:
        """
        Check if there's a pending order for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if pending order exists
        """
        return any(order.symbol == symbol and order.status == "pending" for order in self.pending_orders)
    
    def _get_dataframe(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Convert bars to DataFrame for indicator calculation.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            DataFrame or None
        """
        bars = self.symbol_data.get(symbol, [])
        if not bars:
            return None
        
        data = []
        for bar in bars:
            data.append({
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('timestamp').reset_index(drop=True)
        # Set timestamp as index for VWAP calculation
        df = df.set_index('timestamp')
        df['timestamp'] = df.index
        return df
    
    def _evaluate_strategies(self, symbol: str) -> None:
        """
        Evaluate strategies for symbol.
        
        Args:
            symbol: Trading symbol
        """
        df = self._get_dataframe(symbol)
        if df is None or len(df) < 50:
            return
        
        # Calculate indicators
        df = calculate_all_indicators(df)
        
        # Evaluate each strategy
        for strategy in self.strategies:
            instruction = strategy.evaluate(
                df=df,
                current_position=None,
                regime=self.current_regime,
                sentiment=self.current_sentiment.get(symbol)
            )
            
            # Update instruction with correct symbol
            instruction.symbol = symbol
            
            # Process entry signals
            if instruction.signal == StrategySignal.ENTRY_LONG:
                self._create_entry_order(instruction, df.iloc[-1]['close'])
                break  # Only one strategy per symbol
    
    def _create_entry_order(
        self,
        instruction: TradeInstruction,
        current_price: float
    ) -> None:
        """
        Create entry order.
        
        Args:
            instruction: Trade instruction from strategy
            current_price: Current market price
        """
        symbol = instruction.symbol
        
        # Validate with risk manager
        is_allowed, reason = self.risk_manager.validate_trade(
            instruction,
            self.portfolio,
            datetime.now()
        )
        
        if not is_allowed:
            logger.debug(f"Trade rejected by risk manager for {symbol}: {reason}")
            return
        
        # Calculate position size
        quantity = self.risk_manager.calculate_position_size(instruction, self.portfolio)
        
        if quantity == 0:
            logger.debug(f"Position size calculated as 0 for {symbol}, skipping trade")
            return
        
        # Create paper order
        order = PaperOrder(
            symbol=symbol,
            quantity=quantity,
            order_type="market",
            side="buy",
            stop_loss=instruction.stop_loss,
            target=instruction.target,
            strategy_name=instruction.strategy_name,
            reason=instruction.reason
        )
        
        self.pending_orders.append(order)
        logger.info(f"Created BUY order for {symbol}: {quantity} shares")
    
    def get_status(self) -> Dict:
        """
        Get current engine status.
        
        Returns:
            Dictionary with status information
        """
        with self.lock:
            return {
                'portfolio_value': self.portfolio.get_total_value(),
                'cash': self.portfolio.cash,
                'realized_pnl': self.portfolio.realized_pnl,
                'unrealized_pnl': self.portfolio.unrealized_pnl,
                'daily_pnl': self.portfolio.daily_pnl,
                'total_trades': len(self.trades),
                'winning_trades': self.portfolio.winning_trades,
                'losing_trades': self.portfolio.losing_trades,
                'open_positions': len(self.portfolio.positions),
                'pending_orders': len(self.pending_orders),
                'symbols_tracked': len(self.symbol_data)
            }
    
    def get_trades(self) -> List[Trade]:
        """Get all executed trades."""
        with self.lock:
            return self.trades.copy()
    
    def get_portfolio(self) -> Portfolio:
        """Get current portfolio state."""
        with self.lock:
            return self.portfolio
