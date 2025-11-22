# AlgoTread - Automated Intraday Trading System

A deterministic, rule-based intraday trading engine for Indian equities using Zerodha KiteConnect, with LLM assistance for market regime classification, sentiment analysis, and trade journaling.

## 🎯 Core Principles

**CRITICAL RULE**: The LLM **never** directly decides or submits orders. All trading signals and orders come from deterministic, backtestable Python logic.

- **Deterministic Strategies**: All entry/exit decisions are rule-based
- **LLM as Assistant**: LLM provides advisory information only (regime, sentiment, journaling)
- **Risk-First Design**: Hard-coded risk management with kill switches
- **Modular Architecture**: Clear separation of concerns across layers

## 📋 Features

### Trading Strategies
1. **ORB + Supertrend Breakout**: Opening range breakout with trend confirmation
2. **EMA Trend Following**: EMA(9/21) crossover with VWAP filter
3. **VWAP Mean Reversion**: Range-bound market strategy (regime-dependent)

### News Integration (NEW!)
- **Multi-Source News Fetching**: Aggregates news from Economic Times RSS, Google News, and NSE announcements
- **Smart Caching**: Efficient caching with configurable TTL to minimize API calls
- **Stock Research**: Comprehensive analysis combining news, sentiment, and LLM insights
- **Deduplication**: Automatic removal of duplicate articles across sources
- **Symbol Extraction**: Automatically identifies stocks mentioned in news
- See [News Integration Guide](docs/NEWS_INTEGRATION.md) for details

### Dynamic Watchlist
- **News-Based Stock Selection**: LLM analyzes real news to recommend intraday trading stocks
- **Adaptive Filtering**: Focus on stocks with catalysts and momentum
- **Risk & Direction Filters**: Filter by risk level and expected direction
- **Configurable**: Set confidence thresholds, max stocks, sector focus
- See [Dynamic Watchlist Documentation](docs/DYNAMIC_WATCHLIST.md) for details

### Risk Management
- Position sizing: 1-2% risk per trade
- Daily loss limit: 2-3% of capital
- Time filters: No trades in first 15 minutes, cutoff at 14:45 IST
- Kill switch: Automatic trading halt on limit breach

### LLM Assistance (Advisory Only)
- **Market Regime Classification**: Trending vs. range-bound detection
- **Sentiment Analysis**: News analysis with risky event detection
- **Dynamic Watchlist**: News-based stock recommendations
- **Stock Research**: Comprehensive analysis with opportunity scoring
- **Trade Journaling**: Post-trade analysis for learning

### Telegram Notifications
- **Real-time Trade Alerts**: Instant notifications for every trade entry/exit
- **Risk Alerts**: Warnings when risk limits are approached
- **Daily Summary**: Comprehensive end-of-day trading report
- **AI Insights**: LLM trade reviews included in notifications
- See [Telegram Setup Guide](docs/TELEGRAM_NOTIFICATIONS.md) for details

### Global Market Analysis
- **Pre-Market Context**: Analyze overnight US and Asian markets
- **Strategy Bias**: Adjust trading approach based on global trends
- **Risk Adjustment**: Modify position sizes based on global sentiment
- **Gap Prediction**: Anticipate market opening gaps
- See [Global Market Guide](docs/GLOBAL_MARKET_ANALYSIS.md) for details

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Zerodha Kite API credentials
- OpenAI API key (or other LLM provider)

### Installation

1. **Clone the repository**:
```bash
cd /Users/paragkamble/Documents/algotread
```

