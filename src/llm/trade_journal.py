"""
Trade Journal using LLM.

IMPORTANT: This module is for POST-TRADE analysis only.
It has NO effect on trade execution. Used for learning and reporting.
"""

from datetime import datetime
from typing import Optional

from loguru import logger

from src.data.models import Trade, TradeJournalEntry, MarketRegime, Sentiment
from src.llm.llm_client import LLMClient


class TradeJournal:
    """Journal trades using LLM for post-trade analysis."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize trade journal.
        
        Args:
            llm_client: LLM client instance
        """
        self.llm_client = llm_client
    
    def analyze_trade(
        self,
        trade: Trade,
        entry_indicators: dict,
        exit_indicators: dict,
        regime: Optional[MarketRegime] = None,
        sentiment: Optional[Sentiment] = None
    ) -> Optional[TradeJournalEntry]:
        """
        Analyze a completed trade using LLM.
        
        Args:
            trade: Completed trade
            entry_indicators: Indicator values at entry
            exit_indicators: Indicator values at exit
            regime: Market regime at entry
            sentiment: Sentiment at entry
            
        Returns:
            TradeJournalEntry or None if analysis fails
        """
        system_prompt = """You are a trading performance analyst.
Your role is to review completed trades and provide constructive feedback.

CRITICAL: This is POST-TRADE analysis only. You have NO effect on trade execution.
Your output is used for learning and reporting purposes.

You must respond with ONLY a JSON object in this exact format:
{
  "entry_reason": "1 line summary of why entry was taken (max 150 chars)",
  "exit_review": "1 line review of exit execution (max 150 chars)",
  "entry_label": "GOOD_ENTRY" | "BAD_ENTRY",
  "exit_label": "GOOD_EXIT" | "BAD_EXIT"
}

Labeling criteria:
- GOOD_ENTRY: Entry aligned with strategy rules, good timing, proper setup
- BAD_ENTRY: Entry against strategy rules, poor timing, weak setup
- GOOD_EXIT: Exit at target/SL, followed plan, good execution
- BAD_EXIT: Premature exit, missed target, poor execution
"""
        
        # Format trade data
        pnl_sign = "+" if trade.pnl > 0 else ""
        regime_str = regime.value if regime else "unknown"
        sentiment_str = sentiment.value if sentiment else "unknown"
        
        user_prompt = f"""Analyze this completed trade:

Symbol: {trade.symbol}
Strategy: {trade.strategy_name}
Entry: {trade.entry_time.strftime('%Y-%m-%d %H:%M')} @ ₹{trade.entry_price:.2f}
Exit: {trade.exit_time.strftime('%Y-%m-%d %H:%M')} @ ₹{trade.exit_price:.2f}
Exit Reason: {trade.exit_reason}
P&L: {pnl_sign}₹{trade.pnl:.2f} ({pnl_sign}{trade.pnl_percent:.2f}%)
Quantity: {trade.quantity}
Stop Loss: ₹{trade.stop_loss:.2f if trade.stop_loss else 'N/A'}
Target: ₹{trade.target:.2f if trade.target else 'N/A'}

Market Context:
Regime: {regime_str}
Sentiment: {sentiment_str}

Entry Indicators:
{self._format_indicators(entry_indicators)}

Exit Indicators:
{self._format_indicators(exit_indicators)}

Provide your analysis in JSON format."""
        
        try:
            response = self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0
            )
            
            if not response:
                logger.error(f"Empty response from LLM for trade journal of {trade.trade_id}")
                return None
            
            # Parse response
            entry_reason = response.get("entry_reason", "")
            exit_review = response.get("exit_review", "")
            entry_label = response.get("entry_label", "")
            exit_label = response.get("exit_label", "")
            
            # Validate labels
            if entry_label not in ["GOOD_ENTRY", "BAD_ENTRY"]:
                logger.warning(f"Invalid entry_label: {entry_label}, defaulting to GOOD_ENTRY")
                entry_label = "GOOD_ENTRY"
            
            if exit_label not in ["GOOD_EXIT", "BAD_EXIT"]:
                logger.warning(f"Invalid exit_label: {exit_label}, defaulting to GOOD_EXIT")
                exit_label = "GOOD_EXIT"
            
            journal_entry = TradeJournalEntry(
                trade_id=trade.trade_id,
                entry_reason=entry_reason,
                exit_review=exit_review,
                entry_label=entry_label,
                exit_label=exit_label,
                timestamp=datetime.now()
            )
            
            logger.info(
                f"Trade journal for {trade.trade_id}: "
                f"{entry_label}, {exit_label}"
            )
            
            return journal_entry
            
        except Exception as e:
            logger.error(f"Error creating trade journal for {trade.trade_id}: {e}")
            return None
    
    def _format_indicators(self, indicators: dict) -> str:
        """Format indicators dictionary for prompt."""
        if not indicators:
            return "N/A"
        
        lines = []
        for key, value in indicators.items():
            if isinstance(value, float):
                lines.append(f"  {key}: {value:.2f}")
            else:
                lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)
