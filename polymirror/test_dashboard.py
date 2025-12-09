"""
Unit tests for dashboard module.

Tests config loading/saving, metrics calculation, and empty state handling.
"""

import pytest
import json
import sqlite3
import os
import tempfile
from unittest.mock import patch, mock_open, Mock
from dashboard import load_config, save_config, get_trades, calculate_metrics


class TestConfigManagement:
    """Test suite for configuration loading and saving."""
    
    def test_load_config_success(self):
        """Test that config is loaded correctly from valid JSON file."""
        config_data = {
            "is_active": True,
            "max_cap_usdc": 500.0,
            "copy_ratio": 0.1,
            "target_wallet": "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(config_data))):
            result = load_config()
            
            assert result == config_data
            assert result["is_active"] == True
            assert result["max_cap_usdc"] == 500.0
    
    def test_load_config_file_not_found(self):
        """Test that load_config handles missing file gracefully."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            with patch("streamlit.error") as mock_error:
                result = load_config()
                
                assert result is None
                mock_error.assert_called_once()
    
    def test_load_config_invalid_json(self):
        """Test that load_config handles invalid JSON gracefully."""
        with patch("builtins.open", mock_open(read_data="invalid json {")):
            with patch("streamlit.error") as mock_error:
                result = load_config()
                
                assert result is None
                mock_error.assert_called_once()
    
    def test_save_config_success(self):
        """Test that config is saved correctly."""
        config_data = {
            "is_active": False,
            "max_cap_usdc": 1000.0,
            "copy_ratio": 0.2,
            "target_wallet": "0xtest"
        }
        
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            result = save_config(config_data)
            
            assert result == True
            mock_file.assert_called_once_with("config.json", "w")
            
            # Verify json.dump was called with correct data
            handle = mock_file()
            written_data = "".join(call.args[0] for call in handle.write.call_args_list)
            loaded_data = json.loads(written_data)
            assert loaded_data == config_data
    
    def test_save_config_failure(self):
        """Test that save_config handles write errors gracefully."""
        config_data = {"is_active": True}
        
        with patch("builtins.open", side_effect=IOError("Write failed")):
            with patch("streamlit.error") as mock_error:
                result = save_config(config_data)
                
                assert result == False
                mock_error.assert_called_once()


class TestTradesRetrieval:
    """Test suite for trades database queries."""
    
    def setup_method(self):
        """Set up test database."""
        self.temp_db = "test_dashboard_trades.db"
        conn = sqlite3.connect(self.temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                market TEXT NOT NULL,
                outcome TEXT NOT NULL,
                side TEXT NOT NULL,
                size_usdc REAL NOT NULL,
                price REAL NOT NULL,
                status TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    
    def teardown_method(self):
        """Clean up test database."""
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def test_get_trades_with_data(self):
        """Test that get_trades retrieves trades correctly."""
        # Insert test data
        conn = sqlite3.connect(self.temp_db)
        cursor = conn.cursor()
        
        test_trades = [
            (1609459200.0, "Will Trump win 2024?", "Yes", "BUY", 100.0, 0.55, "SUCCESS"),
            (1609459300.0, "Will it rain?", "No", "SELL", 50.0, 0.45, "SUCCESS"),
            (1609459400.0, "Test market", "Yes", "BUY", 75.0, 0.60, "FAILED"),
        ]
        
        for trade in test_trades:
            cursor.execute("""
                INSERT INTO trades (timestamp, market, outcome, side, size_usdc, price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, trade)
        
        conn.commit()
        conn.close()
        
        # Test retrieval
        with patch("sqlite3.connect", return_value=sqlite3.connect(self.temp_db)):
            trades = get_trades()
            
            assert len(trades) == 3
            # Should be ordered by ID descending (most recent first)
            assert trades[0][2] == "Test market"  # market is index 2
            assert trades[1][2] == "Will it rain?"
            assert trades[2][2] == "Will Trump win 2024?"
    
    def test_get_trades_limit_50(self):
        """Test that get_trades limits results to 50 records."""
        # Insert 60 test trades
        conn = sqlite3.connect(self.temp_db)
        cursor = conn.cursor()
        
        for i in range(60):
            cursor.execute("""
                INSERT INTO trades (timestamp, market, outcome, side, size_usdc, price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (1609459200.0 + i, f"Market {i}", "Yes", "BUY", 10.0, 0.5, "SUCCESS"))
        
        conn.commit()
        conn.close()
        
        # Test retrieval
        with patch("sqlite3.connect", return_value=sqlite3.connect(self.temp_db)):
            trades = get_trades()
            
            assert len(trades) == 50
    
    def test_get_trades_empty_database(self):
        """Test that get_trades handles empty database gracefully."""
        with patch("sqlite3.connect", return_value=sqlite3.connect(self.temp_db)):
            trades = get_trades()
            
            assert trades == []
    
    def test_get_trades_database_error(self):
        """Test that get_trades handles database errors gracefully."""
        with patch("sqlite3.connect", side_effect=sqlite3.Error("Connection failed")):
            with patch("streamlit.error") as mock_error:
                trades = get_trades()
                
                assert trades == []
                mock_error.assert_called_once()
    
    def test_get_trades_file_not_found(self):
        """Test that get_trades handles missing database file gracefully."""
        with patch("sqlite3.connect", side_effect=FileNotFoundError()):
            with patch("streamlit.warning") as mock_warning:
                trades = get_trades()
                
                assert trades == []
                mock_warning.assert_called_once()


class TestMetricsCalculation:
    """Test suite for metrics calculation."""
    
    def test_calculate_metrics_with_trades(self):
        """Test metrics calculation with valid trade data."""
        trades = [
            (1, 1609459400.0, "Market 1", "Yes", "BUY", 100.0, 0.55, "SUCCESS"),
            (2, 1609459300.0, "Market 2", "No", "SELL", 50.0, 0.45, "SUCCESS"),
            (3, 1609459200.0, "Market 3", "Yes", "BUY", 75.0, 0.60, "FAILED"),
        ]
        
        total_trades, total_volume, last_trade_time = calculate_metrics(trades)
        
        assert total_trades == 3
        assert total_volume == 225.0  # 100 + 50 + 75
        assert last_trade_time == 1609459400.0  # First trade's timestamp
    
    def test_calculate_metrics_empty_trades(self):
        """Test metrics calculation with empty trade list."""
        total_trades, total_volume, last_trade_time = calculate_metrics([])
        
        assert total_trades == 0
        assert total_volume == 0.0
        assert last_trade_time is None
    
    def test_calculate_metrics_single_trade(self):
        """Test metrics calculation with single trade."""
        trades = [
            (1, 1609459200.0, "Market 1", "Yes", "BUY", 100.0, 0.55, "SUCCESS"),
        ]
        
        total_trades, total_volume, last_trade_time = calculate_metrics(trades)
        
        assert total_trades == 1
        assert total_volume == 100.0
        assert last_trade_time == 1609459200.0
    
    def test_calculate_metrics_with_failed_trades(self):
        """Test that metrics include failed trades in volume calculation."""
        trades = [
            (1, 1609459200.0, "Market 1", "Yes", "BUY", 100.0, 0.55, "SUCCESS"),
            (2, 1609459300.0, "Market 2", "No", "SELL", 50.0, 0.45, "FAILED"),
        ]
        
        total_trades, total_volume, last_trade_time = calculate_metrics(trades)
        
        assert total_trades == 2
        assert total_volume == 150.0  # Includes failed trade
    
    def test_calculate_metrics_decimal_precision(self):
        """Test that metrics handle decimal values correctly."""
        trades = [
            (1, 1609459200.0, "Market 1", "Yes", "BUY", 10.50, 0.55, "SUCCESS"),
            (2, 1609459300.0, "Market 2", "No", "SELL", 25.75, 0.45, "SUCCESS"),
            (3, 1609459400.0, "Market 3", "Yes", "BUY", 33.33, 0.60, "SUCCESS"),
        ]
        
        total_trades, total_volume, last_trade_time = calculate_metrics(trades)
        
        assert total_trades == 3
        assert abs(total_volume - 69.58) < 0.01  # Handle floating point precision


class TestEmptyStateHandling:
    """Test suite for empty state display."""
    
    def test_empty_state_with_no_trades(self):
        """Test that empty state is displayed when no trades exist."""
        # This test verifies the logic, actual Streamlit rendering would need integration tests
        trades = []
        
        assert len(trades) == 0
        
        # Verify metrics show zeros
        total_trades, total_volume, last_trade_time = calculate_metrics(trades)
        assert total_trades == 0
        assert total_volume == 0.0
        assert last_trade_time is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
