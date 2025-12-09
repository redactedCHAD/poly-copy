"""
Executor Module

Places mirror trades on Polymarket using the py-clob-client library.
Handles order construction, slippage validation, and trade logging.
"""

import os
import json
import sqlite3
import time
from typing import Optional
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs

# Load environment variables
load_dotenv()


def get_client() -> ClobClient:
    """
    Initialize ClobClient with private key and derive API credentials.
    
    Returns:
        ClobClient: Initialized client for Polymarket CLOB API
        
    Raises:
        ValueError: If MY_PRIVATE_KEY environment variable is not set
    """
    private_key = os.getenv("MY_PRIVATE_KEY")
    
    if not private_key:
        raise ValueError("MY_PRIVATE_KEY environment variable is required")
    
    # Check if API credentials are provided in environment
    api_key = os.getenv("POLY_API_KEY")
    api_secret = os.getenv("POLY_API_SECRET")
    api_passphrase = os.getenv("POLY_API_PASSPHRASE")
    
    # Initialize client - will derive credentials from private key if not provided
    if api_key and api_secret and api_passphrase:
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=private_key,
            chain_id=137,  # Polygon mainnet
            creds={
                "api_key": api_key,
                "api_secret": api_secret,
                "api_passphrase": api_passphrase
            }
        )
    else:
        # Derive credentials from private key
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=private_key,
            chain_id=137
        )
    
    return client


