"""
Data models for the trading system.
Defines core data structures using Pydantic for validation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class StrategySignal(str, Enum):
    """Trading signal enum."""
    NO_TRADE = "no_trade"
    ENTRY_LONG = "entry_long"
    EXIT_LONG = "exit_long"
    ENTRY_SHORT = "entry_short"
    EXIT_SHORT = "exit_short"


class OrderType(str, Enum):
    """Order type enum."""
    MARKET = "market"
    LIMIT = "limit"
    SL_MARKET = "sl_market"
    SL_LIMIT = "sl_limit"


class OrderStatus(str, Enum):
    """Order status enum."""
    PENDING = "pending"
    OPEN = "open"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class MarketRegime(str, Enum):
    """Market regime classification."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGE_BOUND = "range_bound"
    HIGH_VOLATILITY_NOISE = "high_volatility_noise"


class Sentiment(str, Enum):
    """Sentiment classification."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class NewsSource(str, Enum):
    """News source classification."""
    ECONOMIC_TIMES = "economic_times"
    GOOGLE_NEWS = "google_news"
    NSE_ANNOUNCEMENTS = "nse_announcements"
    MONEYCONTROL = "moneycontrol"
    UNKNOWN = "unknown"


class NewsArticle(BaseModel):
    """News article data."""
    title: str
    source: NewsSource
    url: str
    published_at: datetime
    summary: Optional[str] = None
    symbols: list[str] = Field(default_factory=list, description="Stock symbols mentioned")
    content: Optional[str] = None
    
    def __hash__(self) -> int:
        """Hash based on URL for deduplication."""
        return hash(self.url)
    
    def __eq__(self, other: object) -> bool:
        """Equality based on URL for deduplication."""
        if not isinstance(other, NewsArticle):
            return False
        return self.url == other.url


class StockResearch(BaseModel):
    """Comprehensive stock research combining news and sentiment."""
    symbol: str
    timestamp: datetime
    news_articles: list[NewsArticle] = Field(default_factory=list)
    sentiment: Optional['SentimentAnalysis'] = None  # Forward reference
    opportunity_score: float = Field(ge=0.0, le=1.0, description="Overall opportunity score")
    key_catalysts: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    recommendation: str = Field(description="LLM recommendation summary")



class OHLCVBar(BaseModel):
    """OHLCV candlestick bar."""
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    symbol: str


class Tick(BaseModel):
    """Live market tick."""
    timestamp: datetime
    symbol: str
    last_price: float = Field(gt=0)
    volume: int = Field(ge=0)
    bid: Optional[float] = None
    ask: Optional[float] = None
    oi: Optional[int] = None  # Open interest for derivatives


class Instrument(BaseModel):
    """Trading instrument details."""
    symbol: str
    exchange: str = Field(default="NSE")
    instrument_token: Optional[int] = None
    lot_size: int = Field(default=1, ge=1)
    tick_size: float = Field(default=0.05, gt=0)


class TradeInstruction(BaseModel):
    """Trade instruction from strategy."""
    signal: StrategySignal
    symbol: str
    quantity: int = Field(ge=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    target: Optional[float] = Field(default=None, gt=0)
    reason: str = Field(description="Human-readable reason for the trade")
    strategy_name: str
    entry_price: Optional[float] = None
    order_type: OrderType = OrderType.MARKET


class Order(BaseModel):
    """Order details."""
    order_id: str
    symbol: str
    quantity: int
    order_type: OrderType
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    status: OrderStatus
    filled_quantity: int = Field(default=0, ge=0)
    average_price: Optional[float] = None
    timestamp: datetime
    parent_order_id: Optional[str] = None  # For SL/target orders


class Position(BaseModel):
    """Trading position."""
    symbol: str
    quantity: int  # Positive for long, negative for short
    average_price: float = Field(gt=0)
    current_price: float = Field(gt=0)
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    entry_time: datetime
    strategy_name: str
    unrealized_pnl: float = 0.0

    def update_pnl(self, current_price: float) -> None:
        """Update unrealized P&L."""
        self.current_price = current_price
        if self.quantity > 0:  # Long position
            self.unrealized_pnl = (current_price - self.average_price) * self.quantity
        else:  # Short position
            self.unrealized_pnl = (self.average_price - current_price) * abs(self.quantity)


class Trade(BaseModel):
    """Completed trade record."""
    trade_id: str
    symbol: str
    strategy_name: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    exit_reason: str  # "target_hit", "stop_loss", "time_exit", "manual"
    regime: Optional[MarketRegime] = None
    sentiment: Optional[Sentiment] = None


class RegimeClassification(BaseModel):
    """Market regime classification from LLM."""
    regime: MarketRegime
    confidence: float = Field(ge=0.0, le=1.0)
    comment: str


class SentimentAnalysis(BaseModel):
    """Sentiment analysis from LLM."""
    ticker: str
    sentiment: Sentiment
    confidence: float = Field(ge=0.0, le=1.0)
    is_event_risky: bool
    rationale: str


class TradeJournalEntry(BaseModel):
    """Trade journal entry from LLM."""
    trade_id: str
    entry_reason: str
    exit_review: str
    entry_label: str  # "GOOD_ENTRY" or "BAD_ENTRY"
    exit_label: str  # "GOOD_EXIT" or "BAD_EXIT"
    timestamp: datetime


class Portfolio(BaseModel):
    """Portfolio state."""
    cash: float = Field(ge=0)
    positions: dict[str, Position] = Field(default_factory=dict)
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    daily_pnl: float = 0.0
    daily_trades: int = 0
    daily_losing_trades: int = 0

    def get_total_value(self) -> float:
        """Get total portfolio value."""
        return self.cash + self.unrealized_pnl

    def update_unrealized_pnl(self) -> None:
        """Update total unrealized P&L from all positions."""
        self.unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())

    def add_position(self, position: Position) -> None:
        """Add or update a position."""
        self.positions[position.symbol] = position
        self.update_unrealized_pnl()

    def close_position(self, symbol: str, exit_price: float) -> Optional[Trade]:
        """Close a position and return trade record."""
        if symbol not in self.positions:
            return None
        
        pos = self.positions.pop(symbol)
        pnl = pos.unrealized_pnl
        self.realized_pnl += pnl
        self.daily_pnl += pnl
        self.cash += (pos.average_price * abs(pos.quantity)) + pnl
        
        self.total_trades += 1
        self.daily_trades += 1
        
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
            self.daily_losing_trades += 1
        
        self.update_unrealized_pnl()
        
        return Trade(
            trade_id=f"{symbol}_{pos.entry_time.timestamp()}",
            symbol=symbol,
            strategy_name=pos.strategy_name,
            entry_time=pos.entry_time,
            exit_time=datetime.now(),
            entry_price=pos.average_price,
            exit_price=exit_price,
            quantity=abs(pos.quantity),
            pnl=pnl,
            pnl_percent=(pnl / (pos.average_price * abs(pos.quantity))) * 100,
            stop_loss=pos.stop_loss,
            target=pos.target,
            exit_reason="manual",  # Will be updated by caller
        )

    def reset_daily_stats(self) -> None:
        """Reset daily statistics."""
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_losing_trades = 0
