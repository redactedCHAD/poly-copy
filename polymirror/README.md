# 📊 PolyMirror - Polymarket Copy Trading Bot

PolyMirror is a real-time copy trading system for Polymarket that monitors blockchain events on Polygon and automatically replicates trades from a target wallet. The system provides a web-based dashboard for monitoring and control.

## 🎯 Features

- **Real-time Trade Detection**: Monitors Polygon blockchain for OrderFilled events every 2 seconds
- **Automatic Trade Mirroring**: Copies trades from a target wallet with configurable ratio
- **Slippage Protection**: Validates prices before execution (5% default tolerance)
- **Web Dashboard**: Streamlit-based interface for monitoring and control
- **Trade History**: SQLite database logs all executed trades
- **Error Resilience**: Handles API failures, network issues, and order rejections gracefully
- **Configurable Settings**: Adjust copy ratio, max cap, and target wallet without code changes

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- 2GB RAM minimum
- Stable internet connection
- Linux, macOS, or Windows

### External Services
- **Polygon RPC Endpoint**: Alchemy or Infura recommended (free tier available)
- **Polymarket Account**: For API access (optional - credentials can be derived)
- **Wallet with USDC**: On Polygon network for trading
- **Wallet with MATIC**: For gas fees on Polygon

### Required Knowledge
- Basic understanding of cryptocurrency wallets and private keys
- Familiarity with command-line interfaces
- Understanding of Polymarket prediction markets

## 🚀 Installation

### 1. Clone or Download the Repository

```bash
# If using git
git clone <repository-url>
cd polymarket-copy-trader

# Or download and extract the ZIP file
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `web3` - Ethereum/Polygon blockchain interaction
- `py-clob-client` - Polymarket order placement
- `python-dotenv` - Environment variable management
- `colorama` - Terminal output formatting
- `requests` - HTTP client for Gamma API
- `streamlit` - Web dashboard framework
- `hypothesis` - Property-based testing
- `pytest` - Unit testing framework

### 3. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Required: Your wallet's private key (64 hex characters)
MY_PRIVATE_KEY=eb2ca4521c1743f3b685a75e00d061fcb2f08d7c322bcce288581fac6a17e225

# Required: Polygon RPC endpoint
RPC_URL=https://polygon-rpc.com

# Optional: Polymarket API credentials (will be derived from private key if not provided)
POLY_API_KEY=
POLY_API_SECRET=
POLY_API_PASSPHRASE=
```

**⚠️ SECURITY WARNING**: Never commit your `.env` file to version control! See [SECURITY.md](SECURITY.md) for best practices.

### 4. Initialize Database and Configuration

```bash
python db_setup.py
```

This creates:
- `trades.db` - SQLite database for trade history
- `config.json` - Configuration file with default settings

### 5. Configure Settings

Edit `config.json` to customize bot behavior:

```json
{
  "is_active": false,
  "max_cap_usdc": 500.0,
  "copy_ratio": 0.1,
  "target_wallet": "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"
}
```

- `is_active`: Enable/disable the bot (false by default for safety)
- `max_cap_usdc`: Maximum bet size per trade in USDC
- `copy_ratio`: Percentage of target wallet's trade size (0.1 = 10%)
- `target_wallet`: Ethereum address to monitor and copy

## 📖 Usage

### Starting the System

The system consists of two components that run simultaneously:

#### 1. Start the Listener (Terminal 1)

```bash
python listener.py
```

The listener will:
- Connect to Polygon RPC
- Monitor for OrderFilled events
- Detect trades from the target wallet
- Execute mirror trades when bot is active

Expected output:
```
================================================================================
🎧 PolyMirror Listener Starting...
================================================================================

✓ Configuration loaded
  Target Wallet: 0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d
  Bot Active:    False
  Copy Ratio:    0.1
  Max Cap:       500.0 USDC

Connecting to Polygon RPC: https://polygon-mainnet.g.alchemy.com/v2/...
✓ Connected to Polygon network
  Chain ID: 137
  Latest Block: 52345678

✓ CTF Exchange contract loaded
  Address: 0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E

================================================================================
🎧 Listener is now ACTIVE - monitoring for trades...
================================================================================
```

