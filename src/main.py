"""
Main entry point for the automated trading system.

Usage:
    uv run src/main.py --mode backtest --symbols RELIANCE,TCS --date 2024-01-15
    uv run src/main.py --mode paper --symbols NIFTY50
    uv run src/main.py --mode live --symbols BANKNIFTY
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.config import get_config, TradingMode
from src.core.indicators import calculate_all_indicators
from src.core.risk import RiskManager
from src.core.strategies.orb_supertrend import ORBSupertrendStrategy
from src.core.strategies.ema_trend import EMATrendStrategy
from src.core.strategies.vwap_reversion import VWAPReversionStrategy
from src.data.models import Portfolio
from src.llm.llm_client import create_llm_client
from src.llm.regime_classifier import RegimeClassifier
from src.llm.sentiment_analyzer import SentimentAnalyzer
from src.llm.trade_journal import TradeJournal


def setup_logging(config):
    """Setup logging configuration."""
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stderr,
        level=config.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>"
    )
    
    # Add file logger
    log_path = Path(config.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        config.log_file,
        level=config.log_level,
        rotation="1 day",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} | {message}"
    )


def create_strategies(config):
    """Create strategy instances based on configuration."""
    strategies = []
    
    for strategy_name in config.strategy.enabled_strategies:
        if strategy_name == "orb_supertrend":
            strategy = ORBSupertrendStrategy(
                orb_period_minutes=config.strategy.orb_period_minutes,
                interval_minutes=5,  # TODO: Get from config
                volume_multiplier=config.strategy.orb_volume_multiplier,
                rsi_threshold=config.strategy.orb_rsi_threshold,
                supertrend_period=config.strategy.supertrend_period,
                supertrend_multiplier=config.strategy.supertrend_multiplier,
                atr_sl_multiplier=2.0,
                reward_ratio=1.5,
                max_risk_pct=config.risk.max_risk_per_trade
            )
            strategies.append(strategy)
            logger.info(f"Loaded strategy: {strategy.name}")
            
        elif strategy_name == "ema_trend":
            strategy = EMATrendStrategy(
                ema_fast=config.strategy.ema_fast,
                ema_slow=config.strategy.ema_slow,
                use_vwap_filter=True,
                use_rsi_filter=False,
                atr_sl_multiplier=2.0,
                reward_ratio=1.5,
                max_risk_pct=config.risk.max_risk_per_trade,
                allow_short=False
            )
            strategies.append(strategy)
            logger.info(f"Loaded strategy: {strategy.name}")
            
        elif strategy_name == "vwap_reversion":
            strategy = VWAPReversionStrategy(
                vwap_deviation_pct=1.0,
                rsi_oversold=30.0,
                rsi_overbought=70.0,
                atr_sl_multiplier=1.0,
                reward_ratio=1.0,
                max_risk_pct=0.01  # Lower risk for mean reversion
            )
            strategies.append(strategy)
            logger.info(f"Loaded strategy: {strategy.name}")
        else:
            logger.warning(f"Unknown strategy: {strategy_name}")
    
    return strategies


def run_backtest(config, symbols, date):
    """Run backtest mode."""
    logger.info(f"Running backtest for {symbols} on {date}")
    logger.warning("Backtest mode not fully implemented yet - data fetcher needed")
    
    # TODO: Implement backtest
    # 1. Fetch historical data for symbols and date
    # 2. Calculate indicators
    # 3. Evaluate strategies
    # 4. Simulate trades
    # 5. Generate report
    
    logger.info("Backtest completed (placeholder)")


def run_paper_trading(config, symbols):
    """Run paper trading mode."""
    logger.info(f"Running paper trading for {symbols}")
    logger.warning("Paper trading mode not fully implemented yet - live data fetcher needed")
    
    # TODO: Implement paper trading
    # 1. Connect to live data stream
    # 2. Calculate indicators in real-time
    # 3. Evaluate strategies
    # 4. Simulate trades (no real orders)
    # 5. Track performance
    
    logger.info("Paper trading started (placeholder)")


def run_live_trading(config, symbols):
    """Run live trading mode."""
    logger.critical("⚠️  LIVE TRADING MODE ⚠️")
    logger.critical("This will place REAL orders with REAL money!")
    
    # Safety confirmation
    confirmation = input("Type 'I UNDERSTAND THE RISKS' to proceed: ")
    if confirmation != "I UNDERSTAND THE RISKS":
        logger.info("Live trading cancelled by user")
        return
    
    logger.info(f"Running live trading for {symbols}")
    logger.warning("Live trading mode not fully implemented yet - broker integration needed")
    
    # TODO: Implement live trading
    # 1. Connect to live data stream
    # 2. Connect to broker API
    # 3. Calculate indicators in real-time
    # 4. Evaluate strategies
    # 5. Validate with risk manager
    # 6. Place real orders
    # 7. Monitor positions
    # 8. Handle exits
    
    logger.info("Live trading started (placeholder)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated Intraday Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backtest
  uv run src/main.py --mode backtest --symbols RELIANCE,TCS --date 2024-01-15
  
  # Paper trading
  uv run src/main.py --mode paper --symbols NIFTY50
  
  # Live trading (use with extreme caution!)
  uv run src/main.py --mode live --symbols BANKNIFTY
        """
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=["backtest", "paper", "live"],
        help="Trading mode"
    )
    
    parser.add_argument(
        "--symbols",
        type=str,
        help="Comma-separated list of symbols to trade"
    )
    
    parser.add_argument(
        "--date",
        type=str,
        help="Date for backtest (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to custom config file (optional)"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = get_config()
    
    # Override mode if provided
    if args.mode:
        config.mode = TradingMode(args.mode)
    
    # Override watchlist if provided
    if args.symbols:
        config.watchlist = [s.strip() for s in args.symbols.split(",")]
    
    # Setup logging
    setup_logging(config)
    
    logger.info("=" * 80)
    logger.info("AlgoTread - Automated Intraday Trading System")
    logger.info("=" * 80)
    logger.info(f"Mode: {config.mode.value}")
    logger.info(f"Watchlist: {', '.join(config.watchlist)}")
    logger.info(f"Initial Capital: ₹{config.initial_capital:,.2f}")
    logger.info(f"Enabled Strategies: {', '.join(config.strategy.enabled_strategies)}")
    logger.info("=" * 80)
    
    # Create components
    logger.info("Initializing components...")
    
    # Strategies
    strategies = create_strategies(config)
    logger.info(f"Loaded {len(strategies)} strategies")
    
    # Risk manager
    risk_manager = RiskManager(config.risk, config.initial_capital)
    logger.info("Risk manager initialized")
    
    # LLM components
    llm_client = create_llm_client(config.llm)
    regime_classifier = RegimeClassifier(llm_client)
    sentiment_analyzer = SentimentAnalyzer(llm_client)
    trade_journal = TradeJournal(llm_client)
    logger.info(f"LLM components initialized (provider: {config.llm.provider.value})")
    
    # Portfolio
    portfolio = Portfolio(cash=config.initial_capital)
    logger.info("Portfolio initialized")
    
    logger.info("All components initialized successfully")
    logger.info("=" * 80)
    
    # Run based on mode
    try:
        if config.mode == TradingMode.BACKTEST:
            if not args.date:
                logger.error("--date is required for backtest mode")
                sys.exit(1)
            run_backtest(config, config.watchlist, args.date)
            
        elif config.mode == TradingMode.PAPER:
            run_paper_trading(config, config.watchlist)
            
        elif config.mode == TradingMode.LIVE:
            run_live_trading(config, config.watchlist)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        logger.info("=" * 80)
        logger.info("Shutdown complete")
        logger.info("=" * 80)


if __name__ == "__main__":
    main()
