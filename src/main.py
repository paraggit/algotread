"""
Main entry point for the automated trading system.

Usage:
    uv run -m src.main --mode backtest --symbols RELIANCE,TCS --date 2024-01-15
    uv run -m src.main --mode paper --symbols NIFTY50
    uv run -m src.main --mode live --symbols BANKNIFTY
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
    from datetime import datetime, timedelta
    from src.data.fetcher import KiteDataFetcher
    from src.backtest.backtest_engine import BacktestEngine
    from src.backtest.performance import PerformanceMetrics
    from src.backtest.report import BacktestReport
    
    logger.info(f"Running backtest for {symbols} on {date}")
    
    # Parse date
    try:
        backtest_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        logger.error(f"Invalid date format: {date}. Expected YYYY-MM-DD")
        return
    
    # Initialize data fetcher
    try:
        data_fetcher = KiteDataFetcher(config.kite, cache_dir="data/cache")
    except Exception as e:
        logger.error(f"Failed to initialize data fetcher: {e}")
        logger.error("Please check your Kite API credentials in .env file")
        return
    
    # Fetch historical data for each symbol
    historical_data = {}
    
    # For intraday backtest, fetch data for the single day
    # Add some buffer to ensure we have enough data for indicators
    from_date = backtest_date - timedelta(days=5)  # Get a few days before for indicator warmup
    to_date = backtest_date + timedelta(days=1)
    
    for symbol in symbols:
        try:
            logger.info(f"Fetching data for {symbol}...")
            bars = data_fetcher.fetch_historical_data(
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                interval=config.data.interval,
                exchange="NSE"
            )
            
            if not bars:
                logger.warning(f"No data available for {symbol}")
                continue
            
            # Filter to only the backtest date for actual trading
            # but keep previous days for indicator calculation
            historical_data[symbol] = bars
            logger.info(f"Loaded {len(bars)} bars for {symbol}")
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            continue
    
    if not historical_data:
        logger.error("No data available for backtest")
        return
    
    # Create strategies (already created in main())
    # We'll get them from the caller
    # For now, create them here
    strategies = create_strategies(config)
    
    # Create risk manager
    risk_manager = RiskManager(config.risk, config.initial_capital)
    
    # Create backtest engine
    engine = BacktestEngine(
        strategies=strategies,
        risk_manager=risk_manager,
        initial_capital=config.initial_capital,
        interval_minutes=5  # TODO: Get from config
    )
    
    # Run backtest
    logger.info("Starting backtest engine...")
    results = engine.run(historical_data)
    
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
    
    # Save results
    json_path = report.save_to_json()
    csv_path = report.save_trades_to_csv()
    
    logger.info(f"Results saved to: {json_path}")
    if csv_path:
        logger.info(f"Trades saved to: {csv_path}")
    
    logger.info("Backtest completed successfully")


def run_paper_trading(config, symbols):
    """Run paper trading mode with live market data."""
    logger.info(f"Running paper trading for {symbols}")
    
    # Import paper trading components
    from src.data.websocket_client import KiteWebSocketClient
    from src.data.fetcher import KiteDataFetcher
    from src.paper.paper_engine import PaperTradingEngine
    
    # Create strategies
    strategies = create_strategies(config)
    
    # Create risk manager
    risk_manager = RiskManager(config.risk, config.initial_capital)
    
    # Create paper trading engine
    engine = PaperTradingEngine(
        strategies=strategies,
        risk_manager=risk_manager,
        initial_capital=config.initial_capital,
        interval_minutes=5
    )
    
    # Fetch instrument tokens
    logger.info("Fetching instrument tokens...")
    fetcher = KiteDataFetcher(config.kite)
    instrument_tokens = {}
    
    for symbol in symbols:
        try:
            token = fetcher._get_instrument_token(symbol, exchange="NSE")
            instrument_tokens[symbol] = token
            logger.info(f"Got instrument token for {symbol}: {token}")
        except Exception as e:
            logger.error(f"Failed to get instrument token for {symbol}: {e}")
            return
    
    # Create WebSocket client
    def on_bar(bar):
        """Handle new bar from WebSocket."""
        engine.on_bar(bar)
    
    def on_error(error):
        """Handle WebSocket error."""
        logger.error(f"WebSocket error: {error}")
    
    ws_client = KiteWebSocketClient(
        config=config.kite,
        symbols=symbols,
        interval_minutes=5,
        on_bar=on_bar,
        on_error=on_error
    )
    
    ws_client.set_instrument_tokens(instrument_tokens)
    
    # Start WebSocket
    logger.info("Starting WebSocket connection...")
    ws_client.start()
    
    # Wait for connection
    import time
    time.sleep(3)
    
    if not ws_client.is_connected:
        logger.error("Failed to connect to WebSocket")
        return
    
    logger.info("=" * 80)
    logger.info("Paper trading started successfully!")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 80)
    
    # Run until interrupted
    try:
        while True:
            time.sleep(10)
            
            # Print status every 10 seconds
            status = engine.get_status()
            logger.info(
                f"Status: Portfolio=₹{status['portfolio_value']:,.2f} | "
                f"P&L=₹{status['daily_pnl']:,.2f} | "
                f"Trades={status['total_trades']} | "
                f"Positions={status['open_positions']}"
            )
    
    except KeyboardInterrupt:
        logger.info("\nStopping paper trading...")
        ws_client.stop()
        
        # Print final summary
        logger.info("=" * 80)
        logger.info("PAPER TRADING SESSION SUMMARY")
        logger.info("=" * 80)
        
        status = engine.get_status()
        logger.info(f"Final Portfolio Value: ₹{status['portfolio_value']:,.2f}")
        logger.info(f"Total P&L: ₹{status['daily_pnl']:,.2f}")
        logger.info(f"Total Trades: {status['total_trades']}")
        logger.info(f"Winning Trades: {status['winning_trades']}")
        logger.info(f"Losing Trades: {status['losing_trades']}")
        
        if status['total_trades'] > 0:
            win_rate = (status['winning_trades'] / status['total_trades']) * 100
            logger.info(f"Win Rate: {win_rate:.2f}%")
        
        logger.info("=" * 80)


def run_live_trading(config, symbols):
    """Run live trading mode."""
    logger.critical("⚠️  LIVE TRADING MODE ⚠️")
    """Run live trading mode with real money."""
    logger.warning("=" * 80)
    logger.warning("⚠️  LIVE TRADING MODE - REAL MONEY AT RISK ⚠️")
    logger.warning("=" * 80)
    logger.warning("This mode will execute REAL trades with REAL money.")
    logger.warning("Losses can and will occur. Only proceed if you:")
    logger.warning("1. Have tested with paper trading for 1-2 weeks")
    logger.warning("2. Understand the risks involved")
    logger.warning("3. Can afford to lose the capital you're trading")
    logger.warning("=" * 80)
    
    # Require explicit confirmation
    logger.warning("\nType 'I UNDERSTAND THE RISKS' to proceed:")
    # In production, would wait for user input
    # For now, we'll just exit with a warning
    logger.error("Live trading requires explicit confirmation")
    logger.error("This is a safety mechanism to prevent accidental live trading")
    logger.error("\nTo enable live trading:")
    logger.error("1. Test thoroughly with paper trading first")
    logger.error("2. Modify this function to accept confirmation")
    logger.error("3. Start with minimal capital")
    return
    
    # Import live trading components
    from src.data.websocket_client import KiteWebSocketClient
    from src.data.fetcher import KiteDataFetcher
    from src.live.live_engine import LiveTradingEngine
    from kiteconnect import KiteConnect
    
    logger.info(f"Running live trading for {symbols}")
    
    # Initialize Kite connection
    kite = KiteConnect(api_key=config.kite.api_key)
    kite.set_access_token(config.kite.access_token)
    
    # Create strategies
    strategies = create_strategies(config)
    
    # Create risk manager
    risk_manager = RiskManager(config.risk, config.initial_capital)
    
    # Create live trading engine
    engine = LiveTradingEngine(
        kite=kite,
        strategies=strategies,
        risk_manager=risk_manager,
        initial_capital=config.initial_capital,
        interval_minutes=5,
        require_confirmation=True,  # ALWAYS require confirmation initially
        max_orders_per_day=10,
        emergency_stop_loss_pct=0.05  # 5% daily loss limit
    )
    
    # Sync positions with broker
    logger.info("Syncing positions with broker...")
    engine.sync_positions()
    
    # Fetch instrument tokens
    logger.info("Fetching instrument tokens...")
    fetcher = KiteDataFetcher(config.kite)
    instrument_tokens = {}
    
    for symbol in symbols:
        try:
            token = fetcher._get_instrument_token(symbol, exchange="NSE")
            instrument_tokens[symbol] = token
            logger.info(f"Got instrument token for {symbol}: {token}")
        except Exception as e:
            logger.error(f"Failed to get instrument token for {symbol}: {e}")
            return
    
    # Create WebSocket client
    def on_bar(bar):
        """Handle new bar from WebSocket."""
        engine.on_bar(bar)
    
    def on_error(error):
        """Handle WebSocket error."""
        logger.error(f"WebSocket error: {error}")
    
    ws_client = KiteWebSocketClient(
        config=config.kite,
        symbols=symbols,
        interval_minutes=5,
        on_bar=on_bar,
        on_error=on_error
    )
    
    ws_client.set_instrument_tokens(instrument_tokens)
    
    # Start WebSocket
    logger.info("Starting WebSocket connection...")
    ws_client.start()
    
    # Wait for connection
    import time
    time.sleep(3)
    
    if not ws_client.is_connected:
        logger.error("Failed to connect to WebSocket")
        return
    
    logger.info("=" * 80)
    logger.info("Live trading started successfully!")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 80)
    
    # Run until interrupted
    try:
        while True:
            time.sleep(10)
            
            # Print status every 10 seconds
            status = engine.get_status()
            logger.info(
                f"Status: Portfolio=₹{status['portfolio_value']:,.2f} | "
                f"P&L=₹{status['daily_pnl']:,.2f} | "
                f"Trades={status['total_trades']} | "
                f"Positions={status['open_positions']} | "
                f"Orders Today={status['orders_today']}"
            )
            
            # Sync positions periodically
            if int(time.time()) % 60 == 0:  # Every minute
                engine.sync_positions()
                engine.order_manager.sync_orders()
    
    except KeyboardInterrupt:
        logger.info("\nStopping live trading...")
        
        # Close all positions
        logger.warning("Closing all open positions...")
        engine._close_all_positions()
        
        # Cancel all pending orders
        logger.warning("Cancelling all pending orders...")
        engine.order_manager.cancel_all_orders()
        
        # Stop WebSocket
        ws_client.stop()
        
        # Print final summary
        logger.info("=" * 80)
        logger.info("LIVE TRADING SESSION SUMMARY")
        logger.info("=" * 80)
        
        status = engine.get_status()
        logger.info(f"Final Portfolio Value: ₹{status['portfolio_value']:,.2f}")
        logger.info(f"Total P&L: ₹{status['daily_pnl']:,.2f}")
        logger.info(f"Total Trades: {status['total_trades']}")
        logger.info(f"Winning Trades: {status['winning_trades']}")
        logger.info(f"Losing Trades: {status['losing_trades']}")
        logger.info(f"Orders Placed: {status['orders_today']}")
        
        if status['total_trades'] > 0:
            win_rate = (status['winning_trades'] / status['total_trades']) * 100
            logger.info(f"Win Rate: {win_rate:.2f}%")
        
        logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated Intraday Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backtest
  uv run -m src.main --mode backtest --symbols RELIANCE,TCS --date 2024-01-15
  
  # Paper trading
  uv run -m src.main --mode paper --symbols NIFTY50
  
  # Live trading (use with extreme caution!)
  uv run -m src.main --mode live --symbols BANKNIFTY
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
