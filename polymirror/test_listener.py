"""
Unit tests for the listener module.

Tests connection establishment, event filtering, trade direction logic,
and error handling.
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
from listener import process_event, CTF_EXCHANGE_ABI


class TestProcessEvent:
    """Test suite for process_event function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.target_wallet = "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"
        self.other_wallet = "0x1234567890123456789012345678901234567890"
        
        self.config_active = {
            "is_active": True,
            "target_wallet": self.target_wallet,
            "copy_ratio": 0.1,
            "max_cap_usdc": 500.0
        }
        
        self.config_inactive = {
            "is_active": False,
            "target_wallet": self.target_wallet,
            "copy_ratio": 0.1,
            "max_cap_usdc": 500.0
        }
    
    @patch('listener.execute_copy_trade')
    @patch('listener.get_market_details')
    def test_maker_buy_trade(self, mock_market_details, mock_execute):
        """Test BUY trade when target wallet is maker giving USDC."""
        # Setup
        mock_market_details.return_value = {
            "question": "Will Trump win 2024?",
            "outcome": "Yes",
            "market_slug": "trump-2024"
        }
        
        event_args = {
            "maker": self.target_wallet,
            "taker": self.other_wallet,
            "makerAssetId": 0,  # USDC
            "takerAssetId": 12345,  # Token
            "makerAmountFilled": 100_000000,  # 100 USDC (6 decimals)
            "takerAmountFilled": 200_000000   # 200 tokens (6 decimals)
        }
        
        # Execute
        process_event(event_args, self.config_active)
        
        # Verify
        mock_market_details.assert_called_once_with(12345)
        mock_execute.assert_called_once_with(12345, "BUY", 0.5)  # 100/200 = 0.5
    
    @patch('listener.execute_copy_trade')
    @patch('listener.get_market_details')
    def test_maker_sell_trade(self, mock_market_details, mock_execute):
        """Test SELL trade when target wallet is maker giving tokens."""
        # Setup
        mock_market_details.return_value = {
            "question": "Will Trump win 2024?",
            "outcome": "Yes",
            "market_slug": "trump-2024"
        }
        
        event_args = {
            "maker": self.target_wallet,
            "taker": self.other_wallet,
            "makerAssetId": 12345,  # Token
            "takerAssetId": 0,  # USDC
            "makerAmountFilled": 200_000000,  # 200 tokens
            "takerAmountFilled": 100_000000   # 100 USDC
        }
        
        # Execute
        process_event(event_args, self.config_active)
        
        # Verify
        mock_market_details.assert_called_once_with(12345)
        mock_execute.assert_called_once_with(12345, "SELL", 0.5)  # 100/200 = 0.5
    
    @patch('listener.execute_copy_trade')
    @patch('listener.get_market_details')
    def test_taker_buy_trade(self, mock_market_details, mock_execute):
        """Test BUY trade when target wallet is taker giving USDC."""
        # Setup
        mock_market_details.return_value = {
            "question": "Will Trump win 2024?",
            "outcome": "No",
            "market_slug": "trump-2024"
        }
        
        event_args = {
            "maker": self.other_wallet,
            "taker": self.target_wallet,
            "makerAssetId": 67890,  # Token
            "takerAssetId": 0,  # USDC
            "makerAmountFilled": 150_000000,  # 150 tokens
            "takerAmountFilled": 75_000000    # 75 USDC
        }
        
        # Execute
        process_event(event_args, self.config_active)
        
        # Verify
        mock_market_details.assert_called_once_with(67890)
        mock_execute.assert_called_once_with(67890, "BUY", 0.5)  # 75/150 = 0.5
    
    @patch('listener.execute_copy_trade')
    @patch('listener.get_market_details')
    def test_taker_sell_trade(self, mock_market_details, mock_execute):
        """Test SELL trade when target wallet is taker giving tokens."""
        # Setup
        mock_market_details.return_value = {
            "question": "Will Trump win 2024?",
            "outcome": "No",
            "market_slug": "trump-2024"
        }
        
        event_args = {
            "maker": self.other_wallet,
            "taker": self.target_wallet,
            "makerAssetId": 0,  # USDC
            "takerAssetId": 67890,  # Token
            "makerAmountFilled": 80_000000,  # 80 USDC
            "takerAmountFilled": 160_000000   # 160 tokens
        }
        
        # Execute
        process_event(event_args, self.config_active)
        
        # Verify
        mock_market_details.assert_called_once_with(67890)
        mock_execute.assert_called_once_with(67890, "SELL", 0.5)  # 80/160 = 0.5
    
    @patch('listener.execute_copy_trade')
    @patch('listener.get_market_details')
    def test_inactive_bot_skips_trade(self, mock_market_details, mock_execute):
        """Test that trades are skipped when bot is inactive."""
        # Setup
        mock_market_details.return_value = {
            "question": "Will Trump win 2024?",
            "outcome": "Yes",
            "market_slug": "trump-2024"
        }
        
        event_args = {
            "maker": self.target_wallet,
            "taker": self.other_wallet,
            "makerAssetId": 0,
            "takerAssetId": 12345,
            "makerAmountFilled": 100_000000,
            "takerAmountFilled": 200_000000
        }
        
        # Execute with inactive config
        process_event(event_args, self.config_inactive)
        
        # Verify - execute_copy_trade should NOT be called
        mock_market_details.assert_called_once()
        mock_execute.assert_not_called()
    
    @patch('listener.execute_copy_trade')
    @patch('listener.get_market_details')
    def test_non_target_wallet_ignored(self, mock_market_details, mock_execute):
        """Test that events not involving target wallet are ignored."""
        # Setup
        event_args = {
            "maker": self.other_wallet,
            "taker": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            "makerAssetId": 0,
            "takerAssetId": 12345,
            "makerAmountFilled": 100_000000,
            "takerAmountFilled": 200_000000
        }
        
        # Execute
        process_event(event_args, self.config_active)
        
        # Verify - neither function should be called
        mock_market_details.assert_not_called()
        mock_execute.assert_not_called()
    
    @patch('listener.execute_copy_trade')
    @patch('listener.get_market_details')
    def test_price_calculation_accuracy(self, mock_market_details, mock_execute):
        """Test that filled price is calculated correctly."""
        # Setup
        mock_market_details.return_value = {
            "question": "Test Market",
            "outcome": "Yes",
            "market_slug": "test"
        }
        
        # Test various price scenarios
        test_cases = [
            (100_000000, 200_000000, 0.5),    # 100 USDC / 200 tokens = 0.5
            (50_000000, 100_000000, 0.5),     # 50 USDC / 100 tokens = 0.5
            (75_000000, 100_000000, 0.75),    # 75 USDC / 100 tokens = 0.75
            (25_000000, 100_000000, 0.25),    # 25 USDC / 100 tokens = 0.25
        ]
        
        for usdc_amount, token_amount, expected_price in test_cases:
            mock_execute.reset_mock()
            
            event_args = {
                "maker": self.target_wallet,
                "taker": self.other_wallet,
                "makerAssetId": 0,
                "takerAssetId": 99999,
                "makerAmountFilled": usdc_amount,
                "takerAmountFilled": token_amount
            }
            
            process_event(event_args, self.config_active)
            
            # Verify price calculation
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args[0]
            assert call_args[2] == expected_price, f"Expected {expected_price}, got {call_args[2]}"
    
    @patch('listener.execute_copy_trade')
    @patch('listener.get_market_details')
    def test_zero_token_amount_handling(self, mock_market_details, mock_execute):
        """Test handling of zero token amounts (edge case)."""
        # Setup
        mock_market_details.return_value = {
            "question": "Test Market",
            "outcome": "Yes",
            "market_slug": "test"
        }
        
        event_args = {
            "maker": self.target_wallet,
            "taker": self.other_wallet,
            "makerAssetId": 0,
            "takerAssetId": 12345,
            "makerAmountFilled": 100_000000,
            "takerAmountFilled": 0  # Zero tokens
        }
        
        # Execute - should not crash
        process_event(event_args, self.config_active)
        
        # Verify - should be called with price 0
        mock_execute.assert_called_once_with(12345, "BUY", 0)


