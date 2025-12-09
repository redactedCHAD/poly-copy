"""
Unit tests for executor module

Tests client initialization, order construction, database logging, and error handling.
"""

import pytest
import os
import json
import sqlite3
import tempfile
from unittest.mock import patch, Mock, MagicMock
from executor import get_client, log_trade_to_db, execute_copy_trade


class TestExecutor:
    """Test suite for executor module"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        # Create temporary database for testing
        self.temp_db = "test_trades.db"
        conn = sqlite3.connect(self.temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
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
        
        # Create temporary config file
        self.temp_config = "test_config.json"
        config = {
            "is_active": True,
            "max_cap_usdc": 500.0,
            "copy_ratio": 0.1,
            "target_wallet": "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"
        }
        with open(self.temp_config, "w") as f:
            json.dump(config, f)
    
    def teardown_method(self):
        """Clean up test environment after each test"""
        # Remove temporary files
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
        if os.path.exists(self.temp_config):
            os.remove(self.temp_config)
    
    def test_client_initialization_with_private_key(self):
        """Test that ClobClient is initialized with private key"""
        test_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        with patch.dict(os.environ, {"MY_PRIVATE_KEY": test_key}):
            with patch('executor.ClobClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                client = get_client()
                
                # Verify ClobClient was called with correct parameters
                mock_client_class.assert_called_once()
                call_kwargs = mock_client_class.call_args[1]
                assert call_kwargs["key"] == test_key
                assert call_kwargs["chain_id"] == 137
                assert call_kwargs["host"] == "https://clob.polymarket.com"
    
    def test_client_initialization_with_api_credentials(self):
        """Test that ClobClient uses provided API credentials"""
        test_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        test_api_key = "test_api_key"
        test_api_secret = "test_api_secret"
        test_api_passphrase = "test_passphrase"
        
        env_vars = {
            "MY_PRIVATE_KEY": test_key,
            "POLY_API_KEY": test_api_key,
            "POLY_API_SECRET": test_api_secret,
            "POLY_API_PASSPHRASE": test_api_passphrase
        }
        
        with patch.dict(os.environ, env_vars):
            with patch('executor.ClobClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                client = get_client()
                
                # Verify API credentials were passed
                call_kwargs = mock_client_class.call_args[1]
                assert "creds" in call_kwargs
                assert call_kwargs["creds"]["api_key"] == test_api_key
                assert call_kwargs["creds"]["api_secret"] == test_api_secret
                assert call_kwargs["creds"]["api_passphrase"] == test_api_passphrase
    
    def test_client_initialization_missing_private_key(self):
        """Test that missing private key raises ValueError"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="MY_PRIVATE_KEY"):
                get_client()
    
    def test_database_logging_success(self):
        """Test that successful trades are logged to database"""
        with patch('executor.sqlite3.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            log_trade_to_db(
                market_name="Will Trump win 2024?",
                outcome="Yes",
                side="BUY",
                size=50.0,
                price=0.55,
                status="SUCCESS"
            )
            
            # Verify database insert was called
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args[0]
            assert "INSERT INTO trades" in call_args[0]
            
            # Verify values
            values = call_args[1]
            assert values[1] == "Will Trump win 2024?"
            assert values[2] == "Yes"
            assert values[3] == "BUY"
            assert values[4] == 50.0
            assert values[5] == 0.55
            assert values[6] == "SUCCESS"
            
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()
    
    def test_database_logging_failure(self):
        """Test that failed trades are logged to database"""
        with patch('executor.sqlite3.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            log_trade_to_db(
                market_name="Will it rain?",
                outcome="No",
                side="SELL",
                size=0,
                price=0.45,
                status="FAILED"
            )
            
            # Verify status is FAILED
            call_args = mock_cursor.execute.call_args[0]
            values = call_args[1]
            assert values[6] == "FAILED"
    
    def test_database_logging_error_handling(self):
        """Test that database errors don't crash the bot"""
        with patch('executor.sqlite3.connect') as mock_connect:
            mock_connect.side_effect = Exception("Database connection failed")
            
            # Should not raise exception
            log_trade_to_db(
                market_name="Test",
                outcome="Yes",
                side="BUY",
                size=10.0,
                price=0.5,
                status="SUCCESS"
            )
    
    def test_order_construction_buy_side(self):
        """Test order construction for BUY orders"""
        test_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        with patch.dict(os.environ, {"MY_PRIVATE_KEY": test_key}):
            with patch('executor.ClobClient') as mock_client_class:
                with patch('asset_mapper.get_market_details') as mock_market:
                    with patch('builtins.open', create=True) as mock_open:
                        # Mock config file
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value.read.return_value = json.dumps({
                            "is_active": True,
                            "max_cap_usdc": 500.0,
                            "copy_ratio": 0.1,
                            "target_wallet": "0xtest"
                        })
                        mock_open.return_value = mock_file
                        
                        # Mock market details
                        mock_market.return_value = {
                            "question": "Test Market",
                            "outcome": "Yes",
                            "market_slug": "test"
                        }
                        
                        # Mock client
                        mock_client = Mock()
                        mock_client.get_order_book.return_value = {
                            "asks": [{"price": "0.55"}],
                            "bids": [{"price": "0.54"}]
                        }
                        mock_client.create_and_post_order.return_value = {"success": True}
                        mock_client_class.return_value = mock_client
                        
                        with patch('executor.log_trade_to_db') as mock_log:
                            execute_copy_trade(12345, "BUY", target_price=0.55)
                            
                            # Verify order was created
                            mock_client.create_and_post_order.assert_called_once()
                            order_args = mock_client.create_and_post_order.call_args[0][0]
                            
                            assert order_args.token_id == "12345"
                            assert order_args.side == "BUY"
                            assert order_args.price == 0.55
    
    def test_order_construction_sell_side(self):
        """Test order construction for SELL orders"""
        test_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        with patch.dict(os.environ, {"MY_PRIVATE_KEY": test_key}):
            with patch('executor.ClobClient') as mock_client_class:
                with patch('asset_mapper.get_market_details') as mock_market:
                    with patch('builtins.open', create=True) as mock_open:
                        # Mock config file
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value.read.return_value = json.dumps({
                            "is_active": True,
                            "max_cap_usdc": 500.0,
                            "copy_ratio": 0.1,
                            "target_wallet": "0xtest"
                        })
                        mock_open.return_value = mock_file
                        
                        # Mock market details
                        mock_market.return_value = {
                            "question": "Test Market",
                            "outcome": "No",
                            "market_slug": "test"
                        }
                        
                        # Mock client
                        mock_client = Mock()
                        mock_client.get_order_book.return_value = {
                            "asks": [{"price": "0.55"}],
                            "bids": [{"price": "0.54"}]
                        }
                        mock_client.create_and_post_order.return_value = {"success": True}
                        mock_client_class.return_value = mock_client
                        
                        with patch('executor.log_trade_to_db') as mock_log:
                            execute_copy_trade(12345, "SELL", target_price=0.54)
                            
                            # Verify order was created with SELL side
                            order_args = mock_client.create_and_post_order.call_args[0][0]
                            assert order_args.side == "SELL"
                            assert order_args.price == 0.54
    
    def test_slippage_validation_exceeds_tolerance(self):
        """Test that orders are skipped when slippage exceeds 5%"""
        test_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        with patch.dict(os.environ, {"MY_PRIVATE_KEY": test_key}):
            with patch('executor.ClobClient') as mock_client_class:
                with patch('asset_mapper.get_market_details') as mock_market:
                    with patch('builtins.open', create=True) as mock_open:
                        # Mock config file
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value.read.return_value = json.dumps({
                            "is_active": True,
                            "max_cap_usdc": 500.0,
                            "copy_ratio": 0.1,
                            "target_wallet": "0xtest"
                        })
                        mock_open.return_value = mock_file
                        
                        # Mock market details
                        mock_market.return_value = {
                            "question": "Test Market",
                            "outcome": "Yes",
                            "market_slug": "test"
                        }
                        
                        # Mock client with price that exceeds slippage
                        mock_client = Mock()
                        mock_client.get_order_book.return_value = {
                            "asks": [{"price": "0.60"}],  # 10% higher than target
                            "bids": [{"price": "0.54"}]
                        }
                        mock_client_class.return_value = mock_client
                        
                        with patch('executor.log_trade_to_db') as mock_log:
                            execute_copy_trade(12345, "BUY", target_price=0.55)
                            
                            # Verify order was NOT created
                            mock_client.create_and_post_order.assert_not_called()
                            
                            # Verify failed trade was logged
                            mock_log.assert_called_once()
                            # Check positional arguments (status is the 6th argument, index 5)
                            assert mock_log.call_args[0][5] == "FAILED"
    
    def test_slippage_validation_within_tolerance(self):
        """Test that orders proceed when slippage is within 5%"""
        test_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        with patch.dict(os.environ, {"MY_PRIVATE_KEY": test_key}):
            with patch('executor.ClobClient') as mock_client_class:
                with patch('asset_mapper.get_market_details') as mock_market:
                    with patch('builtins.open', create=True) as mock_open:
                        # Mock config file
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value.read.return_value = json.dumps({
                            "is_active": True,
                            "max_cap_usdc": 500.0,
                            "copy_ratio": 0.1,
                            "target_wallet": "0xtest"
                        })
                        mock_open.return_value = mock_file
                        
                        # Mock market details
                        mock_market.return_value = {
                            "question": "Test Market",
                            "outcome": "Yes",
                            "market_slug": "test"
                        }
                        
                        # Mock client with price within tolerance
                        mock_client = Mock()
                        mock_client.get_order_book.return_value = {
                            "asks": [{"price": "0.56"}],  # ~1.8% higher than target
                            "bids": [{"price": "0.54"}]
                        }
                        mock_client.create_and_post_order.return_value = {"success": True}
                        mock_client_class.return_value = mock_client
                        
                        with patch('executor.log_trade_to_db') as mock_log:
                            execute_copy_trade(12345, "BUY", target_price=0.55)
                            
                            # Verify order WAS created
                            mock_client.create_and_post_order.assert_called_once()
    
    def test_error_handling_order_failure(self):
        """Test that order failures are logged and don't crash"""
        test_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        with patch.dict(os.environ, {"MY_PRIVATE_KEY": test_key}):
            with patch('executor.ClobClient') as mock_client_class:
                with patch('asset_mapper.get_market_details') as mock_market:
                    with patch('builtins.open', create=True) as mock_open:
                        # Mock config file
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value.read.return_value = json.dumps({
                            "is_active": True,
                            "max_cap_usdc": 500.0,
                            "copy_ratio": 0.1,
                            "target_wallet": "0xtest"
                        })
                        mock_open.return_value = mock_file
                        
                        # Mock market details
                        mock_market.return_value = {
                            "question": "Test Market",
                            "outcome": "Yes",
                            "market_slug": "test"
                        }
                        
                        # Mock client that raises exception
                        mock_client = Mock()
                        mock_client.get_order_book.return_value = {
                            "asks": [{"price": "0.55"}],
                            "bids": [{"price": "0.54"}]
                        }
                        mock_client.create_and_post_order.side_effect = Exception("Order rejected")
                        mock_client_class.return_value = mock_client
                        
                        with patch('executor.log_trade_to_db') as mock_log:
                            # Should not raise exception
                            execute_copy_trade(12345, "BUY")
                            
                            # Verify failed trade was logged
                            mock_log.assert_called()
                            # Find the call with FAILED status (status is 6th arg, index 5)
                            failed_calls = [call for call in mock_log.call_args_list 
                                          if len(call[0]) > 5 and call[0][5] == "FAILED"]
                            assert len(failed_calls) > 0
    
    def test_error_handling_no_orderbook(self):
        """Test handling when orderbook has no asks/bids"""
        test_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        with patch.dict(os.environ, {"MY_PRIVATE_KEY": test_key}):
            with patch('executor.ClobClient') as mock_client_class:
                with patch('asset_mapper.get_market_details') as mock_market:
                    with patch('builtins.open', create=True) as mock_open:
                        # Mock config file
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value.read.return_value = json.dumps({
                            "is_active": True,
                            "max_cap_usdc": 500.0,
                            "copy_ratio": 0.1,
                            "target_wallet": "0xtest"
                        })
                        mock_open.return_value = mock_file
                        
                        # Mock market details
                        mock_market.return_value = {
                            "question": "Test Market",
                            "outcome": "Yes",
                            "market_slug": "test"
                        }
                        
                        # Mock client with empty orderbook
                        mock_client = Mock()
                        mock_client.get_order_book.return_value = {
                            "asks": [],
                            "bids": []
                        }
                        mock_client_class.return_value = mock_client
                        
                        with patch('executor.log_trade_to_db') as mock_log:
                            execute_copy_trade(12345, "BUY")
                            
                            # Verify order was NOT created
                            mock_client.create_and_post_order.assert_not_called()
                            
                            # Verify failed trade was logged
                            mock_log.assert_called_once()
                            # Check positional arguments (status is the 6th argument, index 5)
                            assert mock_log.call_args[0][5] == "FAILED"
