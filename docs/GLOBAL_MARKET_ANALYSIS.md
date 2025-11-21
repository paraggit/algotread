# Global Market Analysis

## Overview

Analyze overnight global markets (US, Singapore, Asian markets) to provide context for Indian market trading. This helps make informed decisions before market open.

## Why This Matters

Indian markets are significantly influenced by global trends:
- **US Markets**: Strong correlation, especially for IT and tech stocks
- **Asian Markets**: Regional sentiment affects Indian indices
- **Overnight News**: Global events impact opening gaps
- **Risk Sentiment**: VIX and global volatility indicators

## How It Works

```
US Markets (Previous Close) → 
Asian Markets (Current) →
Global News →
    ↓
LLM Analysis →
    ↓
Strategy Bias + Risk Adjustments →
    ↓
Adjusted Trading Parameters
```

## Configuration

Add to your `.env` file:

```bash
# Global Market Analysis
ENABLE_GLOBAL_MARKET_ANALYSIS=true
GLOBAL_MARKET_ANALYSIS_TIME=08:30  # Run at 8:30 AM IST (before market open)
ADJUST_STRATEGY_FROM_GLOBAL=true
GLOBAL_MARKET_MIN_CONFIDENCE=0.6
```

## Usage Example

```python
from src.llm.global_market_analyzer import (
    GlobalMarketAnalyzer,
    fetch_us_markets,
    fetch_asian_markets
)

# Initialize
analyzer = GlobalMarketAnalyzer(llm_client)

# Fetch data
us_markets = fetch_us_markets()  # S&P 500, Nasdaq, Dow, VIX
asian_markets = fetch_asian_markets()  # Nikkei, Hang Seng, STI, KOSPI

# Analyze
analysis = analyzer.analyze_global_markets(
    us_markets=us_markets,
    asian_markets=asian_markets,
    news_headlines=global_news
)

# Get strategy adjustments
adjustments = analyzer.get_strategy_adjustments(analysis)
```

## LLM Output

```json
{
  "overall_trend": "bullish",
  "confidence": 0.85,
  "us_markets_summary": "Tech rally led by strong earnings, S&P +0.5%",
  "asian_markets_summary": "Mixed, Nikkei up, HSI down on China concerns",
  "key_drivers": [
    "Fed dovish comments",
    "Strong US tech earnings",
    "Oil prices stable"
  ],
  "indian_market_outlook": "Expect gap up open, IT stocks likely to outperform",
  "recommended_strategy_bias": "aggressive",
  "expected_gap": "gap_up",
  "risk_level": "medium"
}
```

## Strategy Bias Types

### Aggressive
- **When**: Strong global trends, high confidence
- **Adjustments**:
  - Position size: 120% of normal
  - Preferred strategies: ORB breakout, EMA trend
  - Max positions: 4
- **Use**: Favor breakout strategies, larger positions

### Moderate (Default)
- **When**: Normal market conditions
- **Adjustments**:
  - Position size: 100% of normal
  - All strategies enabled
  - Max positions: 3
- **Use**: Balanced approach

### Conservative
- **When**: Mixed signals, uncertainty
- **Adjustments**:
  - Position size: 70% of normal
  - Preferred strategies: VWAP reversion
  - Risk multiplier: 0.8
  - Max positions: 2
- **Use**: Reduce exposure, tighter stops

### Defensive
- **When**: Negative global trends, high risk
- **Adjustments**:
  - Position size: 50% of normal
  - Consider staying out
  - Risk multiplier: 0.5
  - Max positions: 1
- **Use**: Minimal trading or skip the day

## Integration with Trading System

### Pre-Market Routine (8:30 AM IST)

