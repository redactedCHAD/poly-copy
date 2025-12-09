"""
Unit tests for asset_mapper module

Tests API response parsing, timeout handling, error handling, and cache behavior.
"""

import pytest
import requests
from unittest.mock import patch, Mock
from asset_mapper import get_market_details


class TestAssetMapper:
    """Test suite for asset_mapper module"""
    
    def setup_method(self):
        """Clear cache before each test"""
        get_market_details.cache_clear()
    
    def test_api_response_parsing_with_sample_data(self):
        """Test that API response is correctly parsed to extract question, outcome, and market_slug"""
        # Sample API response matching Polymarket's structure
        sample_response = [
            {
                "question": "Will Trump win the 2024 election?",
                "slug": "trump-2024-election",
                "tokens": [
                    {
                        "token_id": "12345",
                        "outcome": "Yes",
                        "price": "0.55"
                    },
                    {
                        "token_id": "12346",
                        "outcome": "No",
                        "price": "0.45"
                    }
                ]
            }
        ]
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = sample_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = get_market_details(12345)
            
            assert result["question"] == "Will Trump win the 2024 election?"
            assert result["outcome"] == "Yes"
            assert result["market_slug"] == "trump-2024-election"
            
            # Verify API was called with correct parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["clob_token_ids_in"] == "12345"
            assert call_args[1]["timeout"] == 5
    
    def test_token_matching_with_multiple_tokens(self):
        """Test that correct token is matched when response contains multiple tokens"""
        sample_response = [
            {
                "question": "Will it rain tomorrow?",
                "slug": "rain-tomorrow",
                "tokens": [
                    {
                        "token_id": "99999",
                        "outcome": "Yes"
                    },
                    {
                        "token_id": "88888",
                        "outcome": "No"
                    }
                ]
            }
        ]
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = sample_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Query for the "No" token
            result = get_market_details(88888)
            
            assert result["outcome"] == "No"
            assert result["question"] == "Will it rain tomorrow?"
    
    def test_timeout_handling(self):
        """Test that timeout returns default values after 5 seconds"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout()
            
            result = get_market_details(12345)
            
            assert result["question"] == "Unknown"
            assert result["outcome"] == "Unknown"
            assert result["market_slug"] == ""
    
    def test_default_value_return_on_http_error(self):
        """Test that HTTP errors return default values"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.HTTPError()
            
            result = get_market_details(12345)
            
            assert result["question"] == "Unknown"
            assert result["outcome"] == "Unknown"
            assert result["market_slug"] == ""
    
    def test_default_value_return_on_network_error(self):
        """Test that network errors return default values"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()
            
            result = get_market_details(12345)
            
            assert result["question"] == "Unknown"
            assert result["outcome"] == "Unknown"
            assert result["market_slug"] == ""
    
    def test_default_value_return_on_empty_response(self):
        """Test that empty API response returns default values"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = get_market_details(12345)
            
            assert result["question"] == "Unknown"
            assert result["outcome"] == "Unknown"
            assert result["market_slug"] == ""
    
    def test_default_value_return_on_invalid_json(self):
        """Test that JSON parsing errors return default values"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = get_market_details(12345)
            
            assert result["question"] == "Unknown"
            assert result["outcome"] == "Unknown"
            assert result["market_slug"] == ""
    
    def test_default_value_return_on_missing_fields(self):
        """Test that missing fields in response use default values"""
        sample_response = [
            {
                # Missing question and slug
                "tokens": [
                    {
                        "token_id": "12345"
                        # Missing outcome
                    }
                ]
            }
        ]
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = sample_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = get_market_details(12345)
            
            assert result["question"] == "Unknown"
            assert result["outcome"] == "Unknown"
            assert result["market_slug"] == ""
    
    def test_cache_behavior(self):
        """Test that cache returns same result without making additional API calls"""
        sample_response = [
            {
                "question": "Test question",
                "slug": "test-slug",
                "tokens": [
                    {
                        "token_id": "12345",
                        "outcome": "Yes"
                    }
                ]
            }
        ]
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = sample_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # First call - should hit API
            result1 = get_market_details(12345)
            assert mock_get.call_count == 1
            
            # Second call - should use cache
            result2 = get_market_details(12345)
            assert mock_get.call_count == 1  # Still 1, not 2
            
            # Results should be identical
            assert result1 == result2
            assert result1["question"] == "Test question"
            assert result1["outcome"] == "Yes"
    
    def test_cache_different_token_ids(self):
        """Test that cache stores different results for different token IDs"""
        with patch('requests.get') as mock_get:
            def mock_response_factory(*args, **kwargs):
                token_id = kwargs["params"]["clob_token_ids_in"]
                mock_resp = Mock()
                mock_resp.json.return_value = [
                    {
                        "question": f"Question for {token_id}",
                        "slug": f"slug-{token_id}",
                        "tokens": [
                            {
                                "token_id": token_id,
                                "outcome": "Yes"
                            }
                        ]
                    }
                ]
                mock_resp.raise_for_status.return_value = None
                return mock_resp
            
            mock_get.side_effect = mock_response_factory
            
            # Call with different token IDs
            result1 = get_market_details(11111)
            result2 = get_market_details(22222)
            
            # Should have made 2 API calls
            assert mock_get.call_count == 2
            
            # Results should be different
            assert result1["question"] == "Question for 11111"
            assert result2["question"] == "Question for 22222"
            
            # Call again with same IDs - should use cache
            result1_cached = get_market_details(11111)
            result2_cached = get_market_details(22222)
            
            # Still only 2 API calls
            assert mock_get.call_count == 2
            
            # Results should match
            assert result1 == result1_cached
            assert result2 == result2_cached
