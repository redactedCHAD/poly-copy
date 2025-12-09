"""
Listener Module

Monitors the Polygon blockchain for OrderFilled events from the CTF Exchange contract.
Detects trades from the target wallet and triggers mirror trades via the executor.
"""

import os
import json
import time
from typing import Dict, Any
from dotenv import load_dotenv
from web3 import Web3
from colorama import Fore, Style, init as colorama_init

# Import other modules
from asset_mapper import get_market_details
from executor import execute_copy_trade

# Initialize colorama for colored console output
colorama_init(autoreset=True)

# Load environment variables
load_dotenv()

# Constants
RPC_URL = os.getenv("RPC_URL", "https://polygon-rpc.com")
TARGET_WALLET = None  # Will be loaded from config.json
CTF_EXCHANGE_ADDR = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"

# CTF Exchange ABI - OrderFilled event structure
CTF_EXCHANGE_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "orderHash", "type": "bytes32"},
            {"indexed": True, "name": "maker", "type": "address"},
            {"indexed": True, "name": "taker", "type": "address"},
            {"indexed": False, "name": "makerAssetId", "type": "uint256"},
            {"indexed": False, "name": "takerAssetId", "type": "uint256"},
            {"indexed": False, "name": "makerAmountFilled", "type": "uint256"},
            {"indexed": False, "name": "takerAmountFilled", "type": "uint256"},
            {"indexed": False, "name": "fee", "type": "uint256"}
        ],
        "name": "OrderFilled",
        "type": "event"
    }
]


