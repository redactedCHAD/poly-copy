"""
Dashboard module for PolyMirror copy trading bot.

Provides a Streamlit web interface for monitoring bot activity and controlling settings.
"""

import streamlit as st
import sqlite3
import json
import time
from datetime import datetime


def load_config():
    """Load configuration from config.json."""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("config.json not found. Please run db_setup.py first.")
        return None
    except json.JSONDecodeError:
        st.error("Invalid config.json format.")
        return None


def save_config(config):
    """Save configuration to config.json."""
    try:
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Failed to save config: {e}")
        return False


def get_trades():
    """Query trades.db for the 50 most recent trades."""
    try:
        conn = sqlite3.connect("trades.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, timestamp, market, outcome, side, size_usdc, price, status
            FROM trades
            ORDER BY id DESC
            LIMIT 50
        """)
        
        trades = cursor.fetchall()
        conn.close()
        
        return trades
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return []
    except FileNotFoundError:
        st.warning("trades.db not found. Please run db_setup.py first.")
        return []


def calculate_metrics(trades):
    """
    Calculate metrics from trade records.
    
    Returns:
        tuple: (total_trades, total_volume, last_trade_time)
    """
    if not trades:
        return 0, 0.0, None
    
    total_trades = len(trades)
    total_volume = sum(trade[5] for trade in trades)  # size_usdc is index 5
    last_trade_time = trades[0][1] if trades else None  # timestamp is index 1
    
    return total_trades, total_volume, last_trade_time


# Configure Streamlit page
st.set_page_config(
    page_title="PolyMirror Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 PolyMirror Copy Trading Dashboard")

# Sidebar - Configuration Controls
st.sidebar.header("⚙️ Bot Configuration")

config = load_config()

if config:
    # Bot status indicator
    is_active = config.get("is_active", False)
    status_color = "🟢" if is_active else "🔴"
    status_text = "ONLINE" if is_active else "OFFLINE"
    st.sidebar.markdown(f"### {status_color} Status: **{status_text}**")
    
    st.sidebar.markdown("---")
    
    # START/STOP buttons
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("▶️ START BOT", disabled=is_active, use_container_width=True):
            config["is_active"] = True
            if save_config(config):
                st.success("Bot started!")
                st.rerun()
    
    with col2:
        if st.button("⏸️ STOP BOT", disabled=not is_active, use_container_width=True):
            config["is_active"] = False
            if save_config(config):
                st.success("Bot stopped!")
                st.rerun()
    
    st.sidebar.markdown("---")
    
    # Settings controls
    st.sidebar.subheader("Trading Settings")
    
    copy_ratio = st.sidebar.slider(
        "Copy Ratio",
        min_value=0.01,
        max_value=1.0,
        value=float(config.get("copy_ratio", 0.1)),
        step=0.01,
        help="Percentage of target wallet's trade size to copy"
    )
    
    max_cap = st.sidebar.number_input(
        "Max Cap (USDC)",
        min_value=10.0,
        max_value=5000.0,
        value=float(config.get("max_cap_usdc", 500.0)),
        step=10.0,
        help="Maximum bet size per trade"
    )
    
    target_wallet = st.sidebar.text_input(
        "Target Wallet",
        value=config.get("target_wallet", ""),
        help="Ethereum address to monitor"
    )
    
    # Update Settings button
    if st.sidebar.button("💾 Update Settings", use_container_width=True):
        config["copy_ratio"] = copy_ratio
        config["max_cap_usdc"] = max_cap
        config["target_wallet"] = target_wallet
        
        if save_config(config):
            st.sidebar.success("✅ Settings updated!")
        else:
            st.sidebar.error("❌ Failed to update settings")

# Main Dashboard
st.markdown("---")

# Get trades data
trades = get_trades()

# Calculate and display metrics
total_trades, total_volume, last_trade_time = calculate_metrics(trades)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Trades", total_trades)

with col2:
    st.metric("Total Volume", f"${total_volume:,.2f}")

with col3:
    if last_trade_time:
        last_trade_dt = datetime.fromtimestamp(last_trade_time)
        st.metric("Last Trade", last_trade_dt.strftime("%Y-%m-%d %H:%M:%S"))
    else:
        st.metric("Last Trade", "N/A")

st.markdown("---")

# Display trades table
st.subheader("📈 Recent Trades")

if trades:
    # Format trades for display
    formatted_trades = []
    for trade in trades:
        trade_id, timestamp, market, outcome, side, size_usdc, price, status = trade
        
        # Format timestamp
        dt = datetime.fromtimestamp(timestamp)
        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        
        formatted_trades.append({
            "ID": trade_id,
            "Timestamp": formatted_time,
            "Market": market,
            "Outcome": outcome,
            "Side": side,
            "Size (USDC)": f"${size_usdc:.2f}",
            "Price": f"{price:.4f}",
            "Status": status
        })
    
    st.dataframe(
        formatted_trades,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("ℹ️ No trades recorded yet. The bot will display trades here once it starts copying.")

# Auto-refresh logic
st.markdown("---")
st.caption("🔄 Dashboard auto-refreshes every 2 seconds")

time.sleep(2)
st.rerun()
