"""
Configuration module for the automated trading system.
Loads environment variables and provides typed configuration objects.
"""

import os
from enum import Enum
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Load environment variables from .env file
load_dotenv()


class TradingMode(str, Enum):
    """Trading mode enum."""
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class LLMProvider(str, Enum):
    """LLM provider enum."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class DataStorage(str, Enum):
    """Data storage type enum."""
    CSV = "csv"
    SQLITE = "sqlite"


class KiteConfig(BaseModel):
    """Kite API configuration."""
    api_key: str = Field(..., description="Kite API key")
    api_secret: str = Field(..., description="Kite API secret")
    access_token: str = Field(..., description="Kite access token")

    @classmethod
    def from_env(cls) -> "KiteConfig":
        """Load from environment variables."""
        return cls(
            api_key=os.getenv("KITE_API_KEY", ""),
            api_secret=os.getenv("KITE_API_SECRET", ""),
            access_token=os.getenv("KITE_ACCESS_TOKEN", ""),
        )


class LLMConfig(BaseModel):
    """LLM configuration."""
    provider: LLMProvider = Field(default=LLMProvider.OPENAI)
    api_key: str = Field(..., description="LLM API key")
    model: str = Field(default="gpt-4", description="Model name")

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load from environment variables."""
        return cls(
            provider=LLMProvider(os.getenv("LLM_PROVIDER", "openai")),
            api_key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", "gpt-4"),
        )


class RiskConfig(BaseModel):
    """Risk management configuration."""
    max_risk_per_trade: float = Field(default=0.02, ge=0.0, le=1.0, description="Max risk per trade as fraction of capital")
    max_daily_loss: float = Field(default=0.03, ge=0.0, le=1.0, description="Max daily loss as fraction of capital")
    max_losing_trades_per_day: int = Field(default=3, ge=1, description="Max number of losing trades per day")
    min_minutes_after_open: int = Field(default=15, ge=0, description="No trades in first N minutes after market open")
    cutoff_time: str = Field(default="14:45", description="No new positions after this time (HH:MM IST)")

    @classmethod
    def from_env(cls) -> "RiskConfig":
        """Load from environment variables."""
        return cls(
            max_risk_per_trade=float(os.getenv("MAX_RISK_PER_TRADE", "0.02")),
            max_daily_loss=float(os.getenv("MAX_DAILY_LOSS", "0.03")),
            max_losing_trades_per_day=int(os.getenv("MAX_LOSING_TRADES_PER_DAY", "3")),
            min_minutes_after_open=int(os.getenv("MIN_MINUTES_AFTER_OPEN", "15")),
            cutoff_time=os.getenv("CUTOFF_TIME", "14:45"),
        )


class StrategyConfig(BaseModel):
    """Strategy configuration."""
    enabled_strategies: List[str] = Field(default_factory=list, description="List of enabled strategy names")
    
    # ORB + Supertrend parameters
    orb_period_minutes: int = Field(default=15, ge=1)
    orb_volume_multiplier: float = Field(default=1.5, ge=1.0)
    orb_rsi_threshold: float = Field(default=55.0, ge=0.0, le=100.0)
    
    # EMA parameters
    ema_fast: int = Field(default=9, ge=1)
    ema_slow: int = Field(default=21, ge=1)
    
    # Supertrend parameters
    supertrend_period: int = Field(default=7, ge=1)
    supertrend_multiplier: float = Field(default=3.0, ge=0.0)
    
    # RSI parameters
    rsi_period: int = Field(default=14, ge=1)
    
    # ATR parameters
    atr_period: int = Field(default=14, ge=1)

    @field_validator("enabled_strategies", mode="before")
    @classmethod
    def parse_strategies(cls, v):
        """Parse comma-separated strategies."""
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @classmethod
    def from_env(cls) -> "StrategyConfig":
        """Load from environment variables."""
        return cls(
            enabled_strategies=os.getenv("ENABLED_STRATEGIES", "orb_supertrend,ema_trend"),
            orb_period_minutes=int(os.getenv("ORB_PERIOD_MINUTES", "15")),
            orb_volume_multiplier=float(os.getenv("ORB_VOLUME_MULTIPLIER", "1.5")),
            orb_rsi_threshold=float(os.getenv("ORB_RSI_THRESHOLD", "55")),
            ema_fast=int(os.getenv("EMA_FAST", "9")),
            ema_slow=int(os.getenv("EMA_SLOW", "21")),
            supertrend_period=int(os.getenv("SUPERTREND_PERIOD", "7")),
            supertrend_multiplier=float(os.getenv("SUPERTREND_MULTIPLIER", "3.0")),
            rsi_period=int(os.getenv("RSI_PERIOD", "14")),
            atr_period=int(os.getenv("ATR_PERIOD", "14")),
        )


class DataConfig(BaseModel):
    """Data configuration."""
    storage: DataStorage = Field(default=DataStorage.SQLITE)
    interval: str = Field(default="5minute", description="Data interval: 1minute, 5minute, 15minute")
    backtest_start_date: str = Field(default="2024-01-01", description="Backtest start date (YYYY-MM-DD)")
    backtest_end_date: str = Field(default="2024-12-31", description="Backtest end date (YYYY-MM-DD)")

    @classmethod
    def from_env(cls) -> "DataConfig":
        """Load from environment variables."""
        return cls(
            storage=DataStorage(os.getenv("DATA_STORAGE", "sqlite")),
            interval=os.getenv("DATA_INTERVAL", "5minute"),
            backtest_start_date=os.getenv("BACKTEST_START_DATE", "2024-01-01"),
            backtest_end_date=os.getenv("BACKTEST_END_DATE", "2024-12-31"),
        )


class TradingConfig(BaseModel):
    """Main trading configuration."""
    mode: TradingMode = Field(default=TradingMode.BACKTEST)
    initial_capital: float = Field(default=100000.0, gt=0.0, description="Initial capital in INR")
    watchlist: List[str] = Field(default_factory=list, description="List of symbols to trade")
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="logs/trading.log", description="Log file path")
    
    kite: KiteConfig
    llm: LLMConfig
    risk: RiskConfig
    strategy: StrategyConfig
    data: DataConfig

    @field_validator("watchlist", mode="before")
    @classmethod
    def parse_watchlist(cls, v):
        """Parse comma-separated watchlist."""
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @classmethod
    def from_env(cls) -> "TradingConfig":
        """Load complete configuration from environment variables."""
        return cls(
            mode=TradingMode(os.getenv("TRADING_MODE", "backtest")),
            initial_capital=float(os.getenv("INITIAL_CAPITAL", "100000")),
            watchlist=os.getenv("WATCHLIST", "RELIANCE,TCS,INFY,HDFCBANK"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "logs/trading.log"),
            kite=KiteConfig.from_env(),
            llm=LLMConfig.from_env(),
            risk=RiskConfig.from_env(),
            strategy=StrategyConfig.from_env(),
            data=DataConfig.from_env(),
        )

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        log_path = Path(self.log_file).parent
        log_path.mkdir(parents=True, exist_ok=True)
        
        Path("data").mkdir(exist_ok=True)
        Path("trades").mkdir(exist_ok=True)
        Path("orders").mkdir(exist_ok=True)
        Path("backtest_results").mkdir(exist_ok=True)


# Global configuration instance
config: TradingConfig | None = None


def get_config() -> TradingConfig:
    """Get or create the global configuration instance."""
    global config
    if config is None:
        config = TradingConfig.from_env()
        config.ensure_directories()
    return config
