Project PolyMirror: Full Setup Guide & Code
This guide provides the specific code and instructions to build the Listener (wallet tracker) and the Executor (copy trader) for the target wallet 0x6031....
Phase 1: Environment Setup
Before running the code, you must set up your environment to interact with the Polygon blockchain and Polymarket's API.
1. Install Python Dependencies
Open your terminal and install the required libraries.
pip install web3 py-clob-client python-dotenv colorama

 * web3: To read data from the Polygon blockchain.
 * py-clob-client: The official Polymarket library to place your own trades.
 * python-dotenv: To securely manage your private keys.
2. Get a Polygon RPC URL
You need a connection to the Polygon network.
 * Free Option: Use https://polygon-rpc.com (Good for testing, slow/unreliable for live trading).
 * Pro Option (Recommended): Sign up for Alchemy or Infura to get a private Polygon RPC URL (e.g., https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY).
3. Set Up Security (.env)
Create a file named .env in your project folder. Never share this file.
# Your Wallet's Private Key (The one that will copy the trades)
MY_PRIVATE_KEY=0x...
# Your RPC URL from Alchemy/Infura
RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY
# Polymarket API Credentials (for execution)
POLY_API_KEY=...
POLY_API_SECRET=...
POLY_API_PASSPHRASE=...

Phase 2: The Listener Code
This script connects to the Polygon blockchain and watches the CTF Exchange Contract for OrderFilled events. If it sees the target wallet (0x6031...) involved in a trade, it alerts you.
File: listener.py
import time
import json
import os
from web3 import Web3
from dotenv import load_dotenv
from colorama import Fore, Style, init

# Initialize color printing
init()

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
RPC_URL = os.getenv("RPC_URL", "https://polygon-rpc.com")
TARGET_WALLET = "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d".lower()
CTF_EXCHANGE_ADDR = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"

# Minimal ABI for the 'OrderFilled' event
# We only need the event definition to decode logs
CTF_EXCHANGE_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "orderHash", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "maker", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "taker", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "makerAssetId", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "takerAssetId", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "makerAmountFilled", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "takerAmountFilled", "type": "uint256"}
        ],
        "name": "OrderFilled",
        "type": "event"
    }
]

def start_listener():
    # Connect to Polygon
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print(f"{Fore.RED}Failed to connect to RPC!{Style.RESET_ALL}")
        return

    print(f"{Fore.GREEN}Connected to Polygon.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Watching Target: {TARGET_WALLET}{Style.RESET_ALL}")

    # Create contract object
    contract = w3.eth.contract(address=CTF_EXCHANGE_ADDR, abi=CTF_EXCHANGE_ABI)

    # Filter Setup
    # Note: filtering by topics is more efficient than fetching all logs
    # Topic0 = Event Signature hash
    # Topic1 = maker (indexed)
    # Topic2 = taker (indexed)
    
    event_signature_hash = w3.keccak(text="OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256)").hex()
    
    # We poll the latest block loop
    last_block = w3.eth.block_number
    
    while True:
        try:
            current_block = w3.eth.block_number
            if current_block > last_block:
                # Look for events in the new range
                print(f"Scanning blocks {last_block + 1} to {current_block}...", end="\r")
                
                events = contract.events.OrderFilled.get_logs(fromBlock=last_block + 1, toBlock=current_block)
                
                for event in events:
                    args = event['args']
                    maker = args['maker'].lower()
                    taker = args['taker'].lower()

                    if maker == TARGET_WALLET or taker == TARGET_WALLET:
                        handle_event(args, w3)

                last_block = current_block
            
            time.sleep(2) # Poll every 2 seconds
            
        except Exception as e:
            print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
            time.sleep(5)

