# Telegram Notifications Setup Guide

## Overview

Get real-time trade notifications and end-of-day summaries sent directly to your Telegram chat or channel.

## Features

- 🟢 **Trade Entry Alerts**: Instant notification when a trade is opened
- 🔴 **Trade Exit Alerts**: Notification when a trade is closed with P&L
- 🚨 **Risk Alerts**: Warnings when risk limits are approached
- 📊 **Daily Summary**: Comprehensive end-of-day trading report
- 🤖 **AI Insights**: LLM trade journal reviews included in notifications

## Setup Instructions

### Step 1: Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Copy the **bot token** (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Your Chat ID

**Option A: Personal Chat**
1. Search for `@userinfobot` on Telegram
2. Start a chat with it
3. It will send you your **chat ID** (a number)

**Option B: Channel**
1. Create a channel (or use existing)
2. Add your bot as an administrator
3. Send a message to the channel
4. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
5. Look for `"chat":{"id":-1001234567890}` in the response
6. Copy the chat ID (including the minus sign)

### Step 3: Configure Environment

Add to your `.env` file:

```bash
# Telegram Notifications
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789  # or -1001234567890 for channels
TELEGRAM_NOTIFY_TRADES=true
TELEGRAM_NOTIFY_RISK_ALERTS=true
TELEGRAM_DAILY_SUMMARY=true
```

### Step 4: Test Notifications

Run the example:

```bash
uv run examples/telegram_notifications_example.py
```

You should receive test messages in your Telegram chat!

## Notification Types

### 1. Trade Entry 🟢

```
🟢 TRADE ENTRY

📊 RELIANCE
Strategy: orb_supertrend
Quantity: 50 shares
Entry: ₹2450.00

🎯 Targets:
Stop Loss: ₹2430.00 (-0.82%)
Target: ₹2480.00 (+1.22%)
R:R Ratio: 1:1.50

💡 Reason: ORB breakout with bullish Supertrend

⏰ 10:35:42 IST
```

### 2. Trade Exit 🔴/🟢

```
🟢 TRADE EXIT

📊 RELIANCE
Strategy: orb_supertrend
Quantity: 50 shares

💰 P&L: +₹1250.00 (+1.02%)

📈 Prices:
Entry: ₹2450.00
Exit: ₹2475.00
Current: ₹2476.00

🎯 Exit: Target Hit

⏰ Duration: 10:30 → 14:15

🤖 AI Review:
Entry: Good Entry
Exit: Good Exit
💭 Target hit as planned, good execution
```

### 3. Risk Alert 🚨

```
⚠️ RISK ALERT

Type: Daily Loss
Daily loss limit approaching: -2.5%

📊 Portfolio Status:
Daily P&L: ₹-2500.00
Daily Trades: 5
Losing Trades: 3

⏰ 14:30:15 IST
```

### 4. Daily Summary 📊

```
📊 DAILY TRADING SUMMARY
15 January 2024

🟢 P&L: ₹+650.00

📈 Trade Statistics:
Total Trades: 2
Winners: 1 (50.0%)
Losers: 1

💰 Performance:
Avg Win: ₹+1250.00
Avg Loss: ₹-600.00
Largest Win: ₹+1250.00
Largest Loss: ₹-600.00

📊 Portfolio:
Total P&L: ₹+650.00
Total Trades: 2
Overall Win Rate: 50.0%

🌐 Market: Nifty up 0.5%, IT sector strong

Top Trades:
🥇 RELIANCE: ₹+1250.00 (+1.02%)
🥈 TCS: ₹-600.00 (-0.57%)

🤖 AI Analysis:
Good Entries: 1/2
Good Exits: 1/2

⏰ Report generated at 15:30:00 IST
```

## Integration with Trading System

In your `main.py`, integrate like this:

```python
from src.notifications.telegram_notifier import create_telegram_notifier

# Initialize
notifier = create_telegram_notifier(
    bot_token=config.telegram_bot_token,
    chat_id=config.telegram_chat_id
)

# System start
if notifier:
    notifier.notify_system_start(config.mode, config.watchlist)

# On trade entry
if instruction.signal == StrategySignal.ENTRY_LONG:
    if notifier and config.telegram_notify_trades:
        notifier.notify_trade_entry(
            symbol=instruction.symbol,
            strategy=instruction.strategy_name,
            quantity=instruction.quantity,
            entry_price=instruction.entry_price,
            stop_loss=instruction.stop_loss,
            target=instruction.target,
            reason=instruction.reason
        )

# On trade exit
if trade:
    if notifier and config.telegram_notify_trades:
        notifier.notify_trade_exit(
            trade=trade,
            current_price=current_price,
            journal_entry=journal_entry  # Optional
        )

# On risk alert
if risk_manager.kill_switch_active:
    if notifier and config.telegram_notify_risk_alerts:
        notifier.notify_risk_alert(
            alert_type="kill_switch",
            message=risk_manager.kill_switch_reason,
            portfolio=portfolio
        )

# End of day (e.g., at 15:30 IST)
if is_market_closed():
    if notifier and config.telegram_daily_summary:
        notifier.notify_daily_summary(
            portfolio=portfolio,
            trades=today_trades,
            journal_entries=today_journals,
            market_summary=market_summary
        )
```

## Tips

1. **Channel vs Personal Chat**: Use a channel for cleaner organization
2. **Mute Notifications**: Mute the channel during trading hours if too noisy
3. **Archive Messages**: Telegram keeps all messages, great for review
4. **Multiple Bots**: Create separate bots for different strategies/accounts
5. **Privacy**: Never share your bot token or chat ID

## Troubleshooting

**Bot not sending messages:**
- Check bot token is correct
- Ensure you've started a chat with the bot (send `/start`)
- For channels, ensure bot is added as admin

**Wrong chat ID:**
- Use `@userinfobot` to verify your chat ID
- For channels, use the API method described above

**Messages not formatted:**
- Ensure `parse_mode="HTML"` is set
- Check HTML tags are properly closed

## Security

- ✅ Bot token is stored in `.env` (gitignored)
- ✅ Never commit credentials to git
- ✅ Use environment variables only
- ✅ Revoke bot token if compromised (via @BotFather)

## Example Output

Check the `examples/telegram_notifications_example.py` file for a complete working example with all notification types.

---

**Note**: Telegram notifications are optional. The system works perfectly fine without them, but they provide excellent real-time monitoring and end-of-day reporting.
