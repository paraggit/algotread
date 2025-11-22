"""Example usage of stock research module."""

from src.config import get_config
from src.data.news_fetcher import NewsFetcher
from src.llm.llm_client import create_llm_client
from src.llm.stock_research import StockResearcher


def main():
    """Example of using stock research."""
    # Load configuration
    config = get_config()
    
    # Create components
    llm_client = create_llm_client(config.llm)
    news_fetcher = NewsFetcher(
        cache_dir=config.news.cache_dir,
        cache_ttl=config.news.cache_ttl,
        max_age_hours=config.news.max_age_hours,
        enabled_sources=config.news.sources
    )
    
    # Create stock researcher
    researcher = StockResearcher(news_fetcher, llm_client)
    
    print("="*80)
    print("STOCK RESEARCH EXAMPLE")
    print("="*80)
    
    # Research a single stock
    print("\n1. Researching RELIANCE...")
    research = researcher.research_stock("RELIANCE", max_articles=15)
    
    if research:
        # Generate and print report
        report = researcher.generate_report(research)
        print(report)
    else:
        print("Failed to generate research for RELIANCE")
    
    # Batch research multiple stocks
    print("\n" + "="*80)
    print("\n2. Batch research for multiple stocks...")
    symbols = ["TCS", "INFY", "HDFCBANK"]
    
    results = researcher.research_batch(symbols, max_articles_per_stock=10)
    
    print(f"\nResearched {len(results)}/{len(symbols)} stocks")
    print("\nSummary:")
    print("-" * 80)
    
    for research in results:
        sentiment_str = research.sentiment.sentiment.value if research.sentiment else "N/A"
        print(f"\n{research.symbol}:")
        print(f"  Opportunity Score: {research.opportunity_score:.2f}")
        print(f"  Sentiment: {sentiment_str}")
        print(f"  News Articles: {len(research.news_articles)}")
        print(f"  Key Catalysts: {len(research.key_catalysts)}")
        print(f"  Risk Factors: {len(research.risk_factors)}")
        print(f"  Recommendation: {research.recommendation[:100]}...")
    
    # Show top opportunities
    print("\n" + "="*80)
    print("\n3. Top opportunities (by score)...")
    
    sorted_results = sorted(results, key=lambda x: x.opportunity_score, reverse=True)
    
    for i, research in enumerate(sorted_results, 1):
        print(f"\n{i}. {research.symbol} - Score: {research.opportunity_score:.2f}")
        print(f"   {research.recommendation}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
