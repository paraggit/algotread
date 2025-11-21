"""
Test script for paper trading with mock WebSocket data.
This simulates live market data without requiring actual WebSocket connection.
"""

from datetime import datetime, timedelta
import random
import time

from src.data.models import OHLCVBar
from src.config import get_config
from src.paper.paper_engine import PaperTradingEngine
from src.core.risk import RiskManager
from src.core.strategies.orb_supertrend import ORBSupertrendStrategy
from src.core.strategies.ema_trend import EMATrendStrategy


def generate_realistic_bars(symbol: str, num_bars: int = 100) -> list[OHLCVBar]:
    """Generate realistic OHLCV bars with trends."""
    bars = []
    base_price = 2500.0
    current_time = datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
    
    # Create a trending market
    trend_direction = 1  # 1 for up, -1 for down
    
    for i in range(num_bars):
        # Add some trend
        trend = trend_direction * random.uniform(0, 5)
        noise = random.uniform(-10, 10)
        
        open_price = base_price
        close_price = base_price + trend + noise
        high_price = max(open_price, close_price) + random.uniform(0, 8)
        low_price = min(open_price, close_price) - random.uniform(0, 8)
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
        
        # Occasionally reverse trend
        if i % 20 == 0 and i > 0:
            trend_direction *= -1
    
    return bars


def main():
    """Run paper trading test with mock data."""
    print("=" * 80)
    print("PAPER TRADING TEST WITH MOCK DATA")
    print("=" * 80)
    
    # Load config
    config = get_config()
    
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
    
    # Create paper trading engine
    engine = PaperTradingEngine(
        strategies=strategies,
        risk_manager=risk_manager,
        initial_capital=config.initial_capital,
        interval_minutes=5
    )
    
    # Generate mock bars
    print("\nGenerating mock market data...")
    bars = generate_realistic_bars('RELIANCE', num_bars=100)
    print(f"Generated {len(bars)} bars")
    
    # Simulate live trading by feeding bars one at a time
    print("\nStarting paper trading simulation...")
    print("Press Ctrl+C to stop\n")
    
    try:
        for i, bar in enumerate(bars):
            # Feed bar to engine
            engine.on_bar(bar)
            
            # Print status every 10 bars
            if (i + 1) % 10 == 0:
                status = engine.get_status()
                print(
                    f"Bar {i+1}/{len(bars)} | "
                    f"Portfolio: ₹{status['portfolio_value']:,.2f} | "
                    f"P&L: ₹{status['daily_pnl']:,.2f} | "
                    f"Trades: {status['total_trades']} | "
                    f"Positions: {status['open_positions']}"
                )
            
            # Simulate real-time delay
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\nStopping simulation...")
    
    # Print final summary
    print("\n" + "=" * 80)
    print("PAPER TRADING SESSION SUMMARY")
    print("=" * 80)
    
    status = engine.get_status()
    print(f"\nFinal Portfolio Value: ₹{status['portfolio_value']:,.2f}")
    print(f"Total P&L: ₹{status['daily_pnl']:,.2f}")
    print(f"Total Return: {((status['portfolio_value'] / config.initial_capital) - 1) * 100:.2f}%")
    print(f"\nTotal Trades: {status['total_trades']}")
    print(f"Winning Trades: {status['winning_trades']}")
    print(f"Losing Trades: {status['losing_trades']}")
    
    if status['total_trades'] > 0:
        win_rate = (status['winning_trades'] / status['total_trades']) * 100
        print(f"Win Rate: {win_rate:.2f}%")
    
    # Print trade details
    if engine.get_trades():
        print("\n" + "=" * 80)
        print("TRADE DETAILS")
        print("=" * 80)
        
        for i, trade in enumerate(engine.get_trades(), 1):
            print(f"\nTrade #{i}:")
            print(f"  Symbol: {trade.symbol}")
            print(f"  Strategy: {trade.strategy_name}")
            print(f"  Entry: ₹{trade.entry_price:.2f} at {trade.entry_time.strftime('%H:%M:%S')}")
            print(f"  Exit: ₹{trade.exit_price:.2f} at {trade.exit_time.strftime('%H:%M:%S')}")
            print(f"  Quantity: {trade.quantity}")
            print(f"  P&L: ₹{trade.pnl:,.2f} ({trade.pnl_percent:.2f}%)")
            print(f"  Exit Reason: {trade.exit_reason}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()
