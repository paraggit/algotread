"""Example usage of global market analyzer."""

from src.config import get_config
from src.llm.llm_client import create_llm_client
from src.llm.global_market_analyzer import (
    GlobalMarketAnalyzer,
    MarketData,
    fetch_us_markets,
    fetch_asian_markets,
    fetch_global_news
)


def main():
    """Example of using global market analyzer."""
    # Setup
    config = get_config()
    llm_client = create_llm_client(config.llm)
    analyzer = GlobalMarketAnalyzer(llm_client)
    
    # Fetch global market data (TODO: implement actual fetching)
    us_markets = fetch_us_markets()
    asian_markets = fetch_asian_markets()
    news = fetch_global_news()
    
    print("\n" + "="*80)
    print("GLOBAL MARKET ANALYSIS")
    print("="*80)
    
    print("\n📊 US Markets (Previous Close):")
    for name, data in us_markets.items():
        print(f"  {name}: {data.change_pct:+.2f}%")
    
    print("\n🌏 Asian Markets:")
    for name, data in asian_markets.items():
        print(f"  {name}: {data.change_pct:+.2f}%")
    
    # Analyze
    analysis = analyzer.analyze_global_markets(
        us_markets=us_markets,
        asian_markets=asian_markets,
        news_headlines=news
    )
    
    if analysis:
        print(f"\n{'='*80}")
        print("ANALYSIS RESULTS")
        print(f"{'='*80}")
        
        print(f"\n🌐 Overall Trend: {analysis.overall_trend.value.upper()}")
        print(f"   Confidence: {analysis.confidence:.0%}")
        
        print(f"\n🇺🇸 US Markets: {analysis.us_markets_summary}")
        print(f"🌏 Asian Markets: {analysis.asian_markets_summary}")
        
        print(f"\n🔑 Key Drivers:")
        for driver in analysis.key_drivers:
            print(f"   • {driver}")
        
        print(f"\n🇮🇳 Indian Market Outlook:")
        print(f"   {analysis.indian_market_outlook}")
        
        print(f"\n📈 Expected Gap: {analysis.expected_gap.upper()}")
        print(f"⚠️  Risk Level: {analysis.risk_level.upper()}")
        print(f"🎯 Strategy Bias: {analysis.recommended_strategy_bias.upper()}")
        
        # Get strategy adjustments
        adjustments = analyzer.get_strategy_adjustments(analysis)
        
        print(f"\n{'='*80}")
        print("RECOMMENDED ADJUSTMENTS")
        print(f"{'='*80}")
        
        print(f"\nPosition Size: {adjustments['position_size_multiplier']:.0%} of normal")
        print(f"Risk Multiplier: {adjustments['risk_multiplier']:.0%}")
        print(f"Max Positions: {adjustments['max_positions']}")
        print(f"Enable Short Trades: {adjustments['enable_short_trades']}")
        
        if adjustments['preferred_strategies']:
            print(f"\nPreferred Strategies:")
            for strategy in adjustments['preferred_strategies']:
                print(f"   • {strategy}")
        else:
            print(f"\n⚠️  Consider staying out of the market today")
        
        print(f"\n{'='*80}")
        
        # Example: How to use in trading system
        print("\n💡 Integration Example:")
        print(f"""
# In your main trading loop:
if analysis.recommended_strategy_bias == "defensive":
    logger.warning("Global markets suggest defensive stance - reducing activity")
    # Reduce position sizes, tighten stops, or skip trading
    
elif analysis.recommended_strategy_bias == "aggressive":
    logger.info("Global markets bullish - increasing position sizes")
    # Increase position sizes, favor breakout strategies
    
# Adjust risk based on global analysis
base_risk = 0.02  # 2%
adjusted_risk = base_risk * adjustments['risk_multiplier']

# Filter strategies based on recommendations
enabled_strategies = [
    s for s in all_strategies 
    if s.name in adjustments['preferred_strategies']
]
        """)
        
    else:
        print("\n❌ Failed to analyze global markets")


if __name__ == "__main__":
    main()
