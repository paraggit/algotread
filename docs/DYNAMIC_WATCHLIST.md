# Dynamic Watchlist Feature

## Overview

The dynamic watchlist feature uses LLM to analyze news headlines and recommend stocks for intraday trading. This is a **smart filtering mechanism** that maintains our core safety principles.

## How It Works

```
News Headlines → LLM Analysis → Stock Recommendations → Watchlist
                                                            ↓
                                            Strategies Evaluate → Risk Manager → Orders
```

**Key Point:** LLM only **suggests which stocks to watch**. It does NOT trigger trades. Strategies still make all entry/exit decisions deterministically.

## Configuration

Add to your `.env` file:

```bash
# Enable dynamic watchlist
USE_DYNAMIC_WATCHLIST=true
DYNAMIC_WATCHLIST_MAX_STOCKS=10
DYNAMIC_WATCHLIST_MIN_CONFIDENCE=0.6
DYNAMIC_WATCHLIST_SECTOR_FILTER=Technology,Banking
DYNAMIC_WATCHLIST_MAX_RISK=MEDIUM
DYNAMIC_WATCHLIST_DIRECTION_FILTER=UP  # Optional: only bullish stocks
NEWS_REFRESH_INTERVAL=60  # Refresh every 60 minutes
```

## Usage Example

```python
from src.llm.llm_client import create_llm_client
from src.llm.dynamic_watchlist import DynamicWatchlistGenerator
from src.config import get_config

# Setup
config = get_config()
llm_client = create_llm_client(config.llm)
watchlist_gen = DynamicWatchlistGenerator(llm_client, max_stocks=10)

# Fetch news (TODO: implement actual news API)
news_headlines = [
    {
        "headline": "Reliance announces Q3 results, beats estimates",
        "source": "MoneyControl",
        "timestamp": "2024-01-15T09:00:00",
        "url": "https://..."
    },
    # ... more headlines
]

# Generate watchlist
watchlist = watchlist_gen.generate_watchlist(
    news_headlines=news_headlines,
    min_confidence=0.6
)

# Get symbols
symbols = watchlist_gen.get_symbols_list(watchlist)
# ['RELIANCE', 'TCS', 'INFY', ...]

# Filter by direction (for long-only strategies)
bullish_stocks = watchlist_gen.filter_by_direction(watchlist, "UP")

# Filter by risk
low_risk_stocks = watchlist_gen.filter_by_risk(watchlist, "LOW")
```

## LLM Output Format

The LLM returns structured recommendations:

```json
{
  "stocks": [
    {
      "symbol": "RELIANCE",
      "reason": "Q3 earnings beat, strong volume expected",
      "catalyst": "Quarterly results announcement",
      "confidence": 0.85,
      "expected_direction": "UP",
      "risk_level": "MEDIUM"
    }
  ],
  "market_summary": "Market bullish on IT sector, banking under pressure"
}
```

## Safety Features

1. **Confidence Filtering**: Only stocks above threshold are included
2. **Risk Filtering**: Can limit to LOW or MEDIUM risk stocks
3. **Direction Filtering**: Can filter for UP/DOWN/VOLATILE
4. **Max Stocks**: Limits watchlist size to prevent overtrading
5. **Deterministic Strategies**: Final trading decisions remain rule-based

## Integration with Main System

In `main.py`, you can integrate like this:

```python
if config.use_dynamic_watchlist:
    # Generate dynamic watchlist
    news = fetch_news_headlines()
    watchlist = watchlist_gen.generate_watchlist(news)
    symbols = watchlist_gen.get_symbols_list(watchlist)
    
    logger.info(f"Using dynamic watchlist: {symbols}")
else:
    # Use static watchlist from config
    symbols = config.watchlist
    logger.info(f"Using static watchlist: {symbols}")

# Rest of trading logic remains the same
for symbol in symbols:
    # Fetch data, calculate indicators, evaluate strategies...
```

## News Sources (TODO)

To implement fully, you'll need to fetch news from:

1. **MoneyControl API** - Indian market news
2. **Economic Times RSS** - Business news
3. **NSE Announcements** - Corporate actions
4. **Google News Finance** - General financial news
5. **Twitter/X** - Real-time sentiment (optional)

Example implementation:

```python
def fetch_news_headlines(sources=None):
    headlines = []
    
    # MoneyControl
    mc_news = requests.get("https://api.moneycontrol.com/...")
    headlines.extend(parse_moneycontrol(mc_news))
    
    # Economic Times RSS
    et_rss = feedparser.parse("https://economictimes.indiatimes.com/...")
    headlines.extend(parse_et_rss(et_rss))
    
    # NSE Announcements
    nse_announcements = requests.get("https://www.nseindia.com/api/...")
    headlines.extend(parse_nse(nse_announcements))
    
    return headlines
```

## Benefits

1. **Adaptive**: Focuses on stocks with current catalysts
2. **Efficient**: Avoids analyzing quiet stocks
3. **News-Driven**: Captures momentum from events
4. **Flexible**: Can filter by sector, risk, direction
5. **Safe**: LLM only suggests, doesn't trade

## Limitations

1. **News Quality**: Depends on quality of news sources
2. **LLM Accuracy**: Recommendations are probabilistic
3. **Latency**: News fetching and LLM calls add delay
4. **Cost**: LLM API calls cost money (but minimal for once/hour)

## Recommendation

Start with **static watchlist** for backtesting and initial paper trading. Once comfortable, enable **dynamic watchlist** for live trading to capture news-driven opportunities.
