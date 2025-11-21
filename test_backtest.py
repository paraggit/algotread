"""
Test script to demonstrate backtest functionality with mock data.
This bypasses the Kite API requirement for testing purposes.
"""

from datetime import datetime, timedelta
import random

from src.data.models import OHLCVBar
from src.config import get_config
from src.backtest.backtest_engine import BacktestEngine
from src.backtest.performance import PerformanceMetrics
from src.backtest.report import BacktestReport
from src.core.risk import RiskManager
from src.core.strategies.orb_supertrend import ORBSupertrendStrategy
from src.core.strategies.ema_trend import EMATrendStrategy


def generate_mock_data(symbol: str, start_date: datetime, num_bars: int = 100) -> list[OHLCVBar]:
    """Generate mock OHLCV data for testing."""
    bars = []
    base_price = 2500.0  # Starting price for RELIANCE
    current_time = start_date
    
    for i in range(num_bars):
        # Simulate price movement
        change = random.uniform(-20, 20)
        open_price = base_price
        high_price = base_price + abs(change) + random.uniform(0, 10)
        low_price = base_price - abs(change) - random.uniform(0, 10)
        close_price = base_price + change
        volume = random.randint(100000, 500000)
        
        bar = OHLCVBar(
            timestamp=current_time,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            symbol=symbol
        )
        bars.append(bar)
        
        base_price = close_price
        current_time += timedelta(minutes=5)
    
    return bars


def main():
    """Run backtest with mock data."""
    print("=" * 80)
    print("BACKTEST TEST WITH MOCK DATA")
    print("=" * 80)
    
    # Load config
    config = get_config()
    
    # Generate mock data
    start_date = datetime(2024, 1, 15, 9, 15)  # Market open time
    mock_data = {
        'RELIANCE': generate_mock_data('RELIANCE', start_date, num_bars=75)  # Full trading day
    }
    
    print(f"\nGenerated {len(mock_data['RELIANCE'])} bars of mock data for RELIANCE")
    
    # Create strategies
    strategies = [
        ORBSupertrendStrategy(
            orb_period_minutes=15,
            interval_minutes=5,
            volume_multiplier=1.5,
            rsi_threshold=55.0,
            supertrend_period=7,
            supertrend_multiplier=3.0,
            atr_sl_multiplier=2.0,
            reward_ratio=1.5,
            max_risk_pct=0.02
        ),
        EMATrendStrategy(
            ema_fast=9,
            ema_slow=21,
            use_vwap_filter=True,
            use_rsi_filter=False,
            atr_sl_multiplier=2.0,
            reward_ratio=1.5,
            max_risk_pct=0.02,
            allow_short=False
        )
    ]
    
    # Create risk manager
    risk_manager = RiskManager(config.risk, config.initial_capital)
    
    # Create backtest engine
    engine = BacktestEngine(
        strategies=strategies,
        risk_manager=risk_manager,
        initial_capital=config.initial_capital,
        interval_minutes=5
    )
    
    # Run backtest
    print("\nRunning backtest...")
    results = engine.run(mock_data)
    
    # Calculate performance metrics
    metrics = PerformanceMetrics(
        initial_capital=results['initial_capital'],
        final_capital=results['final_capital'],
        trades=results['trades'],
        portfolio=results['portfolio']
    )
    
    # Generate report
    report = BacktestReport(results, metrics)
    
    # Print summary
    report.print_summary()
    
    # Print trade breakdown
    if results['trades']:
        report.print_trade_breakdown(max_trades=10)
    else:
        print("\nNo trades were executed during the backtest.")
        print("This could be due to:")
        print("  - No strategy signals generated")
        print("  - Risk limits preventing trades")
        print("  - Insufficient data for indicator calculation")
    
    # Save results
    json_path = report.save_to_json()
    if results['trades']:
        csv_path = report.save_trades_to_csv()
        print(f"\nTrades saved to: {csv_path}")
    
    print(f"Results saved to: {json_path}")
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()