#### 2. Start the Dashboard (Terminal 2)

```bash
streamlit run dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Using the Dashboard

#### Bot Controls (Sidebar)
- **Status Indicator**: Shows if bot is ONLINE (🟢) or OFFLINE (🔴)
- **START BOT**: Activates trade copying
- **STOP BOT**: Pauses trade copying
- **Copy Ratio Slider**: Adjust percentage of target wallet's trade size (1% - 100%)
- **Max Cap Input**: Set maximum bet size per trade (10 - 5000 USDC)
- **Target Wallet**: Change the wallet address to monitor
- **Update Settings**: Save configuration changes

#### Main Dashboard
- **Metrics Row**: Total trades, total volume, last trade timestamp
- **Recent Trades Table**: 50 most recent trades with details
- **Auto-refresh**: Updates every 2 seconds automatically

### Workflow Example

1. **Initial Setup**:
   - Start listener in Terminal 1
   - Start dashboard in Terminal 2
   - Verify bot shows OFFLINE status

2. **Configure Settings**:
   - Adjust copy ratio (e.g., 0.05 = 5% of target's size)
   - Set max cap (e.g., 100 USDC maximum per trade)
   - Click "Update Settings"

3. **Activate Bot**:
   - Click "START BOT" in dashboard
   - Listener will now execute mirror trades
   - Watch Terminal 1 for trade detection logs

4. **Monitor Activity**:
   - Dashboard shows real-time trade history
   - Metrics update automatically
   - Listener logs show detailed trade information

5. **Stop Bot**:
   - Click "STOP BOT" to pause trading
   - Listener continues monitoring but won't execute trades
   - Can restart anytime without losing history

## 🔍 Understanding Trade Detection

### How It Works

1. **Event Monitoring**: Listener polls Polygon blockchain every 2 seconds for new blocks
2. **Event Filtering**: Checks OrderFilled events from CTF Exchange contract
3. **Wallet Matching**: Identifies events where target wallet is maker or taker
4. **Direction Classification**: Determines if trade is BUY or SELL based on asset IDs
5. **Price Calculation**: Computes filled price from USDC and token amounts
6. **Market Lookup**: Queries Gamma API for human-readable market information
7. **Trade Execution**: Places mirror order if bot is active and price is acceptable

### Trade Direction Logic

- **BUY**: Target wallet is giving USDC (Asset ID 0) to receive outcome tokens
- **SELL**: Target wallet is giving outcome tokens to receive USDC

### Example Log Output

```
================================================================================
🎯 TARGET WALLET TRADE DETECTED
================================================================================
Role:     MAKER
Action:   BUY
Market:   Will Trump win the 2024 election?
Outcome:  Yes
Price:    0.5234
Size:     1000.00 USDC
Token ID: 123456789
================================================================================

🚀 Executing mirror trade...
✅ Order placed: BUY 100.00 USDC of Yes @ 0.5234
```

## 🧪 Testing

### Run Unit Tests

```bash
pytest test_*.py -v
```

### Run Property-Based Tests

```bash
pytest test_properties_*.py -v
```

Property tests use Hypothesis to generate random inputs and verify correctness properties across 100+ iterations.

### Test Coverage

The test suite includes:
- **Listener Tests**: Event processing, trade direction logic, connection handling
- **Executor Tests**: Order construction, slippage validation, database logging
- **Asset Mapper Tests**: API interaction, caching, error handling
- **Dashboard Tests**: Configuration management, metrics calculation
- **Property Tests**: Universal correctness properties across all components

## 📊 Database Schema

### trades.db

```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,           -- Unix timestamp
    market TEXT NOT NULL,              -- "Will Trump win 2024?"
    outcome TEXT NOT NULL,             -- "Yes" or "No"
    side TEXT NOT NULL,                -- "BUY" or "SELL"
    size_usdc REAL NOT NULL,           -- Trade size in USDC
    price REAL NOT NULL,               -- Entry price (0.0-1.0)
    status TEXT NOT NULL               -- "SUCCESS" or "FAILED"
);
```

### Querying Trade History

```python
import sqlite3

conn = sqlite3.connect("trades.db")
cursor = conn.cursor()