2. **Install uv** (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. **Install dependencies**:
```bash
uv sync
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your API credentials
```

### Configuration

Edit `.env` file with your credentials and preferences:

```bash
# Kite API
KITE_API_KEY=your_api_key_here
KITE_API_SECRET=your_api_secret_here
KITE_ACCESS_TOKEN=your_access_token_here

# LLM
LLM_PROVIDER=openai
LLM_API_KEY=your_llm_api_key_here
LLM_MODEL=gpt-4

# Trading
TRADING_MODE=backtest  # backtest, paper, or live
INITIAL_CAPITAL=100000
WATCHLIST=RELIANCE,TCS,INFY,HDFCBANK

# Risk Management
MAX_RISK_PER_TRADE=0.02  # 2%
MAX_DAILY_LOSS=0.03  # 3%
MAX_LOSING_TRADES_PER_DAY=3

# Strategies
ENABLED_STRATEGIES=orb_supertrend,ema_trend
```

### Usage

**Backtest Mode** (recommended to start):
```bash
uv run -m src.main --mode backtest --symbols RELIANCE,TCS --date 2024-01-15
```

**Paper Trading** (live data, no real orders):
```bash
uv run -m src.main --mode paper --symbols NIFTY50
```

**Live Trading** (⚠️ use with extreme caution):
```bash
uv run -m src.main --mode live --symbols BANKNIFTY
```

## 📁 Project Structure

```
.
├── src/
│   ├── config.py              # Configuration management
│   ├── main.py                # Main entry point
│   ├── core/
│   │   ├── indicators.py      # Technical indicators
│   │   ├── risk.py            # Risk management
│   │   └── strategies/
│   │       ├── base.py        # Strategy base class
│   │       ├── orb_supertrend.py
│   │       ├── ema_trend.py
│   │       └── vwap_reversion.py
│   ├── data/
│   │   ├── models.py          # Data models
│   │   ├── fetcher.py         # Data fetching (TODO)
│   │   └── storage.py         # Data storage (TODO)
│   ├── execution/
│   │   ├── kite_broker.py     # Kite integration (TODO)
│   │   └── order_validator.py # Order validation (TODO)
│   └── llm/
│       ├── llm_client.py      # LLM client abstraction
│       ├── regime_classifier.py
│       ├── sentiment_analyzer.py
│       └── trade_journal.py
├── tests/                     # Unit tests
├── .env.example               # Environment template
├── pyproject.toml             # Dependencies
└── README.md
```

## 🔒 Safety Features

### LLM Safety Boundaries
- LLM outputs are **never** directly passed to order execution
- All LLM calls are clearly marked as "ADVISORY ONLY"
- Strict JSON schema validation on all LLM responses
- LLM is used for:
  - ✅ Market regime classification (enables/disables strategies)
  - ✅ Sentiment analysis (adjusts position size or blocks trades)
  - ✅ Trade journaling (post-trade analysis)
  - ❌ **NEVER** for order decisions

### Risk Controls
- **Position Sizing**: Automatic calculation based on stop loss and risk percentage
- **Daily Limits**: Trading halts when daily loss limit or max losing trades reached
- **Time Filters**: No trades during first 15 minutes or after 14:45 IST
- **Kill Switch**: Manual or automatic trading halt
- **Validation Pipeline**: Multiple checks before order submission

## 🧪 Testing

Run unit tests:
```bash
uv run pytest tests/
```

Run with coverage:
```bash
uv run pytest --cov=src tests/
```

Type checking:
```bash
uv run mypy src/
```

## 📊 Strategy Details

### 1. ORB + Supertrend Breakout

**Entry (Long)**:
- Price breaks above ORB high (first 15 minutes)
- Supertrend is bullish
- Volume > 1.5× recent average
- RSI > 55

**Exit**:
- Supertrend turns bearish
- Stop loss hit
- Target reached

### 2. EMA Trend Following

**Entry (Long)**:
- EMA(9) crosses above EMA(21)
- Price > VWAP
- Optional: RSI confirmation

**Exit**:
- EMA(9) crosses below EMA(21)
- Stop loss hit
- Target reached

### 3. VWAP Mean Reversion

**Entry (Long)**:
- Market regime is RANGE_BOUND
- Price < VWAP by threshold percentage
- RSI oversold (< 30)

**Exit**:
- Price reaches VWAP
- Stop loss hit
- Target reached

## 🔧 Development

### Adding a New Strategy

1. Create a new file in `src/core/strategies/`
2. Inherit from `BaseStrategy`
3. Implement `evaluate()` and `get_parameters()` methods
4. Add to `ENABLED_STRATEGIES` in `.env`

Example:
```python
from src.core.strategies.base import BaseStrategy
from src.data.models import TradeInstruction, StrategySignal

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("my_strategy")
    
    def evaluate(self, df, current_position=None, regime=None, sentiment=None):
        # Your logic here
        return TradeInstruction(...)
    
    def get_parameters(self):
        return {"param1": value1}
```

### Adding a New Indicator

Add to `src/core/indicators.py`:
```python
def calculate_my_indicator(df: pd.DataFrame, period: int) -> pd.Series:
    """Calculate my custom indicator."""
    # Your calculation here
    return result
```

## ⚠️ Important Notes

### Before Live Trading
1. **Backtest thoroughly** with historical data
2. **Paper trade** for at least 1-2 weeks
3. **Start with minimal capital**
4. **Monitor first few trades manually**
5. **Verify all risk controls are working**

### API Rate Limits
- Kite API has rate limits (3 requests/second)
- Historical data: 3 requests/second
- WebSocket: Real-time data has no rate limit

### Market Hours
- NSE: 9:15 AM to 3:30 PM IST
- No trades in first 15 minutes (configurable)
- No new positions after 14:45 IST (configurable)

## 📝 License

This project is for educational purposes. Use at your own risk. The authors are not responsible for any financial losses.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## 📧 Support

For issues and questions, please open a GitHub issue.

---

**Disclaimer**: This software is provided "as is" without warranty. Trading involves substantial risk of loss. Past performance is not indicative of future results.