def process_event(event_args: Dict[str, Any], config: Dict[str, Any]) -> None:
    """
    Analyze OrderFilled event to determine trade direction and execute mirror trade.
    
    Args:
        event_args: Event arguments from OrderFilled event
        config: Configuration dictionary with bot settings
        
    Logic:
    - Determine if target wallet is maker or taker
    - Classify as BUY or SELL based on asset IDs
    - Calculate filled price from amounts
    - Get human-readable market info
    - Execute mirror trade if bot is active
    
    Exception handling ensures that errors in processing one event don't stop
    monitoring of subsequent events.
    """
    try:
        target_wallet = config.get("target_wallet", "").lower()
        maker = event_args.get("maker", "").lower()
        taker = event_args.get("taker", "").lower()
        maker_asset_id = event_args.get("makerAssetId", 0)
        taker_asset_id = event_args.get("takerAssetId", 0)
        maker_amount = event_args.get("makerAmountFilled", 0)
        taker_amount = event_args.get("takerAmountFilled", 0)
        
        # Determine if target wallet is involved
        is_maker = (maker == target_wallet)
        is_taker = (taker == target_wallet)
        
        if not (is_maker or is_taker):
            return  # Not our target wallet
        
        # Determine trade direction and token ID
        # 
        # Trade Direction Logic (Requirement 2.1-2.4):
        # Asset ID 0 = USDC (the collateral token)
        # Asset ID > 0 = Outcome token (e.g., "Yes" or "No" on a market)
        #
        # BUY: Target wallet gives USDC, receives outcome tokens
        # SELL: Target wallet gives outcome tokens, receives USDC
        #
        # The OrderFilled event structure:
        # - maker: The address that created the order
        # - taker: The address that filled the order
        # - makerAssetId: The asset the maker is giving
        # - takerAssetId: The asset the taker is giving (maker receives this)
        # - makerAmountFilled: Amount of makerAssetId transferred
        # - takerAmountFilled: Amount of takerAssetId transferred
        
        action = None
        token_id = None
        usdc_amount = 0
        token_amount = 0
        
        if is_maker:
            # Target wallet is the maker (created the order)
            if maker_asset_id == 0:
                # Maker giving USDC (asset 0) -> Buying outcome tokens
                action = "BUY"
                token_id = taker_asset_id  # The outcome token being bought
                usdc_amount = maker_amount  # USDC spent
                token_amount = taker_amount  # Tokens received
            else:
                # Maker giving tokens (asset > 0) -> Selling outcome tokens
                action = "SELL"
                token_id = maker_asset_id  # The outcome token being sold
                usdc_amount = taker_amount  # USDC received
                token_amount = maker_amount  # Tokens sold
        else:  # is_taker
            # Target wallet is the taker (filled someone else's order)
            if taker_asset_id == 0:
                # Taker giving USDC (asset 0) -> Buying outcome tokens
                action = "BUY"
                token_id = maker_asset_id  # The outcome token being bought
                usdc_amount = taker_amount  # USDC spent
                token_amount = maker_amount  # Tokens received
            else:
                # Taker giving tokens (asset > 0) -> Selling outcome tokens
                action = "SELL"
                token_id = taker_asset_id  # The outcome token being sold
                usdc_amount = maker_amount  # USDC received
                token_amount = taker_amount  # Tokens sold
        
        # Calculate filled price (USDC amount / token amount)
        # 
        # Price Calculation (Requirement 2.5):
        # Polymarket prices are between 0 and 1 (representing probability)
        # Price = USDC spent / Tokens received
        # 
        # Example: If you spend 52.34 USDC to buy 100 tokens
        # Price = 52.34 / 100 = 0.5234 (52.34% probability)
        #
        # Both USDC and outcome tokens use 6 decimals on Polygon
        # Raw amounts need to be divided by 1e6 to get human-readable values
        usdc_human = usdc_amount / 1e6
        token_human = token_amount / 1e6
        
        if token_amount > 0:
            filled_price = usdc_human / token_human
        else:
            # Avoid division by zero (shouldn't happen in valid trades)
            filled_price = 0
        
        # Get market details
        market_info = get_market_details(token_id)
        market_name = market_info["question"]
        outcome = market_info["outcome"]
        
        # Display trade detection with color
        role = "MAKER" if is_maker else "TAKER"
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}🎯 TARGET WALLET TRADE DETECTED")
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.WHITE}Role:     {Fore.GREEN}{role}")
        print(f"{Fore.WHITE}Action:   {Fore.MAGENTA}{action}")
        print(f"{Fore.WHITE}Market:   {Fore.BLUE}{market_name}")
        print(f"{Fore.WHITE}Outcome:  {Fore.BLUE}{outcome}")
        print(f"{Fore.WHITE}Price:    {Fore.YELLOW}{filled_price:.4f}")
        print(f"{Fore.WHITE}Size:     {Fore.YELLOW}{usdc_human:.2f} USDC")
        print(f"{Fore.WHITE}Token ID: {Fore.WHITE}{token_id}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        # Check if bot is active
        if not config.get("is_active", False):
            print(f"{Fore.RED}⏸️  Bot is INACTIVE - skipping trade{Style.RESET_ALL}")
            return
        
        # Execute mirror trade
        print(f"{Fore.GREEN}🚀 Executing mirror trade...{Style.RESET_ALL}")
        execute_copy_trade(token_id, action, filled_price)
        
    except Exception as e:
        # Log exception but continue to next event
        print(f"\n{Fore.RED}❌ Error processing event: {e}")
        print(f"{Fore.YELLOW}⚠️  Continuing to monitor for next event...{Style.RESET_ALL}\n")
        import traceback
        traceback.print_exc()


def start_listener() -> None:
    """
    Main loop that connects to Polygon RPC and polls for new blocks.
    Filters OrderFilled events from CTF Exchange contract.
    
    Polls every 2 seconds for new blocks.
    Retries connection after 5 seconds on failure.
    """
    global TARGET_WALLET
    
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}🎧 PolyMirror Listener Starting...")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Load configuration
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        TARGET_WALLET = config.get("target_wallet", "").lower()
        print(f"{Fore.GREEN}✓ Configuration loaded")
        print(f"{Fore.WHITE}  Target Wallet: {Fore.YELLOW}{TARGET_WALLET}")
        print(f"{Fore.WHITE}  Bot Active:    {Fore.YELLOW}{config.get('is_active', False)}")
        print(f"{Fore.WHITE}  Copy Ratio:    {Fore.YELLOW}{config.get('copy_ratio', 0.1)}")
        print(f"{Fore.WHITE}  Max Cap:       {Fore.YELLOW}{config.get('max_cap_usdc', 500)} USDC{Style.RESET_ALL}\n")
    except Exception as e:
        print(f"{Fore.RED}❌ Failed to load config.json: {e}{Style.RESET_ALL}")
        return
    
    # Establish Web3 connection
    w3 = None
    while w3 is None:
        try:
            print(f"{Fore.WHITE}Connecting to Polygon RPC: {Fore.CYAN}{RPC_URL}{Style.RESET_ALL}")
            w3 = Web3(Web3.HTTPProvider(RPC_URL))
            
            if not w3.is_connected():
                raise ConnectionError("Failed to connect to RPC")
            
            print(f"{Fore.GREEN}✓ Connected to Polygon network")
            print(f"{Fore.WHITE}  Chain ID: {Fore.YELLOW}{w3.eth.chain_id}")
            print(f"{Fore.WHITE}  Latest Block: {Fore.YELLOW}{w3.eth.block_number}{Style.RESET_ALL}\n")
            
        except Exception as e:
            print(f"{Fore.RED}❌ Connection error: {e}")
            print(f"{Fore.YELLOW}⏳ Retrying in 5 seconds...{Style.RESET_ALL}\n")
            time.sleep(5)
            w3 = None
    
    # Get contract instance
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CTF_EXCHANGE_ADDR),
        abi=CTF_EXCHANGE_ABI
    )
    
    print(f"{Fore.GREEN}✓ CTF Exchange contract loaded")
    print(f"{Fore.WHITE}  Address: {Fore.CYAN}{CTF_EXCHANGE_ADDR}{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.GREEN}🎧 Listener is now ACTIVE - monitoring for trades...")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Track last processed block
    last_block = w3.eth.block_number
    
    # Main polling loop
    while True:
        try:
            # Reload config on each iteration to pick up changes
            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
            except FileNotFoundError:
                print(f"{Fore.RED}❌ config.json not found - using defaults{Style.RESET_ALL}")
                config = {"is_active": False, "target_wallet": TARGET_WALLET}
            except json.JSONDecodeError as e:
                print(f"{Fore.RED}❌ Invalid JSON in config.json: {e}{Style.RESET_ALL}")
                config = {"is_active": False, "target_wallet": TARGET_WALLET}
            
            # Check connection before querying
            if not w3.is_connected():
                raise ConnectionError("RPC connection lost")
            
            # Get current block
            current_block = w3.eth.block_number
            
            # Check if there are new blocks
            if current_block > last_block:
                # Query for OrderFilled events in the new block range
                from_block = last_block + 1
                to_block = current_block
                
                print(f"{Fore.WHITE}📦 Scanning blocks {from_block} to {to_block}...{Style.RESET_ALL}", end="\r")
                
                # Get events
                events = contract.events.OrderFilled.get_logs(
                    from_block=from_block,
                    to_block=to_block
                )
                
                # Process each event
                for event in events:
                    try:
                        event_args = dict(event['args'])
                        process_event(event_args, config)
                    except Exception as event_error:
                        # Log error but continue to next event
                        print(f"\n{Fore.RED}❌ Error processing event: {event_error}{Style.RESET_ALL}")
                        continue
                
                # Update last processed block
                last_block = current_block
            
            # Poll every 2 seconds
            time.sleep(2)
            
        except ConnectionError as e:
            print(f"\n{Fore.RED}❌ Connection error: {e}")
            print(f"{Fore.YELLOW}⏳ Waiting 5 seconds before retry...{Style.RESET_ALL}\n")
            time.sleep(5)
            
            # Try to reconnect
            try:
                print(f"{Fore.YELLOW}🔄 Reconnecting to RPC...{Style.RESET_ALL}")
                w3 = Web3(Web3.HTTPProvider(RPC_URL))
                if w3.is_connected():
                    print(f"{Fore.GREEN}✓ Reconnected successfully{Style.RESET_ALL}\n")
                    contract = w3.eth.contract(
                        address=Web3.to_checksum_address(CTF_EXCHANGE_ADDR),
                        abi=CTF_EXCHANGE_ABI
                    )
                    # Update last_block to current to avoid reprocessing
                    last_block = w3.eth.block_number
                else:
                    print(f"{Fore.RED}❌ Reconnection failed - will retry{Style.RESET_ALL}\n")
            except Exception as reconnect_error:
                print(f"{Fore.RED}❌ Reconnection failed: {reconnect_error}{Style.RESET_ALL}\n")
                
        except Exception as e:
            print(f"\n{Fore.RED}❌ Polling error: {e}")
            print(f"{Fore.YELLOW}⏳ Waiting 5 seconds before retry...{Style.RESET_ALL}\n")
            time.sleep(5)
            
            # Try to reconnect if connection lost
            try:
                if not w3.is_connected():
                    print(f"{Fore.YELLOW}🔄 Reconnecting to RPC...{Style.RESET_ALL}")
                    w3 = Web3(Web3.HTTPProvider(RPC_URL))
                    if w3.is_connected():
                        print(f"{Fore.GREEN}✓ Reconnected successfully{Style.RESET_ALL}\n")
                        contract = w3.eth.contract(
                            address=Web3.to_checksum_address(CTF_EXCHANGE_ADDR),
                            abi=CTF_EXCHANGE_ABI
                        )
                        # Update last_block to current to avoid reprocessing
                        last_block = w3.eth.block_number
            except Exception as reconnect_error:
                print(f"{Fore.RED}❌ Reconnection failed: {reconnect_error}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    start_listener()