def log_trade_to_db(
    market_name: str,
    outcome: str,
    side: str,
    size: float,
    price: float,
    status: str
) -> None:
    """
    Insert trade record into SQLite database.
    
    Args:
        market_name: Human-readable market question
        outcome: Outcome label (e.g., "Yes" or "No")
        side: Trade direction ("BUY" or "SELL")
        size: Trade size in USDC
        price: Entry price (0.0-1.0)
        status: Trade status ("SUCCESS" or "FAILED")
        
    Error Handling:
    - Catches all database errors without crashing (Requirement 6.5)
    - Logs errors for debugging
    - Ensures connection is closed even on error
    """
    conn = None
    try:
        conn = sqlite3.connect("trades.db", timeout=10)
        cursor = conn.cursor()
        
        # Insert trade record with current Unix timestamp
        cursor.execute("""
            INSERT INTO trades (timestamp, market, outcome, side, size_usdc, price, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (time.time(), market_name, outcome, side, size, price, status))
        
        conn.commit()
        
    except sqlite3.OperationalError as e:
        # Handle database locked or other operational errors
        print(f"❌ Database operational error: {e}")
        print(f"   Trade details: {side} {size:.2f} USDC of {outcome} @ {price:.4f} - {status}")
    except sqlite3.IntegrityError as e:
        # Handle constraint violations
        print(f"❌ Database integrity error: {e}")
        print(f"   Trade details: {side} {size:.2f} USDC of {outcome} @ {price:.4f} - {status}")
    except sqlite3.DatabaseError as e:
        # Handle other database errors
        print(f"❌ Database error: {e}")
        print(f"   Trade details: {side} {size:.2f} USDC of {outcome} @ {price:.4f} - {status}")
    except Exception as e:
        # Catch-all for any other errors
        print(f"❌ Unexpected database write error: {e}")
        print(f"   Trade details: {side} {size:.2f} USDC of {outcome} @ {price:.4f} - {status}")
    finally:
        # Ensure connection is closed
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def execute_copy_trade(
    token_id: int,
    side: str,
    target_price: Optional[float] = None
) -> None:
    """
    Place a mirror trade on Polymarket with slippage protection.
    
    Args:
        token_id: The token ID to trade
        side: Trade direction ("BUY" or "SELL")
        target_price: Optional target price for slippage validation
        
    Steps:
    1. Load configuration
    2. Initialize CLOB client
    3. Fetch current orderbook price
    4. Validate slippage (5% default tolerance)
    5. Calculate trade size based on copy_ratio and max_cap
    6. Submit order
    7. Log result to database
    
    Error Handling:
    - Handles order failures without crashing (Requirement 8.3)
    - Logs all errors for debugging
    - Continues monitoring after failures
    """
    # Import asset_mapper here to avoid circular imports
    from asset_mapper import get_market_details
    
    # Load configuration
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ config.json not found - cannot execute trade")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config.json: {e}")
        return
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return
    
    # Get market details for logging
    market_info = get_market_details(token_id)
    market_name = market_info["question"]
    outcome = market_info["outcome"]
    
    try:
        # Initialize client
        try:
            client = get_client()
        except ValueError as e:
            print(f"❌ Client initialization failed: {e}")
            log_trade_to_db(market_name, outcome, side, 0, 0, "FAILED")
            return
        except Exception as e:
            print(f"❌ Unexpected error initializing client: {e}")
            log_trade_to_db(market_name, outcome, side, 0, 0, "FAILED")
            return
        
        # Fetch current orderbook price
        try:
            orderbook = client.get_order_book(token_id)
        except Exception as e:
            print(f"❌ Failed to fetch orderbook for token {token_id}: {e}")
            log_trade_to_db(market_name, outcome, side, 0, 0, "FAILED")
            return
        
        if side == "BUY":
            # For buying, we look at asks (sell orders)
            if not orderbook.asks or len(orderbook.asks) == 0:
                print(f"⚠️  No asks available for token {token_id}")
                log_trade_to_db(market_name, outcome, side, 0, 0, "FAILED")
                return
            try:
                current_price = float(orderbook.asks[0].price)
            except (AttributeError, ValueError, IndexError) as e:
                print(f"❌ Failed to parse ask price: {e}")
                log_trade_to_db(market_name, outcome, side, 0, 0, "FAILED")
                return
        else:  # SELL
            # For selling, we look at bids (buy orders)
            if not orderbook.bids or len(orderbook.bids) == 0:
                print(f"⚠️  No bids available for token {token_id}")
                log_trade_to_db(market_name, outcome, side, 0, 0, "FAILED")
                return
            try:
                current_price = float(orderbook.bids[0].price)
            except (AttributeError, ValueError, IndexError) as e:
                print(f"❌ Failed to parse bid price: {e}")
                log_trade_to_db(market_name, outcome, side, 0, 0, "FAILED")
                return
        
        # Slippage validation (5% default tolerance)
        # 
        # Slippage Protection (Requirement 4.3):
        # Prevents executing trades when price has moved significantly
        # from the target wallet's fill price.
        #
        # Example: Target wallet bought at 0.50, current price is 0.53
        # Slippage = |0.53 - 0.50| / 0.50 = 0.06 = 6%
        # If tolerance is 5%, this trade would be skipped
        #
        # This protects against:
        # - Front-running (price moved before we could execute)
        # - Low liquidity (large price impact)
        # - Market volatility (rapid price changes)
        if target_price is not None:
            slippage_tolerance = 0.05  # 5% default - can be adjusted
            try:
                price_diff = abs(current_price - target_price) / target_price
                
                if price_diff > slippage_tolerance:
                    print(f"⚠️  Slippage exceeded: Price moved from {target_price:.4f} to {current_price:.4f}")
                    log_trade_to_db(market_name, outcome, side, 0, current_price, "FAILED")
                    return
            except ZeroDivisionError:
                print(f"⚠️  Invalid target price (zero) - skipping slippage check")
        
        # Calculate trade size
        #
        # Trade Size Calculation (Requirement 5.5):
        # Size = min(target_wallet_size × copy_ratio, max_cap_usdc)
        #
        # Example: Target wallet trades 1000 USDC
        # - copy_ratio = 0.1 (10%)
        # - max_cap_usdc = 500
        # - Calculated: 1000 × 0.1 = 100 USDC
        # - Final: min(100, 500) = 100 USDC (under cap)
        #
        # Example 2: Target wallet trades 10000 USDC
        # - copy_ratio = 0.1 (10%)
        # - max_cap_usdc = 500
        # - Calculated: 10000 × 0.1 = 1000 USDC
        # - Final: min(1000, 500) = 500 USDC (capped)
        #
        # Note: In this implementation, we use max_cap as the base
        # In production, you would extract the actual trade size from the event
        try:
            copy_ratio = config.get("copy_ratio", 0.1)
            max_cap_usdc = config.get("max_cap_usdc", 500.0)
            
            # TODO: Extract actual trade size from event data
            # For now, use max_cap as the reference size
            base_size = max_cap_usdc / copy_ratio
            calculated_size = base_size * copy_ratio
            
            # Cap at max_cap_usdc to prevent oversized trades
            trade_size = min(calculated_size, max_cap_usdc)
            
            if trade_size <= 0:
                print(f"⚠️  Invalid trade size calculated: {trade_size}")
                log_trade_to_db(market_name, outcome, side, 0, current_price, "FAILED")
                return
        except Exception as e:
            print(f"❌ Error calculating trade size: {e}")
            log_trade_to_db(market_name, outcome, side, 0, current_price, "FAILED")
            return
        
        # Create OrderArgs
        try:
            order_args = OrderArgs(
                token_id=str(token_id),
                price=current_price,
                size=trade_size,
                side=side,
                fee_rate_bps=0,  # Default fee rate
                nonce=0  # Will be set by client
            )
        except Exception as e:
            print(f"❌ Failed to create order arguments: {e}")
            log_trade_to_db(market_name, outcome, side, trade_size, current_price, "FAILED")
            return
        
        # Submit order via client.create_and_post_order()
        try:
            order_result = client.create_and_post_order(order_args)
            
            # Log successful trade
            print(f"✅ Order placed: {side} {trade_size:.2f} USDC of {outcome} @ {current_price:.4f}")
            log_trade_to_db(market_name, outcome, side, trade_size, current_price, "SUCCESS")
            
        except Exception as e:
            # Handle order submission failures (Requirement 8.3)
            error_msg = str(e)
            print(f"❌ Order submission failed: {error_msg}")
            log_trade_to_db(market_name, outcome, side, trade_size, current_price, "FAILED")
            print(f"⚠️  Continuing to monitor for new trades...")
        
    except Exception as e:
        # Catch-all for any unexpected errors
        error_msg = str(e)
        print(f"❌ Unexpected error in execute_copy_trade: {error_msg}")
        
        # Log failed trade with available information
        price_for_log = target_price if target_price is not None else 0
        log_trade_to_db(market_name, outcome, side, 0, price_for_log, "FAILED")
        print(f"⚠️  Continuing to monitor for new trades...")