# Get all successful trades
cursor.execute("SELECT * FROM trades WHERE status = 'SUCCESS'")
trades = cursor.fetchall()

# Calculate total volume
cursor.execute("SELECT SUM(size_usdc) FROM trades WHERE status = 'SUCCESS'")
total_volume = cursor.fetchone()[0]

conn.close()
```

## ⚙️ Configuration Reference

### config.json

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `is_active` | boolean | `false` | Enable/disable trade execution |
| `max_cap_usdc` | float | `500.0` | Maximum bet size per trade |
| `copy_ratio` | float | `0.1` | Percentage of target's trade size (0.01-1.0) |
| `target_wallet` | string | `"0x6031..."` | Ethereum address to monitor |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MY_PRIVATE_KEY` | Yes | Your wallet's private key (64 hex chars) |
| `RPC_URL` | Yes | Polygon RPC endpoint URL |
| `POLY_API_KEY` | No | Polymarket API key (optional) |
| `POLY_API_SECRET` | No | Polymarket API secret (optional) |
| `POLY_API_PASSPHRASE` | No | Polymarket API passphrase (optional) |

## 🔧 Troubleshooting

### Bot Not Detecting Trades

**Symptoms**: Listener running but no trades detected

**Solutions**:
1. Verify RPC connection is active:
   - Check RPC_URL in .env is correct
   - Test RPC endpoint: `curl $RPC_URL -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'`
   - Try alternative RPC provider (Alchemy, Infura, QuickNode)

2. Confirm target wallet address:
   - Check `target_wallet` in config.json is correct
   - Ensure address is lowercase or properly checksummed
   - Verify target wallet is actually trading on Polymarket

3. Ensure bot is active:
   - Check `is_active` is `true` in config.json
   - Restart listener after config changes
   - Verify dashboard shows ONLINE status

4. Check CTF Exchange contract address:
   - Confirm `CTF_EXCHANGE_ADDR` in listener.py is correct
   - Current address: `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E`

### Orders Failing

**Symptoms**: Trades detected but orders fail to execute

**Solutions**:
1. Check USDC balance:
   - Verify wallet has sufficient USDC on Polygon
   - Check balance: Visit PolygonScan with your wallet address
   - Transfer USDC to Polygon if needed

2. Verify MATIC for gas:
   - Ensure wallet has MATIC for transaction fees
   - Minimum recommended: 0.1 MATIC

3. Review slippage tolerance:
   - Default is 5% - may be too tight for volatile markets
   - Increase in executor.py: `slippage_tolerance = 0.10` (10%)
   - Consider market liquidity before adjusting

4. Check Polymarket API status:
   - Visit Polymarket status page
   - Check for maintenance windows
   - Review error messages in listener logs

5. Validate private key:
   - Ensure MY_PRIVATE_KEY in .env is correct
   - Key should be 64 hex characters (without 0x prefix or with it)
   - Test key derivation: Run executor.py standalone

### Dashboard Not Updating

**Symptoms**: Dashboard shows stale data or errors

**Solutions**:
1. Verify database file exists:
   - Check `trades.db` exists in project directory
   - Run `python db_setup.py` if missing
   - Ensure file has write permissions

2. Check Streamlit is running:
   - Verify dashboard is running on correct port (8501)
   - Check for port conflicts: `netstat -an | grep 8501`
   - Try different port: `streamlit run dashboard.py --server.port 8502`

3. Refresh browser:
   - Hard refresh: Ctrl+F5 (Windows/Linux) or Cmd+Shift+R (Mac)
   - Clear browser cache
   - Try incognito/private browsing mode

4. Check for Python errors:
   - Review terminal running dashboard for error messages
   - Check for missing dependencies: `pip install -r requirements.txt`
   - Verify Python version: `python --version` (should be 3.8+)

### High Slippage Warnings

**Symptoms**: Frequent "Slippage exceeded" messages

**Solutions**:
1. Increase slippage tolerance:
   - Edit executor.py: `slippage_tolerance = 0.10` (10%)
   - Balance between protection and execution rate
   - Consider market volatility

2. Reduce copy ratio:
   - Lower copy_ratio in config.json (e.g., 0.05 = 5%)
   - Smaller orders have less price impact
   - Easier to fill at desired price

