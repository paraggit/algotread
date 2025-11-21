"""
Data fetcher for historical OHLCV data from Zerodha Kite API.
Includes caching mechanism to avoid redundant API calls.
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd
from kiteconnect import KiteConnect
from loguru import logger

from src.data.models import OHLCVBar
from src.config import KiteConfig


class KiteDataFetcher:
    """Fetches historical OHLCV data from Zerodha Kite API with caching."""
    
    def __init__(self, kite_config: KiteConfig, cache_dir: str = "data/cache"):
        """
        Initialize the data fetcher.
        
        Args:
            kite_config: Kite API configuration
            cache_dir: Directory for caching historical data
        """
        self.kite = KiteConnect(api_key=kite_config.api_key)
        self.kite.set_access_token(kite_config.access_token)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"KiteDataFetcher initialized with cache dir: {self.cache_dir}")
    
    def fetch_historical_data(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str = "5minute",
        exchange: str = "NSE"
    ) -> List[OHLCVBar]:
        """
        Fetch historical OHLCV data for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE", "TCS")
            from_date: Start date
            to_date: End date
            interval: Data interval (minute, 5minute, 15minute, day, etc.)
            exchange: Exchange (NSE, BSE, etc.)
            
        Returns:
            List of OHLCVBar objects
        """
        # Check cache first
        cached_data = self._load_from_cache(symbol, from_date, to_date, interval, exchange)
        if cached_data is not None:
            logger.info(f"Loaded {len(cached_data)} bars from cache for {symbol}")
            return cached_data
        
        # Fetch from API
        logger.info(f"Fetching data from Kite API for {symbol} ({from_date} to {to_date})")
        
        try:
            # Get instrument token
            instrument_token = self._get_instrument_token(symbol, exchange)
            
            # Fetch historical data
            # Note: Kite API returns data in IST timezone
            records = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )
            
            if not records:
                logger.warning(f"No data returned for {symbol}")
                return []
            
            # Convert to OHLCVBar objects
            bars = []
            for record in records:
                bar = OHLCVBar(
                    timestamp=record['date'],
                    open=float(record['open']),
                    high=float(record['high']),
                    low=float(record['low']),
                    close=float(record['close']),
                    volume=int(record['volume']),
                    symbol=symbol
                )
                bars.append(bar)
            
            logger.info(f"Fetched {len(bars)} bars for {symbol}")
            
            # Cache the data
            self._save_to_cache(symbol, from_date, to_date, interval, exchange, bars)
            
            return bars
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            raise
    
    def _get_instrument_token(self, symbol: str, exchange: str) -> int:
        """
        Get instrument token for a symbol.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange
            
        Returns:
            Instrument token
        """
        # Cache instruments list
        instruments_cache = self.cache_dir / "instruments.json"
        
        # Load from cache if available and fresh (< 1 day old)
        if instruments_cache.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(instruments_cache.stat().st_mtime)
            if cache_age < timedelta(days=1):
                with open(instruments_cache, 'r') as f:
                    instruments = json.load(f)
                    for inst in instruments:
                        if inst['tradingsymbol'] == symbol and inst['exchange'] == exchange:
                            return inst['instrument_token']
        
        # Fetch fresh instruments list
        logger.info("Fetching instruments list from Kite API")
        instruments = self.kite.instruments(exchange)
        
        # Save to cache
        with open(instruments_cache, 'w') as f:
            json.dump(instruments, f)
        
        # Find the instrument token
        for inst in instruments:
            if inst['tradingsymbol'] == symbol and inst['exchange'] == exchange:
                return inst['instrument_token']
        
        raise ValueError(f"Instrument not found: {symbol} on {exchange}")
    
    def _get_cache_key(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str,
        exchange: str
    ) -> str:
        """
        Generate cache key for the data request.
        
        Args:
            symbol: Trading symbol
            from_date: Start date
            to_date: End date
            interval: Data interval
            exchange: Exchange
            
        Returns:
            Cache key (filename)
        """
        # Create a unique key based on parameters
        key_str = f"{symbol}_{exchange}_{from_date.date()}_{to_date.date()}_{interval}"
        # Use hash to keep filename reasonable length
        key_hash = hashlib.md5(key_str.encode()).hexdigest()[:8]
        return f"{symbol}_{from_date.date()}_{to_date.date()}_{interval}_{key_hash}.json"
    
    def _load_from_cache(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str,
        exchange: str
    ) -> Optional[List[OHLCVBar]]:
        """
        Load data from cache if available.
        
        Args:
            symbol: Trading symbol
            from_date: Start date
            to_date: End date
            interval: Data interval
            exchange: Exchange
            
        Returns:
            List of OHLCVBar objects or None if not cached
        """
        cache_file = self.cache_dir / self._get_cache_key(symbol, from_date, to_date, interval, exchange)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            bars = []
            for item in data:
                bar = OHLCVBar(
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    open=item['open'],
                    high=item['high'],
                    low=item['low'],
                    close=item['close'],
                    volume=item['volume'],
                    symbol=item['symbol']
                )
                bars.append(bar)
            
            return bars
            
        except Exception as e:
            logger.warning(f"Error loading cache for {symbol}: {e}")
            return None
    
    def _save_to_cache(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str,
        exchange: str,
        bars: List[OHLCVBar]
    ) -> None:
        """
        Save data to cache.
        
        Args:
            symbol: Trading symbol
            from_date: Start date
            to_date: End date
            interval: Data interval
            exchange: Exchange
            bars: List of OHLCVBar objects to cache
        """
        cache_file = self.cache_dir / self._get_cache_key(symbol, from_date, to_date, interval, exchange)
        
        try:
            data = []
            for bar in bars:
                data.append({
                    'timestamp': bar.timestamp.isoformat(),
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume,
                    'symbol': bar.symbol
                })
            
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Cached {len(bars)} bars to {cache_file}")
            
        except Exception as e:
            logger.warning(f"Error saving cache for {symbol}: {e}")
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """
        Clear cached data.
        
        Args:
            symbol: If provided, clear only cache for this symbol. Otherwise clear all.
        """
        if symbol:
            pattern = f"{symbol}_*.json"
            for cache_file in self.cache_dir.glob(pattern):
                cache_file.unlink()
                logger.info(f"Deleted cache file: {cache_file}")
        else:
            for cache_file in self.cache_dir.glob("*.json"):
                if cache_file.name != "instruments.json":
                    cache_file.unlink()
            logger.info("Cleared all cached data")
