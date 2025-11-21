"""Tests for risk management."""

from datetime import datetime, time
import pytest

from src.config import RiskConfig
from src.core.risk import RiskManager
from src.data.models import (
    TradeInstruction,
    StrategySignal,
    Portfolio,
    Position,
    OrderType
)


@pytest.fixture
def risk_config():
    """Create risk configuration for testing."""
    return RiskConfig(
        max_risk_per_trade=0.02,
        max_daily_loss=0.03,
        max_losing_trades_per_day=3,
        min_minutes_after_open=15,
        cutoff_time="14:45"
    )


@pytest.fixture
def risk_manager(risk_config):
    """Create risk manager instance."""
    return RiskManager(risk_config, initial_capital=100000.0)


@pytest.fixture
def portfolio():
    """Create portfolio for testing."""
    return Portfolio(cash=100000.0)


@pytest.fixture
def long_instruction():
    """Create sample long trade instruction."""
    return TradeInstruction(
        signal=StrategySignal.ENTRY_LONG,
        symbol="TEST",
        quantity=0,
        stop_loss=95.0,
        target=105.0,
        reason="Test entry",
        strategy_name="test_strategy",
        entry_price=100.0,
        order_type=OrderType.MARKET
    )


def test_position_sizing(risk_manager, long_instruction, portfolio):
    """Test position size calculation."""
    quantity = risk_manager.calculate_position_size(long_instruction, portfolio)
    
    # Should return positive quantity
    assert quantity > 0
    
    # Risk should be approximately 2% of capital
    risk_per_share = abs(long_instruction.entry_price - long_instruction.stop_loss)
    total_risk = risk_per_share * quantity
    risk_pct = total_risk / portfolio.cash
    
    # Allow some tolerance due to rounding
    assert 0.015 <= risk_pct <= 0.025


def test_daily_loss_limit(risk_manager, long_instruction, portfolio):
    """Test daily loss limit enforcement."""
    # Set portfolio to have breached daily loss limit
    portfolio.daily_pnl = -3500.0  # -3.5% of 100k
    
    is_allowed, reason = risk_manager.validate_trade(long_instruction, portfolio)
    
    assert not is_allowed
    assert "daily loss limit" in reason.lower()
    assert risk_manager.kill_switch_active


def test_max_losing_trades(risk_manager, long_instruction, portfolio):
    """Test max losing trades per day enforcement."""
    # Set portfolio to have max losing trades
    portfolio.daily_losing_trades = 3
    
    is_allowed, reason = risk_manager.validate_trade(long_instruction, portfolio)
    
    assert not is_allowed
    assert "losing trades" in reason.lower()
    assert risk_manager.kill_switch_active


def test_time_filter_too_early(risk_manager, long_instruction, portfolio):
    """Test time filter - too early after market open."""
    # 9:20 AM (only 5 minutes after open)
    current_time = datetime(2024, 1, 15, 9, 20, 0)
    
    is_allowed, reason = risk_manager.validate_trade(
        long_instruction, portfolio, current_time
    )
    
    assert not is_allowed
    assert "too early" in reason.lower()


def test_time_filter_after_cutoff(risk_manager, long_instruction, portfolio):
    """Test time filter - after cutoff time."""
    # 2:50 PM (after 2:45 PM cutoff)
    current_time = datetime(2024, 1, 15, 14, 50, 0)
    
    is_allowed, reason = risk_manager.validate_trade(
        long_instruction, portfolio, current_time
    )
    
    assert not is_allowed
    assert "cutoff" in reason.lower()


def test_time_filter_valid(risk_manager, long_instruction, portfolio):
    """Test time filter - valid trading time."""
    # 11:00 AM (valid trading time)
    current_time = datetime(2024, 1, 15, 11, 0, 0)
    
    is_allowed, reason = risk_manager.validate_trade(
        long_instruction, portfolio, current_time
    )
    
    assert is_allowed


def test_existing_position(risk_manager, long_instruction, portfolio):
    """Test rejection when position already exists."""
    # Add existing position
    position = Position(
        symbol="TEST",
        quantity=100,
        average_price=100.0,
        current_price=100.0,
        entry_time=datetime.now(),
        strategy_name="test_strategy"
    )
    portfolio.add_position(position)
    
    is_allowed, reason = risk_manager.validate_trade(
        long_instruction, portfolio, datetime(2024, 1, 15, 11, 0, 0)
    )
    
    assert not is_allowed
    assert "already have position" in reason.lower()


def test_kill_switch_reset(risk_manager):
    """Test kill switch reset."""
    # Activate kill switch
    risk_manager._activate_kill_switch("Test reason")
    assert risk_manager.kill_switch_active
    
    # Reset
    risk_manager.reset_kill_switch()
    assert not risk_manager.kill_switch_active


def test_risk_metrics(risk_manager, portfolio):
    """Test risk metrics calculation."""
    portfolio.daily_pnl = -1500.0
    portfolio.daily_trades = 5
    portfolio.daily_losing_trades = 2
    
    metrics = risk_manager.get_risk_metrics(portfolio)
    
    assert metrics["daily_pnl"] == -1500.0
    assert metrics["daily_trades"] == 5
    assert metrics["daily_losing_trades"] == 2
    assert metrics["kill_switch_active"] == False
    assert metrics["daily_loss_limit"] == 3000.0  # 3% of 100k
    assert 0 < metrics["daily_loss_used_pct"] < 100