3. Use faster RPC endpoint:
   - Upgrade to paid RPC plan for lower latency
   - Try multiple providers: Alchemy, Infura, QuickNode
   - Consider dedicated node for high-frequency trading

4. Review market liquidity:
   - Check orderbook depth on Polymarket
   - Avoid copying trades in illiquid markets
   - Consider filtering by market volume

### Connection Errors

**Symptoms**: "Connection error" or "RPC connection lost"

**Solutions**:
1. Check internet connection:
   - Verify network connectivity
   - Test with: `ping 8.8.8.8`
   - Check firewall settings

2. Verify RPC endpoint:
   - Test RPC URL in browser or with curl
   - Check API key is valid and not rate-limited
   - Review RPC provider dashboard for issues

3. Increase timeout:
   - Edit listener.py: Increase sleep duration after errors
   - Add exponential backoff for retries
   - Consider connection pooling

4. Use backup RPC:
   - Configure fallback RPC endpoints
   - Implement automatic failover
   - Monitor RPC uptime

### Database Errors

**Symptoms**: "Database locked" or write failures

**Solutions**:
1. Close competing connections:
   - Ensure only one listener instance is running
   - Close database browser tools (DB Browser for SQLite)
   - Check for zombie processes: `ps aux | grep python`

2. Increase timeout:
   - Edit executor.py: `sqlite3.connect("trades.db", timeout=30)`
   - Allows more time for lock acquisition
   - Helps with concurrent access

3. Check file permissions:
   - Verify trades.db is writable: `ls -l trades.db`
   - Fix permissions: `chmod 644 trades.db`
   - Ensure directory is writable

4. Backup and recreate:
   - Backup: `cp trades.db trades.db.backup`
   - Delete: `rm trades.db`
   - Recreate: `python db_setup.py`
   - Restore data if needed

### Import Errors

**Symptoms**: "ModuleNotFoundError" or import failures

**Solutions**:
1. Reinstall dependencies:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

2. Check Python version:
   ```bash
   python --version  # Should be 3.8+
   ```

3. Use virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Verify installation:
   ```bash
   pip list | grep web3
   pip list | grep streamlit
   ```

## 🔒 Security Considerations

See [SECURITY.md](SECURITY.md) for comprehensive security best practices.

**Quick Security Checklist**:
- ✅ Never commit `.env` file to version control
- ✅ Use separate wallet for copy trading (not your main wallet)
- ✅ Start with small max_cap_usdc for testing
- ✅ Keep private keys encrypted at rest
- ✅ Use hardware wallet for large amounts
- ✅ Monitor bot activity regularly
- ✅ Set up alerts for unusual behavior
- ✅ Keep system and dependencies updated

## 📈 Performance Tips

### Optimize for Speed
- Use paid RPC endpoint for lower latency
- Increase polling frequency (reduce sleep time in listener.py)
- Use WebSocket connection instead of HTTP polling
- Deploy on cloud server closer to RPC endpoint

### Optimize for Reliability
- Implement exponential backoff for retries
- Add health check monitoring
- Set up alerting for failures
- Use database connection pooling
- Implement circuit breaker pattern

### Optimize for Cost
- Use free RPC tier for testing
- Reduce polling frequency (increase sleep time)
- Filter events by market to reduce processing
- Implement trade size minimums

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

[Add your license here]

## ⚠️ Disclaimer

This software is provided for educational purposes only. Cryptocurrency trading involves substantial risk of loss. The authors are not responsible for any financial losses incurred through use of this software. Always test with small amounts first and never invest more than you can afford to lose.

## 🆘 Support

For issues and questions:
- Check this README and troubleshooting section
- Review [SECURITY.md](SECURITY.md) for security questions
- Open an issue on GitHub
- Check Polymarket documentation: https://docs.polymarket.com

## 📚 Additional Resources

- [Polymarket Documentation](https://docs.polymarket.com)
- [py-clob-client Documentation](https://github.com/Polymarket/py-clob-client)
- [Web3.py Documentation](https://web3py.readthedocs.io)
- [Streamlit Documentation](https://docs.streamlit.io)
- [Polygon Network](https://polygon.technology)
