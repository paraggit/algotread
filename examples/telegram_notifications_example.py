"""Example usage of Telegram notifications."""

from datetime import datetime
from src.config import get_config
from src.notifications.telegram_notifier import create_telegram_notifier
from src.data.models import Trade, Portfolio, TradeJournalEntry


def main():
    """Example of using Telegram notifications."""
    # Create notifier
    # In real usage, get these from config
    bot_token = "YOUR_BOT_TOKEN"  # Get from @BotFather
    chat_id = "YOUR_CHAT_ID"  # Your chat/channel ID
    
    notifier = create_telegram_notifier(bot_token, chat_id)
    
    if not notifier:
        print("Failed to create Telegram notifier")
        return
    
    # 1. System start notification
    notifier.notify_system_start(
        mode="paper",
        watchlist=["RELIANCE", "TCS", "INFY"]
    )
    
    # 2. Trade entry notification
    notifier.notify_trade_entry(
        symbol="RELIANCE",
        strategy="orb_supertrend",
        quantity=50,
        entry_price=2450.00,
        stop_loss=2430.00,
        target=2480.00,
        reason="ORB breakout with bullish Supertrend, volume 2.1x average"
    )
    
    # 3. Trade exit notification
    trade = Trade(
        trade_id="RELIANCE_1234567890",
        symbol="RELIANCE",
        strategy_name="orb_supertrend",
        entry_time=datetime(2024, 1, 15, 10, 30),
        exit_time=datetime(2024, 1, 15, 14, 15),
        entry_price=2450.00,
        exit_price=2475.00,
        quantity=50,
        pnl=1250.00,
        pnl_percent=1.02,
        stop_loss=2430.00,
        target=2480.00,
        exit_reason="target_hit"
    )
    
    journal_entry = TradeJournalEntry(
        trade_id="RELIANCE_1234567890",
        entry_reason="Strong ORB breakout with good volume confirmation",
        exit_review="Target hit as planned, good execution",
        entry_label="GOOD_ENTRY",
        exit_label="GOOD_EXIT",
        timestamp=datetime.now()
    )
    
    notifier.notify_trade_exit(
        trade=trade,
        current_price=2476.00,
        journal_entry=journal_entry
    )
    
    # 4. Risk alert notification
    portfolio = Portfolio(
        cash=95000.00,
        daily_pnl=-2500.00,
        daily_trades=5,
        daily_losing_trades=3
    )
    
    notifier.notify_risk_alert(
        alert_type="daily_loss",
        message="Daily loss limit approaching: -2.5%",
        portfolio=portfolio
    )
    
    # 5. End-of-day summary
    trades = [
        Trade(
            trade_id="1",
            symbol="RELIANCE",
            strategy_name="orb_supertrend",
            entry_time=datetime(2024, 1, 15, 10, 30),
            exit_time=datetime(2024, 1, 15, 14, 15),
            entry_price=2450.00,
            exit_price=2475.00,
            quantity=50,
            pnl=1250.00,
            pnl_percent=1.02,
            exit_reason="target_hit"
        ),
        Trade(
            trade_id="2",
            symbol="TCS",
            strategy_name="ema_trend",
            entry_time=datetime(2024, 1, 15, 11, 00),
            exit_time=datetime(2024, 1, 15, 13, 30),
            entry_price=3500.00,
            exit_price=3480.00,
            quantity=30,
            pnl=-600.00,
            pnl_percent=-0.57,
            exit_reason="stop_loss"
        ),
    ]
    
    final_portfolio = Portfolio(
        cash=100650.00,
        realized_pnl=650.00,
        total_trades=2,
        winning_trades=1,
        losing_trades=1,
        daily_pnl=650.00,
        daily_trades=2,
        daily_losing_trades=1
    )
    
    notifier.notify_daily_summary(
        portfolio=final_portfolio,
        trades=trades,
        journal_entries=[journal_entry],
        market_summary="Nifty up 0.5%, IT sector strong"
    )
    
    # 6. System stop notification
    notifier.notify_system_stop(reason="Market closed")
    
    print("\n✅ All notifications sent successfully!")
    print("Check your Telegram chat/channel for messages")


if __name__ == "__main__":
    main()