```python
# 1. Fetch global data
us_markets = fetch_us_markets()
asian_markets = fetch_asian_markets()
news = fetch_global_news()

# 2. Analyze
analysis = analyzer.analyze_global_markets(
    us_markets, asian_markets, news
)

# 3. Get adjustments
adjustments = analyzer.get_strategy_adjustments(analysis)

# 4. Apply to trading system
if analysis.recommended_strategy_bias == "defensive":
    logger.warning("Defensive stance recommended - consider staying out")
    # Option: Skip trading for the day
    
elif analysis.recommended_strategy_bias == "aggressive":
    logger.info("Aggressive stance - increasing position sizes")
    # Increase position sizes
    base_risk *= adjustments['position_size_multiplier']

# 5. Filter strategies
enabled_strategies = [
    s for s in all_strategies
    if s.name in adjustments['preferred_strategies']
]

# 6. Adjust risk
risk_manager.max_risk_per_trade *= adjustments['risk_multiplier']

# 7. Send Telegram notification
if telegram_notifier:
    message = f"""
🌐 GLOBAL MARKET ANALYSIS

Trend: {analysis.overall_trend.value.upper()}
Expected Gap: {analysis.expected_gap.upper()}
Strategy Bias: {analysis.recommended_strategy_bias.upper()}

🇺🇸 {analysis.us_markets_summary}
🌏 {analysis.asian_markets_summary}

🇮🇳 {analysis.indian_market_outlook}

Position Size: {adjustments['position_size_multiplier']:.0%}
Preferred Strategies: {', '.join(adjustments['preferred_strategies'])}
    """
    telegram_notifier.send_message_sync(message)
```

## Market Correlations

### IT Sector
- **Correlation**: High with US tech (Nasdaq)
- **Impact**: If Nasdaq +1%, Indian IT likely +0.7-1%
- **Stocks**: TCS, Infosys, Wipro, HCL Tech

### Banking Sector
- **Correlation**: Moderate with global financials
- **Impact**: Affected by Fed policy, global rates
- **Stocks**: HDFC Bank, ICICI Bank, Axis Bank

### Energy Sector
- **Correlation**: High with oil prices
- **Impact**: Brent crude movements
- **Stocks**: Reliance, ONGC, BPCL

### Metals & Mining
- **Correlation**: High with commodity prices
- **Impact**: China demand, global growth
- **Stocks**: Tata Steel, Hindalco, JSW Steel

## Data Sources (TODO)

### US Markets
- **Yahoo Finance API**: Free, reliable
- **Alpha Vantage**: Free tier available
- **IEX Cloud**: Good for real-time data
- **Twelve Data**: Comprehensive coverage

### Asian Markets
- **Yahoo Finance**: Covers major indices
- **Investing.com**: Good coverage
- **TradingView**: Real-time data

### Global News
- **Bloomberg API**: Premium, comprehensive
- **Reuters API**: Good coverage
- **CNBC RSS**: Free, decent coverage
- **Financial Times**: Quality analysis

## Example Implementation

```python
import yfinance as yf

def fetch_us_markets():
    """Fetch US market data using yfinance."""
    tickers = {
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "Dow Jones": "^DJI",
        "VIX": "^VIX"
    }
    
    markets = {}
    for name, ticker in tickers.items():
        data = yf.Ticker(ticker).history(period="1d")
        if not data.empty:
            close = data['Close'].iloc[-1]
            prev_close = data['Close'].iloc[-2] if len(data) > 1 else close
            change_pct = ((close - prev_close) / prev_close) * 100
            
            markets[name] = MarketData(
                index_name=name,
                close=close,
                change_pct=change_pct
            )
    
    return markets
```

## Benefits

1. **Pre-Market Context**: Know global sentiment before trading
2. **Risk Management**: Adjust position sizes based on global risk
3. **Strategy Selection**: Choose appropriate strategies for the day
4. **Gap Prediction**: Anticipate opening gaps
5. **Sector Focus**: Identify sectors likely to outperform

## Limitations

1. **Correlation Not Causation**: Indian markets can diverge
2. **Local Factors**: Domestic news can override global trends
3. **Time Lag**: Asian markets may have already reacted
4. **LLM Accuracy**: Analysis is probabilistic, not guaranteed

## Best Practices

1. **Run Before Market Open**: Analyze at 8:30 AM IST
2. **Combine with Local News**: Don't ignore domestic factors
3. **Use as Context**: Not a standalone trading signal
4. **Track Accuracy**: Monitor how well predictions match reality
5. **Adjust Over Time**: Refine based on historical accuracy

---

**Remember**: Global market analysis provides **context and bias**, not trading signals. Final decisions remain with your deterministic strategies and risk management.
