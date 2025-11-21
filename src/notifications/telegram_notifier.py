"""
Telegram Notifier for Trade Updates and Daily Summaries.

Sends real-time trade notifications and end-of-day reports to Telegram channel.
"""

import asyncio
from datetime import datetime
from typing import List, Optional

from loguru import logger
from telegram import Bot
from telegram.error import TelegramError

from src.data.models import Trade, Portfolio, TradeJournalEntry


class TelegramNotifier:
    """Send trading notifications to Telegram."""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Telegram chat/channel ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token)
        logger.info(f"Telegram notifier initialized for chat {chat_id}")
    
    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message to Telegram.
        
        Args:
            message: Message text (supports HTML formatting)
            parse_mode: Parse mode (HTML or Markdown)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.debug(f"Telegram message sent successfully")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def send_message_sync(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Synchronous wrapper for send_message.
        
        Args:
            message: Message text
            parse_mode: Parse mode
            
        Returns:
            True if sent successfully
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create a task
                asyncio.create_task(self.send_message(message, parse_mode))
                return True
            else:
                # If no loop is running, run it
                return loop.run_until_complete(self.send_message(message, parse_mode))
        except Exception as e:
            logger.error(f"Error in sync send: {e}")
            return False
    
    def notify_trade_entry(
        self,
        symbol: str,
        strategy: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target: float,
        reason: str
    ) -> bool:
        """
        Send trade entry notification.
        
        Args:
            symbol: Stock symbol
            strategy: Strategy name
            quantity: Number of shares
            entry_price: Entry price
            stop_loss: Stop loss price
            target: Target price
            reason: Entry reason
            
        Returns:
            True if sent successfully
        """
        risk = abs(entry_price - stop_loss) * quantity
        reward = abs(target - entry_price) * quantity
        rr_ratio = reward / risk if risk > 0 else 0
        
        message = f"""
🟢 <b>TRADE ENTRY</b>

📊 <b>{symbol}</b>
Strategy: {strategy}
Quantity: {quantity} shares
Entry: ₹{entry_price:.2f}

🎯 Targets:
Stop Loss: ₹{stop_loss:.2f} ({((stop_loss - entry_price) / entry_price * 100):+.2f}%)
Target: ₹{target:.2f} ({((target - entry_price) / entry_price * 100):+.2f}%)
R:R Ratio: 1:{rr_ratio:.2f}

💡 Reason: {reason}

⏰ {datetime.now().strftime('%H:%M:%S IST')}
"""
        return self.send_message_sync(message.strip())
    
    def notify_trade_exit(
        self,
        trade: Trade,
        current_price: float,
        journal_entry: Optional[TradeJournalEntry] = None
    ) -> bool:
        """
        Send trade exit notification.
        
        Args:
            trade: Completed trade
            current_price: Current market price
            journal_entry: Optional journal entry from LLM
            
        Returns:
            True if sent successfully
        """
        pnl_emoji = "🟢" if trade.pnl > 0 else "🔴"
        pnl_sign = "+" if trade.pnl > 0 else ""
        
        # Determine exit reason emoji
        exit_emoji = {
            "target_hit": "🎯",
            "stop_loss": "🛑",
            "time_exit": "⏰",
            "manual": "👤",
            "strategy_exit": "📊"
        }.get(trade.exit_reason, "📤")
        
        message = f"""
{pnl_emoji} <b>TRADE EXIT</b>

📊 <b>{trade.symbol}</b>
Strategy: {trade.strategy_name}
Quantity: {trade.quantity} shares

💰 P&L: {pnl_sign}₹{trade.pnl:.2f} ({pnl_sign}{trade.pnl_percent:.2f}%)

📈 Prices:
Entry: ₹{trade.entry_price:.2f}
Exit: ₹{trade.exit_price:.2f}
Current: ₹{current_price:.2f}

{exit_emoji} Exit: {trade.exit_reason.replace('_', ' ').title()}

⏰ Duration: {trade.entry_time.strftime('%H:%M')} → {trade.exit_time.strftime('%H:%M')}
"""
        
        # Add LLM journal review if available
        if journal_entry:
            message += f"\n🤖 <b>AI Review:</b>\n"
            message += f"Entry: {journal_entry.entry_label.replace('_', ' ').title()}\n"
            message += f"Exit: {journal_entry.exit_label.replace('_', ' ').title()}\n"
            message += f"💭 {journal_entry.exit_review}"
        
        return self.send_message_sync(message.strip())
    
    def notify_risk_alert(
        self,
        alert_type: str,
        message: str,
        portfolio: Optional[Portfolio] = None
    ) -> bool:
        """
        Send risk management alert.
        
        Args:
            alert_type: Type of alert (kill_switch, daily_loss, etc.)
            message: Alert message
            portfolio: Optional portfolio state
            
        Returns:
            True if sent successfully
        """
        emoji = {
            "kill_switch": "🚨",
            "daily_loss": "⚠️",
            "max_trades": "⛔",
            "time_filter": "⏰"
        }.get(alert_type, "⚠️")
        
        alert_msg = f"""
{emoji} <b>RISK ALERT</b>

Type: {alert_type.replace('_', ' ').title()}
{message}
"""
        
        if portfolio:
            alert_msg += f"""
📊 Portfolio Status:
Daily P&L: ₹{portfolio.daily_pnl:+.2f}
Daily Trades: {portfolio.daily_trades}
Losing Trades: {portfolio.daily_losing_trades}
"""
        
        alert_msg += f"\n⏰ {datetime.now().strftime('%H:%M:%S IST')}"
        
        return self.send_message_sync(alert_msg.strip())
    
    def notify_daily_summary(
        self,
        portfolio: Portfolio,
        trades: List[Trade],
        journal_entries: Optional[List[TradeJournalEntry]] = None,
        market_summary: Optional[str] = None
    ) -> bool:
        """
        Send end-of-day trading summary.
        
        Args:
            portfolio: Final portfolio state
            trades: List of all trades for the day
            journal_entries: Optional LLM journal entries
            market_summary: Optional market summary
            
        Returns:
            True if sent successfully
        """
        # Calculate statistics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl <= 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = sum(t.pnl for t in trades)
        avg_win = sum(t.pnl for t in trades if t.pnl > 0) / winning_trades if winning_trades > 0 else 0
        avg_loss = sum(t.pnl for t in trades if t.pnl <= 0) / losing_trades if losing_trades > 0 else 0
        
        largest_win = max((t.pnl for t in trades), default=0)
        largest_loss = min((t.pnl for t in trades), default=0)
        
        pnl_emoji = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"
        
        message = f"""
📊 <b>DAILY TRADING SUMMARY</b>
{datetime.now().strftime('%d %B %Y')}

{pnl_emoji} <b>P&L: ₹{total_pnl:+.2f}</b>

📈 <b>Trade Statistics:</b>
Total Trades: {total_trades}
Winners: {winning_trades} ({win_rate:.1f}%)
Losers: {losing_trades}

💰 <b>Performance:</b>
Avg Win: ₹{avg_win:+.2f}
Avg Loss: ₹{avg_loss:+.2f}
Largest Win: ₹{largest_win:+.2f}
Largest Loss: ₹{largest_loss:+.2f}

📊 <b>Portfolio:</b>
Total P&L: ₹{portfolio.realized_pnl:+.2f}
Total Trades: {portfolio.total_trades}
Overall Win Rate: {(portfolio.winning_trades / portfolio.total_trades * 100) if portfolio.total_trades > 0 else 0:.1f}%
"""
        
        # Add market summary if available
        if market_summary:
            message += f"\n🌐 <b>Market:</b> {market_summary}\n"
        
        # Add top trades
        if trades:
            message += "\n<b>Top Trades:</b>\n"
            sorted_trades = sorted(trades, key=lambda t: t.pnl, reverse=True)[:3]
            for i, trade in enumerate(sorted_trades, 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                message += f"{emoji} {trade.symbol}: ₹{trade.pnl:+.2f} ({trade.pnl_percent:+.2f}%)\n"
        
        # Add LLM insights if available
        if journal_entries:
            good_entries = len([j for j in journal_entries if j.entry_label == "GOOD_ENTRY"])
            good_exits = len([j for j in journal_entries if j.exit_label == "GOOD_EXIT"])
            message += f"\n🤖 <b>AI Analysis:</b>\n"
            message += f"Good Entries: {good_entries}/{len(journal_entries)}\n"
            message += f"Good Exits: {good_exits}/{len(journal_entries)}\n"
        
        message += f"\n⏰ Report generated at {datetime.now().strftime('%H:%M:%S IST')}"
        
        return self.send_message_sync(message.strip())
    
    def notify_system_start(self, mode: str, watchlist: List[str]) -> bool:
        """
        Send system startup notification.
        
        Args:
            mode: Trading mode (backtest/paper/live)
            watchlist: List of symbols being traded
            
        Returns:
            True if sent successfully
        """
        mode_emoji = {
            "backtest": "📚",
            "paper": "📝",
            "live": "🔴"
        }.get(mode, "🤖")
        
        message = f"""
{mode_emoji} <b>SYSTEM STARTED</b>

Mode: {mode.upper()}
Watchlist: {', '.join(watchlist)}

⏰ {datetime.now().strftime('%d %B %Y, %H:%M:%S IST')}

Ready to trade! 🚀
"""
        return self.send_message_sync(message.strip())
    
    def notify_system_stop(self, reason: str = "Normal shutdown") -> bool:
        """
        Send system shutdown notification.
        
        Args:
            reason: Shutdown reason
            
        Returns:
            True if sent successfully
        """
        message = f"""
🛑 <b>SYSTEM STOPPED</b>

Reason: {reason}

⏰ {datetime.now().strftime('%d %B %Y, %H:%M:%S IST')}
"""
        return self.send_message_sync(message.strip())


def create_telegram_notifier(bot_token: str, chat_id: str) -> Optional[TelegramNotifier]:
    """
    Factory function to create Telegram notifier.
    
    Args:
        bot_token: Telegram bot token
        chat_id: Telegram chat ID
        
    Returns:
        TelegramNotifier instance or None if credentials missing
    """
    if not bot_token or not chat_id:
        logger.warning("Telegram credentials not provided, notifications disabled")
        return None
    
    try:
        return TelegramNotifier(bot_token, chat_id)
    except Exception as e:
        logger.error(f"Failed to create Telegram notifier: {e}")
        return None
