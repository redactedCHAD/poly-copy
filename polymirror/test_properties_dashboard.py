"""
Property-based tests for dashboard module.

Tests metrics calculation accuracy using Hypothesis.
"""

import pytest
import sqlite3
import tempfile
import os
from hypothesis import given, settings, strategies as st, HealthCheck
from dashboard import calculate_metrics


# Custom strategy for generating trade records
@st.composite
def trade_record(draw):
    """Generate a valid trade record tuple."""
    trade_id = draw(st.integers(min_value=1, max_value=1000000))
    timestamp = draw(st.floats(min_value=1600000000.0, max_value=1800000000.0))
    market = draw(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=50))
    outcome = draw(st.sampled_from(["Yes", "No"]))
    side = draw(st.sampled_from(["BUY", "SELL"]))
    size_usdc = draw(st.floats(min_value=0.01, max_value=10000.0))
    price = draw(st.floats(min_value=0.01, max_value=0.99))
    status = draw(st.sampled_from(["SUCCESS", "FAILED"]))
    
    return (trade_id, timestamp, market, outcome, side, size_usdc, price, status)


@st.composite
def trade_list(draw):
    """Generate a list of trade records."""
    num_trades = draw(st.integers(min_value=0, max_value=50))
    trades = [draw(trade_record()) for _ in range(num_trades)]
    return trades


class TestMetricsCalculation:
    """Property-based tests for metrics calculation."""
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(trades=trade_list())
    def test_property_12_metrics_calculation_accuracy(self, trades):
        """
        Feature: polymarket-copy-trader, Property 12: Metrics calculation accuracy
        
        For any set of trade records in the database, the displayed total trades 
        count should equal the number of records, and the total volume should 
        equal the sum of all size_usdc values.
        
        Validates: Requirements 7.7
        """
        # Calculate metrics
        total_trades, total_volume, last_trade_time = calculate_metrics(trades)
        
        # Property 1: Total trades count equals number of records
        assert total_trades == len(trades), \
            f"Total trades {total_trades} does not match record count {len(trades)}"
        
        # Property 2: Total volume equals sum of all size_usdc values
        expected_volume = sum(trade[5] for trade in trades) if trades else 0.0
        assert abs(total_volume - expected_volume) < 0.01, \
            f"Total volume {total_volume} does not match expected {expected_volume}"
        
        # Property 3: Last trade time is the first record's timestamp (or None if empty)
        if trades:
            expected_last_time = trades[0][1]
            assert last_trade_time == expected_last_time, \
                f"Last trade time {last_trade_time} does not match expected {expected_last_time}"
        else:
            assert last_trade_time is None, \
                f"Last trade time should be None for empty trades, got {last_trade_time}"
    
    @settings(max_examples=100)
    @given(trades=trade_list())
    def test_metrics_non_negative(self, trades):
        """
        Test that metrics are always non-negative.
        
        This is an invariant that should hold for all valid trade data.
        """
        total_trades, total_volume, last_trade_time = calculate_metrics(trades)
        
        assert total_trades >= 0, f"Total trades cannot be negative: {total_trades}"
        assert total_volume >= 0, f"Total volume cannot be negative: {total_volume}"
    
    @settings(max_examples=100)
    @given(
        trades=st.lists(
            trade_record(),
            min_size=1,
            max_size=50
        )
    )
    def test_metrics_with_non_empty_trades(self, trades):
        """
        Test that metrics are correctly calculated for non-empty trade lists.
        
        This ensures the function handles the common case properly.
        """
        total_trades, total_volume, last_trade_time = calculate_metrics(trades)
        
        # With non-empty trades, count should be positive
        assert total_trades > 0
        
        # Volume should match sum
        expected_volume = sum(trade[5] for trade in trades)
        assert abs(total_volume - expected_volume) < 0.01
        
        # Last trade time should not be None
        assert last_trade_time is not None
        assert last_trade_time == trades[0][1]
    
    def test_metrics_with_empty_trades(self):
        """
        Test that metrics handle empty trade list correctly.
        
        This is an important edge case.
        """
        total_trades, total_volume, last_trade_time = calculate_metrics([])
        
        assert total_trades == 0
        assert total_volume == 0.0
        assert last_trade_time is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
