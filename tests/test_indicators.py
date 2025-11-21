"""Tests for indicator calculations."""

import pandas as pd
import numpy as np
import pytest

from src.core.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_atr,
    calculate_volume_ratio,
    is_ema_crossover_bullish,
    is_ema_crossover_bearish
)


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
    
    # Create synthetic price data with trend
    np.random.seed(42)
    close_prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices + np.random.randn(100) * 0.2,
        'high': close_prices + np.abs(np.random.randn(100) * 0.5),
        'low': close_prices - np.abs(np.random.randn(100) * 0.5),
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, 100),
        'symbol': 'TEST'
    })
    
    return df


def test_calculate_ema(sample_ohlcv_data):
    """Test EMA calculation."""
    ema = calculate_ema(sample_ohlcv_data, period=9)
    
    assert len(ema) == len(sample_ohlcv_data)
    assert not ema.isna().all()  # Should have some non-NaN values
    assert ema.iloc[-1] > 0  # Last value should be positive


def test_calculate_rsi(sample_ohlcv_data):
    """Test RSI calculation."""
    rsi = calculate_rsi(sample_ohlcv_data, period=14)
    
    assert len(rsi) == len(sample_ohlcv_data)
    
    # RSI should be between 0 and 100
    valid_rsi = rsi.dropna()
    assert (valid_rsi >= 0).all()
    assert (valid_rsi <= 100).all()


def test_calculate_atr(sample_ohlcv_data):
    """Test ATR calculation."""
    atr = calculate_atr(sample_ohlcv_data, period=14)
    
    assert len(atr) == len(sample_ohlcv_data)
    
    # ATR should be positive
    valid_atr = atr.dropna()
    assert (valid_atr > 0).all()


def test_calculate_volume_ratio(sample_ohlcv_data):
    """Test volume ratio calculation."""
    volume_ratio = calculate_volume_ratio(sample_ohlcv_data, lookback=20)
    
    assert len(volume_ratio) == len(sample_ohlcv_data)
    
    # Volume ratio should be positive
    valid_ratio = volume_ratio.dropna()
    assert (valid_ratio > 0).all()


def test_ema_crossover_bullish():
    """Test bullish EMA crossover detection."""
    # Create data with known crossover - fast crosses above slow
    df = pd.DataFrame({
        'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        'ema_fast': [98, 99, 100, 101, 102, 103, 104, 105, 106, 107],  # Below then above
        'ema_slow': [100, 100.5, 101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5]  # Slower rise
    })
    
    # Should detect crossover (fast crosses above slow around index 2-3)
    assert is_ema_crossover_bullish(df, lookback=5)


def test_ema_crossover_bearish():
    """Test bearish EMA crossover detection."""
    # Create data with known crossover - fast crosses below slow
    df = pd.DataFrame({
        'close': [109, 108, 107, 106, 105, 104, 103, 102, 101, 100],
        'ema_fast': [107, 106, 105, 104, 103, 102, 101, 100, 99, 98],  # Above then below
        'ema_slow': [104.5, 104, 103.5, 103, 102.5, 102, 101.5, 101, 100.5, 100]  # Slower decline
    })
    
    # Should detect crossover (fast crosses below slow around index 2-3)
    assert is_ema_crossover_bearish(df, lookback=5)


def test_no_crossover():
    """Test no crossover detection."""
    # Create data with no crossover
    df = pd.DataFrame({
        'close': [100, 101, 102, 103, 104],
        'ema_fast': [100, 101, 102, 103, 104],
        'ema_slow': [95, 96, 97, 98, 99]
    })
    
    # Should not detect crossover
    assert not is_ema_crossover_bullish(df, lookback=2)
    assert not is_ema_crossover_bearish(df, lookback=2)
