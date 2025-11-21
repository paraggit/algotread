"""Example usage of dynamic watchlist generator."""

from src.config import get_config
from src.llm.llm_client import create_llm_client
from src.llm.dynamic_watchlist import (
    DynamicWatchlistGenerator,
    fetch_news_headlines,
    fetch_market_indices
)


def main():
    """Example of using dynamic watchlist."""
    # Load configuration
    config = get_config()
    
    # Create LLM client
    llm_client = create_llm_client(config.llm)
    
    # Create watchlist generator
    watchlist_gen = DynamicWatchlistGenerator(llm_client, max_stocks=10)
    
    # Fetch news (TODO: implement actual news fetching)
    news_headlines = fetch_news_headlines()
    
    # Fetch market indices (TODO: implement actual index fetching)
    market_indices = fetch_market_indices()
    
    # Generate dynamic watchlist
    watchlist = watchlist_gen.generate_watchlist(
        news_headlines=news_headlines,
        market_indices=market_indices,
        sector_filter=["Technology", "Banking"],  # Optional
        min_confidence=0.6
    )
    
    if watchlist:
        print(f"\n{'='*80}")
        print(f"Dynamic Watchlist Generated at {watchlist.timestamp}")
        print(f"{'='*80}")
        print(f"\nMarket Summary: {watchlist.market_summary}\n")
        
        print(f"Recommended Stocks ({len(watchlist.stocks)}):")
        print(f"{'-'*80}")
        
        for stock in watchlist.stocks:
            print(f"\n{stock.symbol}")
            print(f"  Reason: {stock.reason}")
            print(f"  Catalyst: {stock.catalyst}")
            print(f"  Direction: {stock.expected_direction} | Risk: {stock.risk_level}")
            print(f"  Confidence: {stock.confidence:.0%}")
        
        print(f"\n{'='*80}")
        
        # Get just the symbols
        symbols = watchlist_gen.get_symbols_list(watchlist)
        print(f"\nSymbols for trading: {', '.join(symbols)}")
        
        # Filter by direction (e.g., only UP stocks for long-only strategies)
        up_stocks = watchlist_gen.filter_by_direction(watchlist, "UP")
        print(f"Bullish stocks: {', '.join(up_stocks)}")
        
        # Filter by risk
        low_risk_stocks = watchlist_gen.filter_by_risk(watchlist, "LOW")
        print(f"Low risk stocks: {', '.join(low_risk_stocks)}")
        
    else:
        print("Failed to generate watchlist")


if __name__ == "__main__":
    main()
