"""
Performance metrics calculator for backtest results.
Calculates returns, risk metrics, and trade statistics.
"""

from typing import List, Dict
from datetime import datetime
import math

from src.data.models import Trade, Portfolio


class PerformanceMetrics:
    """Calculate performance metrics from backtest results."""
    
    def __init__(
        self,
        initial_capital: float,
        final_capital: float,
        trades: List[Trade],
        portfolio: Portfolio
    ):
        """
        Initialize performance metrics calculator.
        
        Args:
            initial_capital: Starting capital
            final_capital: Ending capital
            trades: List of completed trades
            portfolio: Final portfolio state
        """
        self.initial_capital = initial_capital
        self.final_capital = final_capital
        self.trades = trades
        self.portfolio = portfolio
    
    def calculate_all_metrics(self) -> Dict:
        """
        Calculate all performance metrics.
        
        Returns:
            Dictionary with all metrics
        """
        return {
            'returns': self._calculate_returns(),
            'risk_metrics': self._calculate_risk_metrics(),
            'trade_stats': self._calculate_trade_stats(),
            'drawdown': self._calculate_drawdown()
        }
    
    def _calculate_returns(self) -> Dict:
        """
        Calculate return metrics.
        
        Returns:
            Dictionary with return metrics
        """
        total_return = self.final_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        return {
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'final_capital': self.final_capital,
            'initial_capital': self.initial_capital
        }
    
    def _calculate_risk_metrics(self) -> Dict:
        """
        Calculate risk metrics.
        
        Returns:
            Dictionary with risk metrics
        """
        if not self.trades:
            return {
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'max_drawdown_pct': 0.0,
                'volatility': 0.0
            }
        
        # Calculate daily returns from trades
        trade_returns = [
            (trade.pnl / (trade.entry_price * trade.quantity)) 
            for trade in self.trades
        ]
        
        # Calculate Sharpe ratio (assuming 252 trading days, 6% risk-free rate)
        if len(trade_returns) > 1:
            avg_return = sum(trade_returns) / len(trade_returns)
            std_return = math.sqrt(
                sum((r - avg_return) ** 2 for r in trade_returns) / (len(trade_returns) - 1)
            )
            
            if std_return > 0:
                # Annualize
                risk_free_rate = 0.06 / 252  # Daily risk-free rate
                sharpe_ratio = (avg_return - risk_free_rate) / std_return * math.sqrt(252)
            else:
                sharpe_ratio = 0.0
            
            volatility = std_return * math.sqrt(252) * 100  # Annualized volatility in %
        else:
            sharpe_ratio = 0.0
            volatility = 0.0
        
        # Calculate max drawdown
        max_drawdown, max_drawdown_pct = self._calculate_max_drawdown()
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'volatility': volatility
        }
    
    def _calculate_max_drawdown(self) -> tuple[float, float]:
        """
        Calculate maximum drawdown.
        
        Returns:
            Tuple of (max_drawdown_amount, max_drawdown_pct)
        """
        if not self.trades:
            return 0.0, 0.0
        
        # Build equity curve
        equity = self.initial_capital
        peak = equity
        max_dd = 0.0
        max_dd_pct = 0.0
        
        for trade in sorted(self.trades, key=lambda t: t.exit_time):
            equity += trade.pnl
            
            if equity > peak:
                peak = equity
            
            drawdown = peak - equity
            drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0.0
            
            if drawdown > max_dd:
                max_dd = drawdown
                max_dd_pct = drawdown_pct
        
        return max_dd, max_dd_pct
    
    def _calculate_trade_stats(self) -> Dict:
        """
        Calculate trade statistics.
        
        Returns:
            Dictionary with trade statistics
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'profit_factor': 0.0,
                'avg_trade_pnl': 0.0
            }
        
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        
        total_trades = len(self.trades)
        num_winning = len(winning_trades)
        num_losing = len(losing_trades)
        
        win_rate = (num_winning / total_trades * 100) if total_trades > 0 else 0.0
        
        avg_win = sum(t.pnl for t in winning_trades) / num_winning if num_winning > 0 else 0.0
        avg_loss = sum(t.pnl for t in losing_trades) / num_losing if num_losing > 0 else 0.0
        
        largest_win = max((t.pnl for t in winning_trades), default=0.0)
        largest_loss = min((t.pnl for t in losing_trades), default=0.0)
        
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0
        
        avg_trade_pnl = sum(t.pnl for t in self.trades) / total_trades
        
        return {
            'total_trades': total_trades,
            'winning_trades': num_winning,
            'losing_trades': num_losing,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'profit_factor': profit_factor,
            'avg_trade_pnl': avg_trade_pnl
        }
    
    def _calculate_drawdown(self) -> Dict:
        """
        Calculate detailed drawdown information.
        
        Returns:
            Dictionary with drawdown details
        """
        if not self.trades:
            return {
                'max_drawdown': 0.0,
                'max_drawdown_pct': 0.0,
                'current_drawdown': 0.0,
                'current_drawdown_pct': 0.0
            }
        
        # Build equity curve
        equity = self.initial_capital
        peak = equity
        current_dd = 0.0
        current_dd_pct = 0.0
        
        for trade in sorted(self.trades, key=lambda t: t.exit_time):
            equity += trade.pnl
            
            if equity > peak:
                peak = equity
            
            current_dd = peak - equity
            current_dd_pct = (current_dd / peak) * 100 if peak > 0 else 0.0
        
        max_dd, max_dd_pct = self._calculate_max_drawdown()
        
        return {
            'max_drawdown': max_dd,
            'max_drawdown_pct': max_dd_pct,
            'current_drawdown': current_dd,
            'current_drawdown_pct': current_dd_pct
        }
    
    def get_trade_breakdown(self) -> List[Dict]:
        """
        Get trade-by-trade breakdown.
        
        Returns:
            List of trade dictionaries
        """
        breakdown = []
        
        for trade in sorted(self.trades, key=lambda t: t.entry_time):
            breakdown.append({
                'symbol': trade.symbol,
                'strategy': trade.strategy_name,
                'entry_time': trade.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
                'exit_time': trade.exit_time.strftime('%Y-%m-%d %H:%M:%S'),
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'quantity': trade.quantity,
                'pnl': trade.pnl,
                'pnl_pct': trade.pnl_percent,
                'exit_reason': trade.exit_reason
            })
        
        return breakdown
