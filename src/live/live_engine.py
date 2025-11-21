"""
Live trading engine for real-money trading.

Extends paper trading engine with real order execution via Kite API.
"""

from datetime import datetime
from typing import List, Dict, Optional
from threading import Lock

from kiteconnect import KiteConnect
from loguru import logger

from src.data.models import (
    OHLCVBar, Position, Trade, Portfolio, TradeInstruction,
    StrategySignal
)
from src.core.strategies.base import BaseStrategy
from src.core.risk import RiskManager
from src.paper.paper_engine import PaperTradingEngine
from src.live.order_manager import OrderManager, OrderStatus


class LiveTradingEngine(PaperTradingEngine):
    """
    Live trading engine with real order execution.
    
    Inherits from PaperTradingEngine but replaces simulated orders
    with real Kite API calls.
    """
    
    def __init__(
        self,
        kite: KiteConnect,
        strategies: List[BaseStrategy],
        risk_manager: RiskManager,
        initial_capital: float,
        interval_minutes: int = 5,
        require_confirmation: bool = True,
        max_orders_per_day: int = 10,
        emergency_stop_loss_pct: float = 0.05
    ):
        """
        Initialize live trading engine.
        
        Args:
            kite: KiteConnect instance
            strategies: List of strategy instances
            risk_manager: Risk manager instance
            initial_capital: Starting capital
            interval_minutes: Bar interval in minutes
            require_confirmation: Require manual confirmation for trades
            max_orders_per_day: Maximum orders per day
            emergency_stop_loss_pct: Emergency stop loss percentage
        """
        # Initialize parent (paper trading engine)
        super().__init__(
            strategies=strategies,
            risk_manager=risk_manager,
            initial_capital=initial_capital,
            interval_minutes=interval_minutes
        )
        
        # Live trading specific
        self.kite = kite
        self.order_manager = OrderManager(kite)
        self.require_confirmation = require_confirmation
        self.max_orders_per_day = max_orders_per_day
        self.emergency_stop_loss_pct = emergency_stop_loss_pct
        
        # Order tracking
        self.orders_today = 0
        self.emergency_stop_active = False
        
        # Stop loss orders (symbol -> order_id)
        self.stop_loss_orders: Dict[str, str] = {}
        
        logger.warning("=" * 80)
        logger.warning("LIVE TRADING MODE - REAL MONEY AT RISK")
        logger.warning("=" * 80)
        logger.info(f"Initial capital: ₹{initial_capital:,.2f}")
        logger.info(f"Confirmation required: {require_confirmation}")
        logger.info(f"Max orders per day: {max_orders_per_day}")
        logger.info(f"Emergency stop loss: {emergency_stop_loss_pct * 100:.1f}%")
    
    def _execute_entry(
        self,
        order: 'PaperOrder',
        fill_price: float,
        timestamp: datetime
    ) -> None:
        """
        Execute entry order via Kite API (overrides parent method).
        
        Args:
            order: Paper order (from parent class)
            fill_price: Expected fill price
            timestamp: Timestamp
        """
        symbol = order.symbol
        
        # Check emergency stop
        if self.emergency_stop_active:
            logger.warning(f"Emergency stop active - rejecting entry for {symbol}")
            return
        
        # Check max orders per day
        if self.orders_today >= self.max_orders_per_day:
            logger.warning(f"Max orders per day reached ({self.max_orders_per_day})")
            return
        
        # Confirmation prompt
        if self.require_confirmation:
            logger.warning("=" * 80)
            logger.warning(f"TRADE CONFIRMATION REQUIRED")
            logger.warning(f"Symbol: {symbol}")
            logger.warning(f"Quantity: {order.quantity}")
            logger.warning(f"Expected Price: ₹{fill_price:.2f}")
            logger.warning(f"Stop Loss: ₹{order.stop_loss:.2f}")
            logger.warning(f"Target: ₹{order.target:.2f}")
            logger.warning(f"Strategy: {order.strategy_name}")
            logger.warning(f"Reason: {order.reason}")
            logger.warning("=" * 80)
            
            # In production, this would wait for user input
            # For now, we'll just log and skip
            logger.warning("Manual confirmation required - skipping trade")
            logger.warning("Set require_confirmation=False to auto-execute")
            return
        
        # Place market order via Kite API
        try:
            live_order = self.order_manager.place_market_order(
                symbol=symbol,
                quantity=order.quantity,
                transaction_type="BUY",
                strategy_name=order.strategy_name,
                reason=order.reason
            )
            
            if not live_order or not live_order.order_id:
                logger.error(f"Failed to place order for {symbol}")
                return
            
            self.orders_today += 1
            
            # Wait briefly for order to fill
            import time
            time.sleep(1)
            
            # Update order status
            self.order_manager.update_order_status(live_order.order_id)
            
            if live_order.status != OrderStatus.COMPLETE:
                logger.warning(f"Order not filled yet: {live_order.status}")
                # In production, would monitor order status
                return
            
            # Get actual fill price
            actual_fill_price = live_order.average_price or fill_price
            
            # Create position
            position = Position(
                symbol=symbol,
                quantity=order.quantity,
                average_price=actual_fill_price,
                current_price=actual_fill_price,
                stop_loss=order.stop_loss,
                target=order.target,
                entry_time=timestamp,
                strategy_name=order.strategy_name,
                unrealized_pnl=0.0
            )
            
            # Update portfolio
            cost = actual_fill_price * order.quantity
            self.portfolio.cash -= cost
            self.portfolio.add_position(position)
            
            logger.info(
                f"ENTRY EXECUTED: {symbol} | Qty: {order.quantity} | "
                f"Price: ₹{actual_fill_price:.2f} | SL: ₹{order.stop_loss:.2f} | "
                f"Target: ₹{order.target:.2f} | Strategy: {order.strategy_name}"
            )
            logger.info(f"Order ID: {live_order.order_id}")
            
            # Place stop loss order
            self._place_stop_loss_order(symbol, order.quantity, order.stop_loss, order.strategy_name)
        
        except Exception as e:
            logger.error(f"Error executing entry for {symbol}: {e}")
    
    def _place_stop_loss_order(
        self,
        symbol: str,
        quantity: int,
        stop_loss_price: float,
        strategy_name: str
    ) -> None:
        """
        Place stop loss order for position.
        
        Args:
            symbol: Trading symbol
            quantity: Position quantity
            stop_loss_price: Stop loss trigger price
            strategy_name: Strategy name
        """
        try:
            sl_order = self.order_manager.place_stop_loss_order(
                symbol=symbol,
                quantity=quantity,
                transaction_type="SELL",
                trigger_price=stop_loss_price,
                strategy_name=strategy_name,
                reason="stop_loss"
            )
            
            if sl_order and sl_order.order_id:
                self.stop_loss_orders[symbol] = sl_order.order_id
                logger.info(f"Stop loss order placed for {symbol} at ₹{stop_loss_price:.2f}")
            else:
                logger.error(f"Failed to place stop loss order for {symbol}")
        
        except Exception as e:
            logger.error(f"Error placing stop loss order for {symbol}: {e}")
    
    def _execute_exit(
        self,
        symbol: str,
        exit_price: float,
        exit_reason: str,
        timestamp: datetime
    ) -> None:
        """
        Execute exit order via Kite API (overrides parent method).
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price
            exit_reason: Reason for exit
            timestamp: Exit timestamp
        """
        if symbol not in self.portfolio.positions:
            logger.warning(f"No position to exit for {symbol}")
            return
        
        position = self.portfolio.positions[symbol]
        
        try:
            # Cancel stop loss order if exists
            if symbol in self.stop_loss_orders:
                sl_order_id = self.stop_loss_orders[symbol]
                self.order_manager.cancel_order(sl_order_id)
                del self.stop_loss_orders[symbol]
            
            # Place market sell order
            exit_order = self.order_manager.place_market_order(
                symbol=symbol,
                quantity=position.quantity,
                transaction_type="SELL",
                strategy_name=position.strategy_name,
                reason=exit_reason
            )
            
            if not exit_order or not exit_order.order_id:
                logger.error(f"Failed to place exit order for {symbol}")
                return
            
            self.orders_today += 1
            
            # Wait briefly for order to fill
            import time
            time.sleep(1)
            
            # Update order status
            self.order_manager.update_order_status(exit_order.order_id)
            
            if exit_order.status != OrderStatus.COMPLETE:
                logger.warning(f"Exit order not filled yet: {exit_order.status}")
                return
            
            # Get actual exit price
            actual_exit_price = exit_order.average_price or exit_price
            
            # Close position
            trade = self.portfolio.close_position(symbol, actual_exit_price)
            
            if trade:
                trade.exit_reason = exit_reason
                trade.exit_time = timestamp
                trade.regime = self.current_regime
                trade.sentiment = self.current_sentiment.get(symbol)
                
                self.trades.append(trade)
                
                logger.info(
                    f"EXIT EXECUTED: {symbol} | Price: ₹{actual_exit_price:.2f} | "
                    f"P&L: ₹{trade.pnl:,.2f} ({trade.pnl_percent:.2f}%) | "
                    f"Reason: {exit_reason}"
                )
                logger.info(f"Order ID: {exit_order.order_id}")
                
                # Check emergency stop
                self._check_emergency_stop()
        
        except Exception as e:
            logger.error(f"Error executing exit for {symbol}: {e}")
    
    def _check_emergency_stop(self) -> None:
        """Check if emergency stop should be activated."""
        if self.emergency_stop_active:
            return
        
        # Check daily loss
        loss_pct = abs(self.portfolio.daily_pnl) / self.initial_capital
        
        if loss_pct >= self.emergency_stop_loss_pct:
            logger.error("=" * 80)
            logger.error("EMERGENCY STOP ACTIVATED")
            logger.error(f"Daily loss: ₹{self.portfolio.daily_pnl:,.2f} ({loss_pct * 100:.2f}%)")
            logger.error(f"Threshold: {self.emergency_stop_loss_pct * 100:.1f}%")
            logger.error("=" * 80)
            
            self.emergency_stop_active = True
            self.risk_manager.activate_kill_switch("Emergency stop - daily loss limit")
            
            # Cancel all pending orders
            self.order_manager.cancel_all_orders()
            
            # Close all positions
            self._close_all_positions()
    
    def _close_all_positions(self) -> None:
        """Close all open positions immediately."""
        logger.warning("Closing all positions...")
        
        for symbol in list(self.portfolio.positions.keys()):
            position = self.portfolio.positions[symbol]
            self._execute_exit(
                symbol=symbol,
                exit_price=position.current_price,
                exit_reason="emergency_stop",
                timestamp=datetime.now()
            )
        
        logger.warning("All positions closed")
    
    def sync_positions(self) -> None:
        """Sync positions with broker."""
        try:
            logger.info("Syncing positions with broker...")
            
            # Get positions from Kite
            positions = self.kite.positions()
            
            # Process net positions
            net_positions = positions.get("net", [])
            
            for pos in net_positions:
                symbol = pos["tradingsymbol"]
                quantity = pos["quantity"]
                
                if quantity == 0:
                    continue
                
                # Check if we have this position locally
                if symbol not in self.portfolio.positions:
                    logger.warning(f"Found position in broker not in local portfolio: {symbol}")
                    # Could add logic to sync here
                
            logger.info("Position sync complete")
        
        except Exception as e:
            logger.error(f"Error syncing positions: {e}")
    
    def get_status(self) -> Dict:
        """Get current engine status (overrides parent)."""
        status = super().get_status()
        
        # Add live trading specific info
        status.update({
            'orders_today': self.orders_today,
            'emergency_stop_active': self.emergency_stop_active,
            'pending_orders': len(self.order_manager.get_pending_orders()),
            'stop_loss_orders': len(self.stop_loss_orders)
        })
        
        return status