def handle_event(args, w3):
    print(f"\n{Fore.CYAN}--- DETECTED ACTIVITY ---{Style.RESET_ALL}")
    
    # Logic to determine Buy vs Sell
    # Asset ID '0' usually represents USDC (Collateral)
    # If Maker gives USDC (Asset 0), they are BUYING a position.
    # If Maker gives a Long ID, they are SELLING a position.
    
    maker_asset = args['makerAssetId']
    taker_asset = args['takerAssetId']
    amount = args['makerAmountFilled'] / 10**6 # USDC has 6 decimals
    
    # Simple Heuristic for Output
    action = "UNKNOWN"
    if maker_asset == 0:
        action = "BUYING OUTCOME"
        size = amount
    else:
        action = "SELLING OUTCOME"
        size = args['takerAmountFilled'] / 10**6
        
    print(f"Action: {Fore.MAGENTA}{action}{Style.RESET_ALL}")
    print(f"Size: ${size:.2f} USDC")
    print(f"Tx Hash: {args['maker']}") # In a real app, grab the tx hash from event metadata
    
    # --- TRIGGER COPY TRADER HERE ---
    # execute_copy_trade(action, size)

if __name__ == "__main__":
    start_listener()

Phase 3: The Copy Trader Logic (Stub)
In the code above, there is a comment # trigger copy trader here. This is where you connect the execution logic.
How it works:
 * Map the Asset ID: The Listener gives you a takerAssetId (e.g., 23489...). You must query the Polymarket API to find out which market this ID belongs to (e.g., "Will Bitcoin hit 100k?").
 * Place Order: Use py_clob_client to place a limit order on that same market.
Snippet for execute_copy_trade:
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType, ApiCreds

def execute_copy_trade(target_asset_id, side):
    # Initialize Client
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=os.getenv("POLY_API_KEY"),
        chain_id=137, # Polygon Mainnet
        # ... (rest of creds)
    )

    # 1. Get Market Info from Asset ID
    # This requires looking up the Condition ID via API (omitted for brevity)
    
    # 2. Place Order
    print("Placing copy trade...")
    resp = client.create_and_post_order(
        OrderArgs(
            price=0.50, # You must fetch current orderbook price to avoid slippage
            size=10.0, # Your fixed bet size
            side=side, # BUY or SELL
            token_id=target_asset_id # The token ID from the listener
        )
    )
    print("Order Placed:", resp)

Phase 4: Understanding the Data Flow
 * Target Wallet signs an order.
 * Polymarket Matcher matches it off-chain.
 * CTF Exchange settles it on-chain (Polygon).
 * Listener.py sees the OrderFilled event on the blockchain.
 * Listener.py triggers execute_copy_trade.
 * Your Wallet submits a new order to Polymarket via API.

Phase 5: The "Asset Mapper" Module
To make your bot human-readable (e.g., "Buying TRUMP YES" instead of "Buying 0x24..."), you need to query Polymarket's "Gamma API" (their metadata indexer).
The Token ID (Asset ID) you see on-chain is unique to a specific outcome (e.g., "Yes" for "Bitcoin > $100k"). We can use this ID to reverse-lookup the Market Question.
1. The Code (asset_mapper.py)
Create this file in the same directory. It uses lru_cache to store results so you don't hit the API repeatedly for the same market.
import requests
from functools import lru_cache

# Polymarket Gamma API Endpoint
GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"

