"""
Asset Mapper Module

Translates blockchain token IDs to human-readable market information
using Polymarket's Gamma API.
"""

import requests
from functools import lru_cache
from typing import Dict


@lru_cache(maxsize=100)
def get_market_details(asset_id_int: int) -> Dict[str, str]:
    """
    Queries Polymarket Gamma API to get market metadata for a token ID.
    
    Args:
        asset_id_int: The token ID to look up
        
    Returns:
        Dictionary containing:
        - question: The market question (e.g., "Will Trump win 2024?")
        - outcome: The outcome label (e.g., "Yes" or "No")
        - market_slug: URL-friendly identifier
        
    Uses LRU cache to avoid redundant API calls.
    Handles API errors and timeouts with default return values.
    
    Error Handling:
    - Timeout after 5 seconds (Requirement 8.2)
    - Returns default values on any API failure
    - Logs errors for debugging
    """
    # Default return value for errors
    default_response = {
        "question": "Unknown",
        "outcome": "Unknown",
        "market_slug": ""
    }
    
    try:
        # Query Gamma API with token ID
        url = "https://gamma-api.polymarket.com/markets"
        params = {"clob_token_ids_in": str(asset_id_int)}
        
        # 5 second timeout as specified in requirements (8.2)
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        # Handle empty response
        if not data or len(data) == 0:
            print(f"⚠️  Gamma API returned empty response for token {asset_id_int}")
            return default_response
        
        # Get first market (should only be one for specific token ID)
        market = data[0]
        
        # Extract question and market_slug
        question = market.get("question", "Unknown")
        market_slug = market.get("slug", "")
        
        # Find the matching token in the tokens array
        #
        # Token Matching Logic (Requirement 3.5):
        # Gamma API returns a market with multiple tokens (usually 2: Yes/No)
        # We need to find which token matches our queried token_id
        #
        # Example response:
        # {
        #   "question": "Will Trump win 2024?",
        #   "tokens": [
        #     {"token_id": "123456", "outcome": "Yes"},
        #     {"token_id": "123457", "outcome": "No"}
        #   ]
        # }
        #
        # If we queried token_id 123456, we should return outcome "Yes"
        tokens = market.get("tokens", [])
        outcome = "Unknown"
        
        # Match token ID to get outcome label
        for token in tokens:
            token_id_str = token.get("token_id", "")
            if token_id_str == str(asset_id_int):
                outcome = token.get("outcome", "Unknown")
                break
        
        return {
            "question": question,
            "outcome": outcome,
            "market_slug": market_slug
        }
        
    except requests.exceptions.Timeout:
        # Handle timeout - return default values (Requirement 8.2)
        print(f"⚠️  Gamma API timeout (5s) for token {asset_id_int} - using defaults")
        return default_response
    except requests.exceptions.HTTPError as e:
        # Handle HTTP errors (4xx, 5xx)
        status_code = e.response.status_code if e.response else "unknown"
        print(f"⚠️  Gamma API HTTP error for token {asset_id_int}: {status_code}")
        return default_response
    except requests.exceptions.ConnectionError as e:
        # Handle network connection errors
        print(f"⚠️  Gamma API connection error for token {asset_id_int}: {e}")
        return default_response
    except requests.exceptions.RequestException as e:
        # Handle other request errors
        print(f"⚠️  Gamma API request error for token {asset_id_int}: {e}")
        return default_response
    except (ValueError, KeyError, IndexError) as e:
        # Handle JSON parsing errors or missing fields
        print(f"⚠️  Gamma API parsing error for token {asset_id_int}: {e}")
        return default_response
    except Exception as e:
        # Catch-all for any other unexpected errors
        print(f"⚠️  Unexpected error in get_market_details for token {asset_id_int}: {e}")
        return default_response
