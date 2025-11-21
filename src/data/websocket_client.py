"""
WebSocket client for live market data streaming from Zerodha Kite.

Handles:
- WebSocket connection and authentication
- Tick data subscription
- OHLCV bar aggregation from ticks
- Automatic reconnection
- Event callbacks for new bars
"""

from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional
from collections import defaultdict
from threading import Thread, Lock
import time

from kiteconnect import KiteTicker
from loguru import logger

from src.data.models import OHLCVBar
from src.config import KiteConfig


class BarAggregator:
    """
    Aggregates tick data into OHLCV bars.
    """
    
    def __init__(self, interval_minutes: int = 5):
        """
        Initialize bar aggregator.
        
        Args:
            interval_minutes: Bar interval in minutes
        """
        self.interval_minutes = interval_minutes
        self.current_bars: Dict[str, Dict] = {}  # symbol -> partial bar data
        self.lock = Lock()
    
    def add_tick(self, symbol: str, tick: Dict) -> Optional[OHLCVBar]:
        """
        Add tick and return completed bar if interval elapsed.
        
        Args:
            symbol: Trading symbol
            tick: Tick data from WebSocket
            
        Returns:
            OHLCVBar if bar is complete, None otherwise
        """
        with self.lock:
            timestamp = tick.get('exchange_timestamp') or datetime.now()
            price = tick.get('last_price', 0)
            volume = tick.get('volume_traded', 0)
            
            if not price:
                return None
            
            # Calculate bar start time (round down to interval)
            bar_start = self._get_bar_start(timestamp)
            
            # Initialize or update current bar
            if symbol not in self.current_bars:
                self.current_bars[symbol] = {
                    'start_time': bar_start,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume,
                    'tick_count': 1
                }
                return None
            
            bar = self.current_bars[symbol]
            
            # Check if we need to close current bar and start new one
            if timestamp >= bar['start_time'] + timedelta(minutes=self.interval_minutes):
                # Complete the current bar
                completed_bar = OHLCVBar(
                    timestamp=bar['start_time'],
                    open=bar['open'],
                    high=bar['high'],
                    low=bar['low'],
                    close=bar['close'],
                    volume=bar['volume'],
                    symbol=symbol
                )
                
                # Start new bar
                self.current_bars[symbol] = {
                    'start_time': bar_start,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume,
                    'tick_count': 1
                }
                
                return completed_bar
            
            # Update current bar
            bar['high'] = max(bar['high'], price)
            bar['low'] = min(bar['low'], price)
            bar['close'] = price
            bar['volume'] = volume  # Kite sends cumulative volume
            bar['tick_count'] += 1
            
            return None
    
    def _get_bar_start(self, timestamp: datetime) -> datetime:
        """
        Get bar start time by rounding down to interval.
        
        Args:
            timestamp: Current timestamp
            
        Returns:
            Bar start timestamp
        """
        # Round down to nearest interval
        minutes = (timestamp.minute // self.interval_minutes) * self.interval_minutes
        return timestamp.replace(minute=minutes, second=0, microsecond=0)
    
    def get_current_bar(self, symbol: str) -> Optional[Dict]:
        """
        Get current incomplete bar for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Current bar data or None
        """
        with self.lock:
            return self.current_bars.get(symbol)


class KiteWebSocketClient:
    """
    WebSocket client for live market data from Zerodha Kite.
    """
    
    def __init__(
        self,
        config: KiteConfig,
        symbols: List[str],
        interval_minutes: int = 5,
        on_bar: Optional[Callable[[OHLCVBar], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ):
        """
        Initialize WebSocket client.
        
        Args:
            config: Kite API configuration
            symbols: List of symbols to subscribe
            interval_minutes: Bar interval in minutes
            on_bar: Callback for new completed bars
            on_error: Callback for errors
        """
        self.config = config
        self.symbols = symbols
        self.interval_minutes = interval_minutes
        self.on_bar_callback = on_bar
        self.on_error_callback = on_error
        
        # Initialize components
        self.ticker = KiteTicker(config.api_key, config.access_token)
        self.aggregator = BarAggregator(interval_minutes)
        self.instrument_tokens: Dict[str, int] = {}
        
        # Connection state
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Setup callbacks
        self.ticker.on_connect = self._on_connect
        self.ticker.on_close = self._on_close
        self.ticker.on_error = self._on_error
        self.ticker.on_reconnect = self._on_reconnect
        self.ticker.on_noreconnect = self._on_noreconnect
        self.ticker.on_ticks = self._on_ticks
        
        logger.info(f"KiteWebSocketClient initialized for {len(symbols)} symbols")
    
    def set_instrument_tokens(self, tokens: Dict[str, int]) -> None:
        """
        Set instrument tokens for symbols.
        
        Args:
            tokens: Dictionary mapping symbol to instrument token
        """
        self.instrument_tokens = tokens
        logger.info(f"Set instrument tokens for {len(tokens)} symbols")
    
    def start(self) -> None:
        """Start WebSocket connection in background thread."""
        logger.info("Starting WebSocket connection...")
        thread = Thread(target=self.ticker.connect, daemon=True)
        thread.start()
    
    def stop(self) -> None:
        """Stop WebSocket connection."""
        logger.info("Stopping WebSocket connection...")
        self.ticker.close()
        self.is_connected = False
    
    def _on_connect(self, ws, response) -> None:
        """Handle WebSocket connection."""
        self.is_connected = True
        self.reconnect_attempts = 0
        logger.info("WebSocket connected successfully")
        
        # Subscribe to instruments
        if self.instrument_tokens:
            tokens = list(self.instrument_tokens.values())
            ws.subscribe(tokens)
            ws.set_mode(ws.MODE_FULL, tokens)  # Get full tick data
            logger.info(f"Subscribed to {len(tokens)} instruments")
        else:
            logger.warning("No instrument tokens set, cannot subscribe")
    
    def _on_close(self, ws, code, reason) -> None:
        """Handle WebSocket close."""
        self.is_connected = False
        logger.warning(f"WebSocket closed: {code} - {reason}")
    
    def _on_error(self, ws, code, reason) -> None:
        """Handle WebSocket error."""
        logger.error(f"WebSocket error: {code} - {reason}")
        if self.on_error_callback:
            try:
                self.on_error_callback(Exception(f"{code}: {reason}"))
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    def _on_reconnect(self, ws, attempts_count) -> None:
        """Handle WebSocket reconnection attempt."""
        self.reconnect_attempts = attempts_count
        logger.info(f"WebSocket reconnecting... (attempt {attempts_count})")
    
    def _on_noreconnect(self, ws) -> None:
        """Handle WebSocket reconnection failure."""
        logger.error("WebSocket reconnection failed after max attempts")
        if self.on_error_callback:
            try:
                self.on_error_callback(Exception("WebSocket reconnection failed"))
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    def _on_ticks(self, ws, ticks: List[Dict]) -> None:
        """
        Handle incoming ticks.
        
        Args:
            ws: WebSocket instance
            ticks: List of tick data
        """
        # Reverse lookup: token -> symbol
        token_to_symbol = {v: k for k, v in self.instrument_tokens.items()}
        
        for tick in ticks:
            instrument_token = tick.get('instrument_token')
            symbol = token_to_symbol.get(instrument_token)
            
            if not symbol:
                continue
            
            # Add tick to aggregator
            completed_bar = self.aggregator.add_tick(symbol, tick)
            
            # If bar is complete, call callback
            if completed_bar and self.on_bar_callback:
                try:
                    self.on_bar_callback(completed_bar)
                except Exception as e:
                    logger.error(f"Error in bar callback: {e}")
    
    def get_connection_status(self) -> Dict:
        """
        Get current connection status.
        
        Returns:
            Dictionary with connection info
        """
        return {
            'connected': self.is_connected,
            'reconnect_attempts': self.reconnect_attempts,
            'subscribed_symbols': len(self.instrument_tokens),
            'current_bars': {
                symbol: self.aggregator.get_current_bar(symbol)
                for symbol in self.symbols
            }
        }
