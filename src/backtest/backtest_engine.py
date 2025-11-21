"""
Backtest engine for simulating trading strategies on historical data.
Event-driven architecture to process bars sequentially.
"""

from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict

import pandas as pd
from loguru import logger

from src.data.models import (
    OHLCVBar, Position, Trade, Portfolio, TradeInstruction,
    StrategySignal, MarketRegime, Sentiment
)
from src.core.strategies.base import BaseStrategy
from src.core.risk import RiskManager
from src.core.indicators import calculate_all_indicators


class BacktestEngine:
    """
    Event-driven backtesting engine.
    
    Processes historical bars sequentially, evaluates strategies,
    and simulates trade execution.
    """
    
    def __init__(
        self,
        strategies: List[BaseStrategy],
        risk_manager: RiskManager,
        initial_capital: float,
        interval_minutes: int = 5
    ):
        """
        Initialize backtest engine.
        
        Args:
            strategies: List of strategy instances to evaluate
            risk_manager: Risk manager instance
            initial_capital: Starting capital
            interval_minutes: Bar interval in minutes (for indicator calculation)
        """
        self.strategies = strategies
        self.risk_manager = risk_manager
        self.initial_capital = initial_capital
        self.interval_minutes = interval_minutes
        
        # Portfolio state
        self.portfolio = Portfolio(cash=initial_capital)
        
        # Trade history
        self.trades: List[Trade] = []
        
        # Bar data for each symbol
        self.symbol_data: Dict[str, pd.DataFrame] = {}
        
        # Current regime and sentiment (placeholder for LLM integration)
        self.current_regime: Optional[MarketRegime] = None
        self.current_sentiment: Dict[str, Optional[Sentiment]] = {}
        
        logger.info(f"BacktestEngine initialized with {len(strategies)} strategies")
        logger.info(f"Initial capital: ₹{initial_capital:,.2f}")
    
    def run(
        self,
        historical_data: Dict[str, List[OHLCVBar]],
        regime: Optional[MarketRegime] = None,
        sentiment: Optional[Dict[str, Sentiment]] = None
    ) -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            historical_data: Dictionary mapping symbol to list of OHLCVBar
            regime: Optional market regime classification
            sentiment: Optional sentiment for each symbol
            
        Returns:
            Dictionary with backtest results
        """
        logger.info("=" * 80)
        logger.info("Starting backtest")
        logger.info("=" * 80)
        
        self.current_regime = regime
        self.current_sentiment = sentiment or {}
        
        # Convert bars to DataFrames and calculate indicators
        for symbol, bars in historical_data.items():
            df = self._bars_to_dataframe(bars)
            df = calculate_all_indicators(df, interval_minutes=self.interval_minutes)
            self.symbol_data[symbol] = df
            logger.info(f"Loaded {len(df)} bars for {symbol}")
        
        # Get all unique timestamps across all symbols
        all_timestamps = set()
        for df in self.symbol_data.values():
            all_timestamps.update(df['timestamp'].tolist())
        
        sorted_timestamps = sorted(all_timestamps)
        logger.info(f"Processing {len(sorted_timestamps)} unique timestamps")
        
        # Process each timestamp (bar) sequentially
        for i, timestamp in enumerate(sorted_timestamps):
            self._process_bar(timestamp)
            
            # Log progress periodically
            if (i + 1) % 50 == 0:
                logger.debug(f"Processed {i + 1}/{len(sorted_timestamps)} bars")
        
        # Close any remaining positions at the end
        self._close_all_positions(sorted_timestamps[-1])
        
        logger.info("=" * 80)
        logger.info("Backtest completed")
        logger.info(f"Total trades: {len(self.trades)}")
        logger.info(f"Final portfolio value: ₹{self.portfolio.get_total_value():,.2f}")
        logger.info("=" * 80)
        
        return self._generate_results()
    
    def _bars_to_dataframe(self, bars: List[OHLCVBar]) -> pd.DataFrame:
        """
        Convert list of OHLCVBar to DataFrame.
        
        Args:
            bars: List of OHLCV bars
            
        Returns:
            DataFrame with OHLCV data
        """
        data = []
        for bar in bars:
            data.append({
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('timestamp').reset_index(drop=True)
        return df
    
    def _process_bar(self, timestamp: datetime) -> None:
        """
        Process a single bar across all symbols.
        
        Args:
            timestamp: Current timestamp to process
        """
        # Update positions with current prices
        for symbol, position in list(self.portfolio.positions.items()):
            df = self.symbol_data[symbol]
            current_bar = df[df['timestamp'] == timestamp]
            
            if not current_bar.empty:
                current_price = current_bar.iloc[0]['close']
                position.update_pnl(current_price)
                
                # Check for exit conditions
                self._check_exit_conditions(symbol, position, current_bar.iloc[0], timestamp)
        
        # Update portfolio unrealized P&L
        self.portfolio.update_unrealized_pnl()
        
        # Check if we can take new positions (risk limits)
        if not self.risk_manager.can_trade(self.portfolio):
            return
        
        # Evaluate strategies for each symbol
        for symbol, df in self.symbol_data.items():
            # Skip if already in position
            if symbol in self.portfolio.positions:
                continue
            
            # Get data up to current timestamp
            historical_df = df[df['timestamp'] <= timestamp].copy()
            
            if len(historical_df) < 50:  # Need minimum data for indicators
                continue
            
            # Evaluate each strategy
            for strategy in self.strategies:
                instruction = strategy.evaluate(
                    df=historical_df,
                    current_position=None,
                    regime=self.current_regime,
                    sentiment=self.current_sentiment.get(symbol)
                )
                
                # Process entry signals
                if instruction.signal == StrategySignal.ENTRY_LONG:
                    self._execute_entry(instruction, historical_df.iloc[-1], timestamp)
                    break  # Only one strategy per symbol
    
    def _check_exit_conditions(
        self,
        symbol: str,
        position: Position,
        current_bar: pd.Series,
        timestamp: datetime
    ) -> None:
        """
        Check if position should be exited.
        
        Args:
            symbol: Trading symbol
            position: Current position
            current_bar: Current bar data
            timestamp: Current timestamp
        """
        current_price = current_bar['close']
        exit_reason = None
        
        # Check stop loss
        if position.stop_loss and current_price <= position.stop_loss:
            exit_reason = "stop_loss"
            logger.info(f"Stop loss hit for {symbol} at ₹{current_price:.2f}")
        
        # Check target
        elif position.target and current_price >= position.target:
            exit_reason = "target_hit"
            logger.info(f"Target hit for {symbol} at ₹{current_price:.2f}")
        
        # Check strategy exit signal
        else:
            # Get historical data for strategy evaluation
            df = self.symbol_data[symbol]
            historical_df = df[df['timestamp'] <= timestamp].copy()
            
            # Find the strategy that opened this position
            for strategy in self.strategies:
                if strategy.name == position.strategy_name:
                    instruction = strategy.evaluate(
                        df=historical_df,
                        current_position="long" if position.quantity > 0 else "short",
                        regime=self.current_regime,
                        sentiment=self.current_sentiment.get(symbol)
                    )
                    
                    if instruction.signal == StrategySignal.EXIT_LONG:
                        exit_reason = "strategy_exit"
                        logger.info(f"Strategy exit signal for {symbol}")
                    break
        
        # Execute exit if needed
        if exit_reason:
            self._execute_exit(symbol, current_price, exit_reason, timestamp)
    
    def _execute_entry(
        self,
        instruction: TradeInstruction,
        current_bar: pd.Series,
        timestamp: datetime
    ) -> None:
        """
        Execute entry order.
        
        Args:
            instruction: Trade instruction from strategy
            current_bar: Current bar data
            timestamp: Current timestamp
        """
        symbol = instruction.symbol
        entry_price = current_bar['close']
        
        # Validate with risk manager
        if not self.risk_manager.validate_trade(
            instruction,
            self.portfolio,
            entry_price
        ):
            logger.debug(f"Trade rejected by risk manager for {symbol}")
            return
        
        # Create position
        position = Position(
            symbol=symbol,
            quantity=instruction.quantity,
            average_price=entry_price,
            current_price=entry_price,
            stop_loss=instruction.stop_loss,
            target=instruction.target,
            entry_time=timestamp,
            strategy_name=instruction.strategy_name,
            unrealized_pnl=0.0
        )
        
        # Update portfolio
        cost = entry_price * instruction.quantity
        self.portfolio.cash -= cost
        self.portfolio.add_position(position)
        
        logger.info(
            f"ENTRY: {symbol} | Qty: {instruction.quantity} | "
            f"Price: ₹{entry_price:.2f} | SL: ₹{instruction.stop_loss:.2f} | "
            f"Target: ₹{instruction.target:.2f} | Strategy: {instruction.strategy_name}"
        )
        logger.info(f"Reason: {instruction.reason}")
    
    def _execute_exit(
        self,
        symbol: str,
        exit_price: float,
        exit_reason: str,
        timestamp: datetime
    ) -> None:
        """
        Execute exit order.
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price
            exit_reason: Reason for exit
            timestamp: Current timestamp
        """
        trade = self.portfolio.close_position(symbol, exit_price)
        
        if trade:
            trade.exit_reason = exit_reason
            trade.exit_time = timestamp
            trade.regime = self.current_regime
            trade.sentiment = self.current_sentiment.get(symbol)
            
            self.trades.append(trade)
            
            logger.info(
                f"EXIT: {symbol} | Price: ₹{exit_price:.2f} | "
                f"P&L: ₹{trade.pnl:,.2f} ({trade.pnl_percent:.2f}%) | "
                f"Reason: {exit_reason}"
            )
    
    def _close_all_positions(self, timestamp: datetime) -> None:
        """
        Close all remaining positions at end of backtest.
        
        Args:
            timestamp: Final timestamp
        """
        for symbol, position in list(self.portfolio.positions.items()):
            df = self.symbol_data[symbol]
            final_bar = df[df['timestamp'] == timestamp]
            
            if not final_bar.empty:
                final_price = final_bar.iloc[0]['close']
                self._execute_exit(symbol, final_price, "end_of_backtest", timestamp)
    
    def _generate_results(self) -> Dict:
        """
        Generate backtest results summary.
        
        Returns:
            Dictionary with results
        """
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.portfolio.get_total_value(),
            'total_pnl': self.portfolio.realized_pnl,
            'total_trades': len(self.trades),
            'winning_trades': self.portfolio.winning_trades,
            'losing_trades': self.portfolio.losing_trades,
            'trades': self.trades,
            'portfolio': self.portfolio
        }
