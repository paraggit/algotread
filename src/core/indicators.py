"""
Technical indicator calculations.
Pure functions operating on pandas DataFrames.
"""

import numpy as np
import pandas as pd
import pandas_ta as ta


def calculate_ema(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
    """
    Calculate Exponential Moving Average.
    
    Args:
        df: DataFrame with OHLCV data
        period: EMA period
        column: Column to calculate EMA on (default: close)
        
    Returns:
        Series with EMA values
    """
    return ta.ema(df[column], length=period)


def calculate_supertrend(
    df: pd.DataFrame,
    period: int = 7,
    multiplier: float = 3.0
) -> pd.DataFrame:
    """
    Calculate Supertrend indicator.
    
    Args:
        df: DataFrame with OHLCV data (must have high, low, close columns)
        period: ATR period
        multiplier: ATR multiplier
        
    Returns:
        DataFrame with columns: SUPERT_<period>_<multiplier>, SUPERTd_<period>_<multiplier>, SUPERTl_<period>_<multiplier>, SUPERTs_<period>_<multiplier>
        - SUPERT: Supertrend line
        - SUPERTd: Direction (1 for bullish, -1 for bearish)
        - SUPERTl: Long stop
        - SUPERTs: Short stop
    """
    result = ta.supertrend(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        length=period,
        multiplier=multiplier
    )
    return result


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume Weighted Average Price.
    
    Args:
        df: DataFrame with OHLCV data (must have high, low, close, volume columns)
        
    Returns:
        Series with VWAP values
    """
    return ta.vwap(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        volume=df["volume"]
    )


def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = "close") -> pd.Series:
    """
    Calculate Relative Strength Index.
    
    Args:
        df: DataFrame with OHLCV data
        period: RSI period
        column: Column to calculate RSI on (default: close)
        
    Returns:
        Series with RSI values (0-100)
    """
    return ta.rsi(df[column], length=period)


def calculate_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = "close"
) -> pd.DataFrame:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        df: DataFrame with OHLCV data
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period
        column: Column to calculate MACD on (default: close)
        
    Returns:
        DataFrame with columns: MACD_<fast>_<slow>_<signal>, MACDh_<fast>_<slow>_<signal>, MACDs_<fast>_<slow>_<signal>
        - MACD: MACD line
        - MACDh: MACD histogram
        - MACDs: Signal line
    """
    result = ta.macd(df[column], fast=fast, slow=slow, signal=signal)
    return result


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range.
    
    Args:
        df: DataFrame with OHLCV data (must have high, low, close columns)
        period: ATR period
        
    Returns:
        Series with ATR values
    """
    return ta.atr(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        length=period
    )


def calculate_volume_ratio(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """
    Calculate volume ratio (current volume / average volume).
    
    Args:
        df: DataFrame with OHLCV data (must have volume column)
        lookback: Number of periods to calculate average volume
        
    Returns:
        Series with volume ratio values
    """
    avg_volume = df["volume"].rolling(window=lookback).mean()
    return df["volume"] / avg_volume


def calculate_orb_levels(
    df: pd.DataFrame,
    period_minutes: int = 15,
    interval_minutes: int = 5
) -> tuple[float, float]:
    """
    Calculate Opening Range Breakout levels.
    
    Args:
        df: DataFrame with OHLCV data indexed by timestamp
        period_minutes: ORB period in minutes (e.g., 15 for first 15 minutes)
        interval_minutes: Candle interval in minutes (e.g., 5 for 5-minute candles)
        
    Returns:
        Tuple of (orb_high, orb_low)
    """
    # Calculate number of candles in ORB period
    num_candles = period_minutes // interval_minutes
    
    # Get first N candles of the day
    orb_candles = df.head(num_candles)
    
    if len(orb_candles) < num_candles:
        # Not enough data yet
        return (0.0, 0.0)
    
    orb_high = orb_candles["high"].max()
    orb_low = orb_candles["low"].min()
    
    return (orb_high, orb_low)


def calculate_swing_levels(
    df: pd.DataFrame,
    lookback: int = 5
) -> tuple[float, float]:
    """
    Calculate recent swing high and swing low.
    
    Args:
        df: DataFrame with OHLCV data
        lookback: Number of periods to look back
        
    Returns:
        Tuple of (swing_high, swing_low)
    """
    recent_data = df.tail(lookback)
    
    if len(recent_data) == 0:
        return (0.0, 0.0)
    
    swing_high = recent_data["high"].max()
    swing_low = recent_data["low"].min()
    
    return (swing_high, swing_low)


def calculate_all_indicators(
    df: pd.DataFrame,
    ema_fast: int = 9,
    ema_slow: int = 21,
    supertrend_period: int = 7,
    supertrend_multiplier: float = 3.0,
    rsi_period: int = 14,
    atr_period: int = 14,
    volume_lookback: int = 20
) -> pd.DataFrame:
    """
    Calculate all indicators and add them to the DataFrame.
    
    Args:
        df: DataFrame with OHLCV data
        ema_fast: Fast EMA period
        ema_slow: Slow EMA period
        supertrend_period: Supertrend ATR period
        supertrend_multiplier: Supertrend multiplier
        rsi_period: RSI period
        atr_period: ATR period
        volume_lookback: Volume ratio lookback period
        
    Returns:
        DataFrame with all indicators added as columns
    """
    df = df.copy()
    
    # EMAs
    df["ema_fast"] = calculate_ema(df, ema_fast)
    df["ema_slow"] = calculate_ema(df, ema_slow)
    
    # Supertrend
    supertrend = calculate_supertrend(df, supertrend_period, supertrend_multiplier)
    df = pd.concat([df, supertrend], axis=1)
    
    # VWAP
    df["vwap"] = calculate_vwap(df)
    
    # RSI
    df["rsi"] = calculate_rsi(df, rsi_period)
    
    # MACD
    macd = calculate_macd(df)
    df = pd.concat([df, macd], axis=1)
    
    # ATR
    df["atr"] = calculate_atr(df, atr_period)
    
    # Volume ratio
    df["volume_ratio"] = calculate_volume_ratio(df, volume_lookback)
    
    return df


def is_bullish_supertrend(df: pd.DataFrame, period: int = 7, multiplier: float = 3.0) -> bool:
    """
    Check if Supertrend is currently bullish.
    
    Args:
        df: DataFrame with Supertrend indicator
        period: Supertrend period (must match calculated indicator)
        multiplier: Supertrend multiplier (must match calculated indicator)
        
    Returns:
        True if bullish, False otherwise
    """
    direction_col = f"SUPERTd_{period}_{multiplier}"
    
    if direction_col not in df.columns or len(df) == 0:
        return False
    
    # Direction: 1 for bullish, -1 for bearish
    return df[direction_col].iloc[-1] == 1


def is_bearish_supertrend(df: pd.DataFrame, period: int = 7, multiplier: float = 3.0) -> bool:
    """
    Check if Supertrend is currently bearish.
    
    Args:
        df: DataFrame with Supertrend indicator
        period: Supertrend period (must match calculated indicator)
        multiplier: Supertrend multiplier (must match calculated indicator)
        
    Returns:
        True if bearish, False otherwise
    """
    direction_col = f"SUPERTd_{period}_{multiplier}"
    
    if direction_col not in df.columns or len(df) == 0:
        return False
    
    # Direction: 1 for bullish, -1 for bearish
    return df[direction_col].iloc[-1] == -1


def is_ema_crossover_bullish(df: pd.DataFrame, lookback: int = 2) -> bool:
    """
    Check if fast EMA recently crossed above slow EMA.
    
    Args:
        df: DataFrame with ema_fast and ema_slow columns
        lookback: Number of candles to look back for crossover
        
    Returns:
        True if bullish crossover detected, False otherwise
    """
    if "ema_fast" not in df.columns or "ema_slow" not in df.columns:
        return False
    
    if len(df) < lookback + 1:
        return False
    
    recent = df.tail(lookback + 1)
    
    # Check if fast was below slow and is now above
    for i in range(len(recent) - 1):
        if (recent["ema_fast"].iloc[i] <= recent["ema_slow"].iloc[i] and
            recent["ema_fast"].iloc[i + 1] > recent["ema_slow"].iloc[i + 1]):
            return True
    
    return False


def is_ema_crossover_bearish(df: pd.DataFrame, lookback: int = 2) -> bool:
    """
    Check if fast EMA recently crossed below slow EMA.
    
    Args:
        df: DataFrame with ema_fast and ema_slow columns
        lookback: Number of candles to look back for crossover
        
    Returns:
        True if bearish crossover detected, False otherwise
    """
    if "ema_fast" not in df.columns or "ema_slow" not in df.columns:
        return False
    
    if len(df) < lookback + 1:
        return False
    
    recent = df.tail(lookback + 1)
    
    # Check if fast was above slow and is now below
    for i in range(len(recent) - 1):
        if (recent["ema_fast"].iloc[i] >= recent["ema_slow"].iloc[i] and
            recent["ema_fast"].iloc[i + 1] < recent["ema_slow"].iloc[i + 1]):
            return True
    
    return False
