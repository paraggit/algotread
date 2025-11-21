"""
Order manager for live trading.

Handles order placement, tracking, and lifecycle management via Kite API.
"""

from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum

from kiteconnect import KiteConnect
from loguru import logger

from src.data.models import TradeInstruction


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    OPEN = "open"
    COMPLETE = "complete"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class Order:
    """Represents a live order."""
    
    def __init__(
        self,
        symbol: str,
        quantity: int,
        order_type: str,
        transaction_type: str,  # BUY or SELL
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        product: str = "MIS",  # MIS for intraday
        variety: str = "regular",
        strategy_name: str = "",
        reason: str = ""
    ):
        self.symbol = symbol
        self.quantity = quantity
        self.order_type = order_type
        self.transaction_type = transaction_type
        self.price = price
        self.trigger_price = trigger_price
        self.product = product
        self.variety = variety
        self.strategy_name = strategy_name
        self.reason = reason
        
        # Order tracking
        self.order_id: Optional[str] = None
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0
        self.average_price: Optional[float] = None
        self.created_time = datetime.now()
        self.updated_time = datetime.now()
        self.exchange_timestamp: Optional[datetime] = None
        self.rejection_reason: Optional[str] = None


class OrderManager:
    """
    Manages order lifecycle for live trading.
    
    Handles order placement, tracking, and status updates via Kite API.
    """
    
    def __init__(self, kite: KiteConnect, exchange: str = "NSE"):
        """
        Initialize order manager.
        
        Args:
            kite: KiteConnect instance
            exchange: Exchange (NSE, BSE, etc.)
        """
        self.kite = kite
        self.exchange = exchange
        self.orders: Dict[str, Order] = {}  # order_id -> Order
        
        logger.info("OrderManager initialized")
    
    def place_order(
        self,
        symbol: str,
        quantity: int,
        transaction_type: str,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        product: str = "MIS",
        strategy_name: str = "",
        reason: str = ""
    ) -> Optional[Order]:
        """
        Place order via Kite API.
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            transaction_type: BUY or SELL
            order_type: MARKET, LIMIT, SL, SL-M
            price: Limit price (for LIMIT orders)
            trigger_price: Trigger price (for SL orders)
            product: MIS (intraday) or CNC (delivery)
            strategy_name: Strategy that generated the signal
            reason: Reason for the trade
            
        Returns:
            Order object if successful, None otherwise
        """
        try:
            # Create order object
            order = Order(
                symbol=symbol,
                quantity=quantity,
                order_type=order_type,
                transaction_type=transaction_type,
                price=price,
                trigger_price=trigger_price,
                product=product,
                strategy_name=strategy_name,
                reason=reason
            )
            
            # Prepare order parameters
            order_params = {
                "tradingsymbol": symbol,
                "exchange": self.exchange,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "order_type": order_type,
                "product": product,
                "variety": order.variety
            }
            
            # Add price for limit orders
            if order_type == "LIMIT" and price:
                order_params["price"] = price
            
            # Add trigger price for SL orders
            if order_type in ["SL", "SL-M"] and trigger_price:
                order_params["trigger_price"] = trigger_price
            
            # Place order via Kite API
            logger.info(f"Placing {transaction_type} order: {symbol} x {quantity} @ {order_type}")
            response = self.kite.place_order(**order_params)
            
            # Extract order ID
            order_id = response.get("order_id")
            if not order_id:
                logger.error(f"No order ID in response: {response}")
                return None
            
            # Update order
            order.order_id = order_id
            order.status = OrderStatus.OPEN
            order.updated_time = datetime.now()
            
            # Store order
            self.orders[order_id] = order
            
            logger.info(f"Order placed successfully: ID={order_id}")
            logger.info(f"Strategy: {strategy_name} | Reason: {reason}")
            
            return order
        
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            if order:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = str(e)
            return None
    
    def place_market_order(
        self,
        symbol: str,
        quantity: int,
        transaction_type: str,
        strategy_name: str = "",
        reason: str = ""
    ) -> Optional[Order]:
        """
        Place market order (convenience method).
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            transaction_type: BUY or SELL
            strategy_name: Strategy name
            reason: Trade reason
            
        Returns:
            Order object if successful
        """
        return self.place_order(
            symbol=symbol,
            quantity=quantity,
            transaction_type=transaction_type,
            order_type="MARKET",
            strategy_name=strategy_name,
            reason=reason
        )
    
    def place_stop_loss_order(
        self,
        symbol: str,
        quantity: int,
        transaction_type: str,
        trigger_price: float,
        strategy_name: str = "",
        reason: str = "stop_loss"
    ) -> Optional[Order]:
        """
        Place stop-loss market order.
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            transaction_type: BUY or SELL
            trigger_price: Stop loss trigger price
            strategy_name: Strategy name
            reason: Trade reason
            
        Returns:
            Order object if successful
        """
        return self.place_order(
            symbol=symbol,
            quantity=quantity,
            transaction_type=transaction_type,
            order_type="SL-M",
            trigger_price=trigger_price,
            strategy_name=strategy_name,
            reason=reason
        )
    
    def update_order_status(self, order_id: str) -> Optional[Order]:
        """
        Update order status from Kite API.
        
        Args:
            order_id: Order ID
            
        Returns:
            Updated order object
        """
        if order_id not in self.orders:
            logger.warning(f"Order {order_id} not found in local cache")
            return None
        
        try:
            # Get order history from Kite
            order_history = self.kite.order_history(order_id)
            
            if not order_history:
                logger.warning(f"No history for order {order_id}")
                return None
            
            # Get latest status (last item in history)
            latest = order_history[-1]
            
            # Update local order
            order = self.orders[order_id]
            order.status = OrderStatus(latest["status"].lower())
            order.filled_quantity = latest.get("filled_quantity", 0)
            order.average_price = latest.get("average_price")
            order.updated_time = datetime.now()
            
            if latest.get("exchange_timestamp"):
                order.exchange_timestamp = latest["exchange_timestamp"]
            
            if latest.get("status_message"):
                order.rejection_reason = latest["status_message"]
            
            logger.debug(f"Order {order_id} status: {order.status}")
            
            return order
        
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return None
    
    def cancel_order(self, order_id: str, variety: str = "regular") -> bool:
        """
        Cancel pending order.
        
        Args:
            order_id: Order ID
            variety: Order variety
            
        Returns:
            True if cancelled successfully
        """
        try:
            logger.info(f"Cancelling order {order_id}")
            self.kite.cancel_order(variety=variety, order_id=order_id)
            
            # Update local order
            if order_id in self.orders:
                self.orders[order_id].status = OrderStatus.CANCELLED
                self.orders[order_id].updated_time = datetime.now()
            
            logger.info(f"Order {order_id} cancelled successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def cancel_all_orders(self) -> int:
        """
        Cancel all pending orders.
        
        Returns:
            Number of orders cancelled
        """
        cancelled_count = 0
        
        for order_id, order in list(self.orders.items()):
            if order.status in [OrderStatus.PENDING, OrderStatus.OPEN]:
                if self.cancel_order(order_id, order.variety):
                    cancelled_count += 1
        
        logger.info(f"Cancelled {cancelled_count} orders")
        return cancelled_count
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders.get(order_id)
    
    def get_pending_orders(self) -> List[Order]:
        """Get all pending/open orders."""
        return [
            order for order in self.orders.values()
            if order.status in [OrderStatus.PENDING, OrderStatus.OPEN]
        ]
    
    def get_completed_orders(self) -> List[Order]:
        """Get all completed orders."""
        return [
            order for order in self.orders.values()
            if order.status == OrderStatus.COMPLETE
        ]
    
    def sync_orders(self) -> None:
        """Sync all order statuses with Kite API."""
        logger.info("Syncing order statuses...")
        
        for order_id in list(self.orders.keys()):
            self.update_order_status(order_id)
        
        logger.info("Order sync complete")