@lru_cache(maxsize=100)
def get_market_details(asset_id_int):
    """
    Takes a raw Asset ID (integer) and returns a human-readable dict:
    {
        "question": "Will Trump win 2024?",
        "outcome": "Yes",
        "market_slug": "will-trump-win-us-election-2024"
    }
    """
    # 1. Convert int to String for API
    token_id_str = str(asset_id_int)
    
    # 2. Query Gamma API
    # We use 'clob_token_ids_in' to filter markets by this specific token
    params = {
        "clob_token_ids_in": token_id_str
    }
    
    try:
        response = requests.get(GAMMA_API_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return {"question": "Unknown Market", "outcome": "Unknown", "market_slug": ""}

        # 3. Parse the result
        market = data[0] # The API returns a list
        question = market.get("question", "Unknown Question")
        slug = market.get("slug", "")
        
        # Determine if this token is YES or NO
        outcome_label = "Unknown"
        tokens = market.get("tokens", [])
        
        for t in tokens:
            if t.get("token_id") == token_id_str:
                outcome_label = t.get("outcome", "Unknown") # Usually "Yes" or "No"
                break
                
        return {
            "question": question,
            "outcome": outcome_label,
            "market_slug": slug
        }

    except Exception as e:
        print(f"API Error: {e}")
        return {"question": "API Error", "outcome": "Err", "market_slug": ""}

# Quick Test
if __name__ == "__main__":
    # Example Token ID for 'Will Trump win 2024? - Yes' (Random real example ID)
    test_id = 21742633143463906290569050155826241533067272736897614950488156847949938836455
    print(get_market_details(test_id))

2. Integrating it into listener.py
Now, update your handle_event function in listener.py to use this mapper.
Step 1: Import the function at the top of listener.py:
from asset_mapper import get_market_details

Step 2: Update the handle_event function logic:
def handle_event(args, w3):
    print(f"\n{Fore.CYAN}--- DETECTED ACTIVITY ---{Style.RESET_ALL}")
    
    maker_asset = args['makerAssetId']
    taker_asset = args['takerAssetId']
    
    # Determine which asset is the Market Token vs USDC
    # USDC is almost always ID '0' or the Collateral Token address (depending on contract version)
    # In CTF Exchange, Collateral (USDC) is ID 0 when unwrapping, but usually we look for the large ID.
    
    target_token_id = 0
    action = "UNKNOWN"
    
    if maker_asset == 0:
        # Maker is giving USDC to buy a Position -> BUY
        action = "BUY"
        target_token_id = taker_asset
        size_usdc = args['makerAmountFilled'] / 10**6
    else:
        # Maker is giving a Position to get USDC -> SELL
        action = "SELL"
        target_token_id = maker_asset
        size_usdc = args['takerAmountFilled'] / 10**6

    # --- NEW: GET READABLE NAMES ---
    details = get_market_details(target_token_id)
    
    # Formatting the Output
    question = details['question'][:50] + "..." if len(details['question']) > 50 else details['question']
    outcome = details['outcome']
    
    print(f"Action: {Fore.MAGENTA}{action} {outcome}{Style.RESET_ALL}")
    print(f"Market: {question}")
    print(f"Size: ${size_usdc:,.2f} USDC")
    print(f"TokenID: {str(target_token_id)[:10]}...")
    
    # Trigger Execution
    # execute_copy_trade(target_token_id, action)

Summary of Logic Flow
 * Whale Buys: 0x6031... calls the exchange.
 * Listener: Detects OrderFilled.
 * Parser: Sees makerAssetId=0 (USDC) and takerAssetId=2174... (The Outcome Token).
 * Mapper: Sends 2174... to asset_mapper.py.
 * API: Polymarket says 2174... = "Will Trump Win? (YES)".
 * Console: Prints Action: BUY YES | Market: Will Trump Win?



Phase 6: The Executor (Making the Trade)
This is the final piece. The Executor takes the signal from the Listener and uses your wallet to mirror the trade on Polymarket.
File: executor.py
import os
import time
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
# "FOK" (Fill or Kill) prevents partial fills, but "GTC" (Good Till Cancel) is safer for copy trading
# to ensure you get in even if liquidity is thin.
ORDER_TYPE = OrderType.FOK 
SLIPPAGE_TOLERANCE = 0.05 # 5% price leeway

def get_client():
    """Initializes the Polymarket CLOB Client"""
    host = "https://clob.polymarket.com"
    key = os.getenv("MY_PRIVATE_KEY")
    chain_id = 137 # Polygon Mainnet
    
    # Init client with private key
    client = ClobClient(host, key=key, chain_id=chain_id)
    
    # Create/Derive API Credentials (necessary for placing orders)
    # This generates a temporary API key from your wallet signature
    client.set_api_creds(client.create_or_derive_api_creds())
    return client

def execute_copy_trade(token_id, side, target_price=None):
    """
    Places a trade to mirror the target.
    :param token_id: The massive integer ID of the outcome token.
    :param side: "BUY" or "SELL"
    :param target_price: (Optional) The price the whale paid. Used for limit orders.
    """
    client = get_client()
    
    # 1. Determine Size (Fixed size for safety in MVP)
    # In production, you might calculate this as % of your bankroll
    trade_size_tokens = 10.0 # e.g., Buy 10 "YES" shares
    
    try:
        # 2. Fetch Current Orderbook to avoid bad pricing
        # If we are BUYING, we look at the lowest ASK (Sell offer)
        # If we are SELLING, we look at the highest BID (Buy offer)
        book_side = SELL if side == BUY else BUY 
        price_resp = client.get_price(token_id=str(token_id), side=book_side)
        current_market_price = float(price_resp['price'])
        
        print(f"Target Token: {token_id}")
        print(f"Market Price: {current_market_price}")
        
        # 3. Safety Check: Slippage
        # If the whale bought at 0.50, and it's now 0.80, DON'T BUY.
        if target_price:
            deviation = abs(current_market_price - target_price)
            if deviation > SLIPPAGE_TOLERANCE:
                print(f"Skipping: Price moved too much (Whale: {target_price}, Now: {current_market_price})")
                return

        # 4. Construct Order
        order_args = OrderArgs(
            price=current_market_price, # Limit price
            size=trade_size_tokens,
            side=BUY if side == "BUY" else SELL,
            token_id=str(token_id)
        )
        
        # 5. Sign and Post
        print(f"Submitting {side} order...")
        resp = client.create_and_post_order(order_args, order_type=ORDER_TYPE)
        
        if resp and resp.get("success"):
            print(f"✅ Trade Executed! ID: {resp['orderID']}")
        else:
            print(f"❌ Trade Failed: {resp.get('errorMsg')}")
            
    except Exception as e:
        print(f"Execution Error: {e}")

# Test Run (Uncomment to test a tiny order on a real market if you have funds)
# if __name__ == "__main__":
# # Example: Buy "YES" on a random cheap market
# execute_copy_trade("TOKEN_ID_HERE", "BUY", target_price=0.50)

Phase 7: The Main Runner (Connecting It All)
Update your listener.py to correctly import and call the execution logic. I have refined the logic below to handle the nuance of whether the Target was the Maker (placed a limit order) or the Taker (market bought).
Updated listener.py (Final Version):
import time
import os
from web3 import Web3
from dotenv import load_dotenv
from colorama import Fore, Style, init

# Import our helper modules
from asset_mapper import get_market_details
from executor import execute_copy_trade

init()
load_dotenv()

RPC_URL = os.getenv("RPC_URL")
TARGET_WALLET = "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d".lower()
CTF_EXCHANGE_ADDR = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"

# Standard CTF Exchange ABI for 'OrderFilled'
CTF_ABI = [{"anonymous":False,"inputs":[{"indexed":True,"internalType":"bytes32","name":"orderHash","type":"bytes32"},{"indexed":True,"internalType":"address","name":"maker","type":"address"},{"indexed":True,"internalType":"address","name":"taker","type":"address"},{"indexed":False,"internalType":"uint256","name":"makerAssetId","type":"uint256"},{"indexed":False,"internalType":"uint256","name":"takerAssetId","type":"uint256"},{"indexed":False,"internalType":"uint256","name":"makerAmountFilled","type":"uint256"},{"indexed":False,"internalType":"uint256","name":"takerAmountFilled","type":"uint256"}],"name":"OrderFilled","type":"event"}]

def start_listener():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print(f"{Fore.RED}RPC Connection Failed{Style.RESET_ALL}")
        return

    print(f"{Fore.GREEN}Listening for Whale: {TARGET_WALLET}{Style.RESET_ALL}")
    contract = w3.eth.contract(address=CTF_EXCHANGE_ADDR, abi=CTF_ABI)
    last_block = w3.eth.block_number

    while True:
        try:
            current_block = w3.eth.block_number
            if current_block > last_block:
                print(f"Scanning block {current_block}...", end="\r")
                events = contract.events.OrderFilled.get_logs(fromBlock=last_block + 1, toBlock=current_block)
                
                for event in events:
                    process_event(event['args'])
                
                last_block = current_block
            time.sleep(2)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

def process_event(args):
    maker = args['maker'].lower()
    taker = args['taker'].lower()

    # Check if our target is involved
    if TARGET_WALLET not in [maker, taker]:
        return

    # LOGIC: Did the target BUY or SELL?
    # Asset ID '0' is USDC.
    
    is_buy = False
    target_token_id = None
    filled_price_approx = 0.0

    if maker == TARGET_WALLET:
        # Target was MAKER (Limit Order)
        if args['makerAssetId'] == 0:
            is_buy = True # Gave USDC, Got Token
            target_token_id = args['takerAssetId']
            # Price = USDC Given / Tokens Received
            filled_price_approx = args['makerAmountFilled'] / args['takerAmountFilled']
        else:
            is_buy = False # Gave Token, Got USDC
            target_token_id = args['makerAssetId']
            filled_price_approx = args['takerAmountFilled'] / args['makerAmountFilled']

    elif taker == TARGET_WALLET:
        # Target was TAKER (Market Order)
        if args['takerAssetId'] == 0:
            is_buy = True # Gave USDC, Got Token
            target_token_id = args['makerAssetId']
            filled_price_approx = args['takerAmountFilled'] / args['makerAmountFilled']
        else:
            is_buy = False # Gave Token, Got USDC
            target_token_id = args['takerAssetId']
            filled_price_approx = args['makerAmountFilled'] / args['takerAmountFilled']

    # --- ACTION ---
    action_str = "BUY" if is_buy else "SELL"
    details = get_market_details(target_token_id)
    
    print(f"\n{Fore.CYAN}>>> WHALE ALERT <<<{Style.RESET_ALL}")
    print(f"Action: {Fore.MAGENTA}{action_str}{Style.RESET_ALL} on {details['question']} ({details['outcome']})")
    print(f"Price: {filled_price_approx:.3f}")
    
    # Trigger the copy trade
    # Note: We pass the RAW token ID, not the human name, to the executor
    execute_copy_trade(target_token_id, action_str, target_price=filled_price_approx)

if __name__ == "__main__":
    start_listener()

8. Final Checklist to Run
 * Dependencies: pip install web3 py-clob-client python-dotenv colorama requests
 * Config: Ensure .env has your RPC_URL and MY_PRIVATE_KEY.
 * Funds: Ensure your wallet has USDC (Polygon) for betting and MATIC for gas (though py-clob-client handles gasless relaying for orders usually, you need USDC to collateralize).
 * Launch:
   python listener.py


 * Streamlit is 100% Python. You can build a professional-looking data dashboard with live metrics and control buttons in under 50 lines of code.
Architecture: The "Command Center" Model
To keep your bot stable, do not run the trading logic inside the dashboard script. Instead, decouple them:
 * The Bot (Background Process): Runs continuously. It reads a config.json file to know if it should be running or paused. It logs trades to a database (SQLite).
 * The Dashboard (Streamlit): Reads/Writes config.json to control the bot. Reads the database to visualize performance.

Step 1: The Database & Config Setup
Create a file db_setup.py to initialize your shared storage.
import sqlite3
import json

def init_db():
    conn = sqlite3.connect('trades.db')
    c = conn.cursor()
    # Create a table to store trades
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp REAL, 
                  market TEXT, 
                  outcome TEXT, 
                  side TEXT, 
                  size_usdc REAL, 
                  price REAL, 
                  status TEXT)''')
    conn.commit()
    conn.close()

def init_config():
    # Default settings
    config = {
        "is_active": False,
        "max_cap_usdc": 500.0,
        "copy_ratio": 0.1, # Copy 10% of whale's size
        "target_wallet": "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"
    }
    with open('config.json', 'w') as f:
        json.dump(config, f)

if __name__ == "__main__":
    init_db()
    init_config()
    print("Database and Config initialized.")

Step 2: The Dashboard Code (dashboard.py)
This is your UI. It auto-refreshes to show new trades.
import streamlit as st
import pandas as pd
import sqlite3
import json
import time

# Page Config
st.set_page_config(page_title="PolyMirror Control", layout="wide")
st.title("🐋 PolyMirror: Whale Tracker & Copy Trader")

# --- SIDEBAR: CONTROLS ---
st.sidebar.header("⚙️ Bot Configuration")

# Load Config
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    st.error("Config file not found. Run db_setup.py first.")
    st.stop()

# Status Toggle
status_col1, status_col2 = st.sidebar.columns(2)
is_active = config.get("is_active", False)
if is_active:
    status_col1.success("● ONLINE")
    if status_col2.button("STOP BOT"):
        config["is_active"] = False
        with open('config.json', 'w') as f:
            json.dump(config, f)
        st.rerun()
else:
    status_col1.error("● OFFLINE")
    if status_col2.button("START BOT"):
        config["is_active"] = True
        with open('config.json', 'w') as f:
            json.dump(config, f)
        st.rerun()

# Settings Inputs
new_ratio = st.sidebar.slider("Copy Ratio (0.1 = 10%)", 0.01, 1.0, config.get("copy_ratio", 0.1))
new_cap = st.sidebar.number_input("Max Bet Cap (USDC)", 10, 5000, int(config.get("max_cap_usdc", 500)))

# Save Settings Button
if st.sidebar.button("Update Settings"):
    config["copy_ratio"] = new_ratio
    config["max_cap_usdc"] = new_cap
    with open('config.json', 'w') as f:
        json.dump(config, f)
    st.sidebar.success("Settings Saved!")

# --- MAIN DASHBOARD: DATA ---

# Fetch Data
conn = sqlite3.connect('trades.db')
df = pd.read_sql_query("SELECT * FROM trades ORDER BY id DESC LIMIT 50", conn)
conn.close()

# Metrics Row
m1, m2, m3 = st.columns(3)
total_trades = len(df)
total_volume = df['size_usdc'].sum() if not df.empty else 0
last_trade_time = pd.to_datetime(df['timestamp'].iloc[0], unit='s').strftime('%H:%M:%S') if not df.empty else "--"

m1.metric("Total Copy Trades", total_trades)
m2.metric("Total Volume Copied", f"${total_volume:,.2f}")
m3.metric("Last Activity", last_trade_time)

# Recent Trades Table
st.subheader("📋 Recent Activity")
if not df.empty:
    # Stylize the dataframe
    st.dataframe(
        df[['timestamp', 'market', 'side', 'outcome', 'price', 'size_usdc', 'status']],
        use_container_width=True,
        column_config={
            "timestamp": st.column_config.DatetimeColumn("Time", format="D MMM, HH:mm:ss"),
            "price": st.column_config.NumberColumn("Entry Price", format="$%.2f"),
            "size_usdc": st.column_config.NumberColumn("Size (USDC)", format="$%.2f"),
        }
    )
else:
    st.info("No trades recorded yet. Waiting for whale activity...")

# Auto-Refresh (Poll every 2 seconds)
time.sleep(2)
st.rerun()

Step 3: Modify Your Executor to Log to DB
Update your executor.py (or wherever the trade happens) to insert a record into SQLite whenever a trade is placed.
import sqlite3
import time

def log_trade_to_db(market_name, outcome, side, size, price, status):
    conn = sqlite3.connect('trades.db')
    c = conn.cursor()
    c.execute("INSERT INTO trades (timestamp, market, outcome, side, size_usdc, price, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (time.time(), market_name, outcome, side, size, price, status))
    conn.commit()
    conn.close()

# Call this function right after client.create_and_post_order() succeeds

How to Run It
 * Run python db_setup.py (once).
 * Start your dashboard: streamlit run dashboard.py.
 * Start your bot: python listener.py.
 * Open your browser to localhost:8501 to control the bot and watch the whale trades come in.
Streamlit for Real Time Data Visualization
This video is relevant because it demonstrates how to build a real-time dashboard with Streamlit that auto-refreshes data, which is exactly the functionality needed to monitor your live trading bot without manual page reloads.