"""
Backtest report generator.
Creates formatted reports from backtest results.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from loguru import logger

from src.backtest.performance import PerformanceMetrics


class BacktestReport:
    """Generate and save backtest reports."""
    
    def __init__(self, results: Dict, metrics: PerformanceMetrics):
        """
        Initialize report generator.
        
        Args:
            results: Backtest results dictionary
            metrics: Performance metrics instance
        """
        self.results = results
        self.metrics = metrics
    
    def print_summary(self) -> None:
        """Print backtest summary to console."""
        all_metrics = self.metrics.calculate_all_metrics()
        
        print("\n" + "=" * 80)
        print("BACKTEST SUMMARY")
        print("=" * 80)
        
        # Capital and Returns
        returns = all_metrics['returns']
        print(f"\nCapital:")
        print(f"  Initial Capital:     ₹{returns['initial_capital']:>15,.2f}")
        print(f"  Final Capital:       ₹{returns['final_capital']:>15,.2f}")
        print(f"  Total Return:        ₹{returns['total_return']:>15,.2f}")
        print(f"  Total Return %:       {returns['total_return_pct']:>15.2f}%")
        
        # Trade Statistics
        trade_stats = all_metrics['trade_stats']
        print(f"\nTrade Statistics:")
        print(f"  Total Trades:        {trade_stats['total_trades']:>16}")
        print(f"  Winning Trades:      {trade_stats['winning_trades']:>16}")
        print(f"  Losing Trades:       {trade_stats['losing_trades']:>16}")
        print(f"  Win Rate:            {trade_stats['win_rate']:>15.2f}%")
        print(f"  Average Win:         ₹{trade_stats['avg_win']:>15,.2f}")
        print(f"  Average Loss:        ₹{trade_stats['avg_loss']:>15,.2f}")
        print(f"  Largest Win:         ₹{trade_stats['largest_win']:>15,.2f}")
        print(f"  Largest Loss:        ₹{trade_stats['largest_loss']:>15,.2f}")
        print(f"  Profit Factor:        {trade_stats['profit_factor']:>15.2f}")
        print(f"  Avg Trade P&L:       ₹{trade_stats['avg_trade_pnl']:>15,.2f}")
        
        # Risk Metrics
        risk_metrics = all_metrics['risk_metrics']
        print(f"\nRisk Metrics:")
        print(f"  Sharpe Ratio:         {risk_metrics['sharpe_ratio']:>15.2f}")
        print(f"  Max Drawdown:        ₹{risk_metrics['max_drawdown']:>15,.2f}")
        print(f"  Max Drawdown %:       {risk_metrics['max_drawdown_pct']:>15.2f}%")
        print(f"  Volatility:           {risk_metrics['volatility']:>15.2f}%")
        
        print("\n" + "=" * 80)
    
    def print_trade_breakdown(self, max_trades: int = 20) -> None:
        """
        Print trade-by-trade breakdown.
        
        Args:
            max_trades: Maximum number of trades to display
        """
        breakdown = self.metrics.get_trade_breakdown()
        
        if not breakdown:
            print("\nNo trades executed.")
            return
        
        print("\n" + "=" * 80)
        print(f"TRADE BREAKDOWN (Showing {min(len(breakdown), max_trades)} of {len(breakdown)} trades)")
        print("=" * 80)
        
        for i, trade in enumerate(breakdown[:max_trades]):
            print(f"\nTrade #{i+1}:")
            print(f"  Symbol:         {trade['symbol']}")
            print(f"  Strategy:       {trade['strategy']}")
            print(f"  Entry Time:     {trade['entry_time']}")
            print(f"  Exit Time:      {trade['exit_time']}")
            print(f"  Entry Price:    ₹{trade['entry_price']:.2f}")
            print(f"  Exit Price:     ₹{trade['exit_price']:.2f}")
            print(f"  Quantity:       {trade['quantity']}")
            print(f"  P&L:            ₹{trade['pnl']:,.2f} ({trade['pnl_pct']:.2f}%)")
            print(f"  Exit Reason:    {trade['exit_reason']}")
        
        if len(breakdown) > max_trades:
            print(f"\n... and {len(breakdown) - max_trades} more trades")
        
        print("\n" + "=" * 80)
    
    def save_to_json(self, output_dir: str = "backtest_results") -> str:
        """
        Save backtest results to JSON file.
        
        Args:
            output_dir: Directory to save results
            
        Returns:
            Path to saved file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_{timestamp}.json"
        filepath = output_path / filename
        
        # Prepare data for JSON serialization
        all_metrics = self.metrics.calculate_all_metrics()
        trade_breakdown = self.metrics.get_trade_breakdown()
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'initial_capital': self.results['initial_capital'],
            'final_capital': self.results['final_capital'],
            'total_pnl': self.results['total_pnl'],
            'metrics': all_metrics,
            'trades': trade_breakdown
        }
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Backtest results saved to: {filepath}")
        return str(filepath)
    
    def save_trades_to_csv(self, output_dir: str = "backtest_results") -> str:
        """
        Save trade breakdown to CSV file.
        
        Args:
            output_dir: Directory to save results
            
        Returns:
            Path to saved file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trades_{timestamp}.csv"
        filepath = output_path / filename
        
        # Get trade breakdown
        breakdown = self.metrics.get_trade_breakdown()
        
        if not breakdown:
            logger.warning("No trades to save")
            return ""
        
        # Write CSV
        with open(filepath, 'w') as f:
            # Header
            headers = breakdown[0].keys()
            f.write(','.join(headers) + '\n')
            
            # Data rows
            for trade in breakdown:
                values = [str(trade[h]) for h in headers]
                f.write(','.join(values) + '\n')
        
        logger.info(f"Trade breakdown saved to: {filepath}")
        return str(filepath)