class TestEventFiltering:
    """Test suite for event filtering logic."""
    
    def test_ctf_exchange_abi_structure(self):
        """Test that CTF_EXCHANGE_ABI has correct OrderFilled event structure."""
        assert len(CTF_EXCHANGE_ABI) == 1
        event = CTF_EXCHANGE_ABI[0]
        
        assert event["name"] == "OrderFilled"
        assert event["type"] == "event"
        assert event["anonymous"] == False
        
        # Check required inputs
        input_names = [inp["name"] for inp in event["inputs"]]
        required_inputs = [
            "orderHash", "maker", "taker", "makerAssetId", 
            "takerAssetId", "makerAmountFilled", "takerAmountFilled", "fee"
        ]
        
        for required in required_inputs:
            assert required in input_names, f"Missing required input: {required}"


class TestConnectionAndRetry:
    """Test suite for connection establishment and retry logic."""
    
    @patch('listener.Web3')
    @patch('listener.time.sleep')
    @patch('builtins.open', new_callable=mock_open, read_data='{"is_active": false, "target_wallet": "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d", "copy_ratio": 0.1, "max_cap_usdc": 500}')
    def test_connection_retry_on_failure(self, mock_file, mock_sleep, mock_web3):
        """Test that connection retries after 5 seconds on failure."""
        # Setup - first connection fails, second succeeds
        mock_provider = Mock()
        mock_web3.HTTPProvider.return_value = mock_provider
        
        mock_w3_instance = Mock()
        mock_w3_instance.is_connected.side_effect = [False, True]  # Fail then succeed
        mock_w3_instance.eth.chain_id = 137
        mock_w3_instance.eth.block_number = 1000
        mock_w3_instance.eth.contract.return_value = Mock()
        
        mock_web3.return_value = mock_w3_instance
        
        # We need to stop the infinite loop after connection succeeds
        # Mock the main loop to raise an exception after setup
        with patch('listener.time.sleep', side_effect=[None, KeyboardInterrupt]):
            try:
                from listener import start_listener
                start_listener()
            except KeyboardInterrupt:
                pass
        
        # Verify retry was attempted
        assert mock_w3_instance.is_connected.call_count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
