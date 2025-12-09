# 🔒 Security Best Practices for PolyMirror

This document outlines security best practices for safely operating the PolyMirror copy trading bot. Cryptocurrency trading involves handling sensitive credentials and financial assets - following these guidelines is essential.

## 🔑 Private Key Management

### Critical Rules

**NEVER**:
- ❌ Commit private keys to version control (Git, SVN, etc.)
- ❌ Share private keys via email, chat, or messaging apps
- ❌ Store private keys in plain text on shared systems
- ❌ Use your main wallet's private key for automated trading
- ❌ Screenshot or photograph private keys
- ❌ Store private keys in cloud storage (Dropbox, Google Drive, etc.)

**ALWAYS**:
- ✅ Use a dedicated wallet for copy trading
- ✅ Keep private keys in `.env` file (excluded from version control)
- ✅ Use hardware wallets for large amounts
- ✅ Encrypt private keys at rest
- ✅ Use strong passwords for encrypted storage
- ✅ Backup private keys securely offline

### Recommended Setup

#### 1. Create a Dedicated Trading Wallet

Use a separate wallet specifically for copy trading:

```bash
# Generate new wallet using web3.py
python -c "from web3 import Web3; w3 = Web3(); acc = w3.eth.account.create(); print(f'Address: {acc.address}\\nPrivate Key: {acc.key.hex()}')"
```

**Benefits**:
- Limits exposure if credentials are compromised
- Easier to monitor and audit trading activity
- Can set specific balance limits
- Simplifies accounting and tax reporting

#### 2. Use Environment Variables

Store credentials in `.env` file (never commit this file):

```env
# .env
MY_PRIVATE_KEY=0x1234567890abcdef...
RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY
```

Verify `.env` is in `.gitignore`:

```bash
# Check if .env is ignored
git check-ignore .env
# Should output: .env

# If not, add it
echo ".env" >> .gitignore
```

#### 3. Encrypt Sensitive Files

For additional security, encrypt your `.env` file:

**Using GPG**:
```bash
# Encrypt
gpg -c .env
# Creates .env.gpg

# Decrypt when needed
gpg .env.gpg
# Enter passphrase to decrypt
```

**Using OpenSSL**:
```bash
# Encrypt
openssl enc -aes-256-cbc -salt -in .env -out .env.enc

# Decrypt when needed
openssl enc -aes-256-cbc -d -in .env.enc -out .env
```

#### 4. Use Hardware Wallets for Large Amounts

For significant trading capital:
- Store bulk funds in hardware wallet (Ledger, Trezor)
- Transfer only needed amounts to hot wallet
- Regularly sweep profits back to hardware wallet
- Never connect hardware wallet directly to bot

### Private Key Rotation

Rotate private keys periodically:

1. **Create new wallet**:
   ```bash
   python -c "from web3 import Web3; w3 = Web3(); acc = w3.eth.account.create(); print(f'Address: {acc.address}\\nPrivate Key: {acc.key.hex()}')"
   ```

2. **Transfer funds** to new wallet

3. **Update `.env`** with new private key

4. **Restart bot** to use new credentials

5. **Securely delete** old private key:
   ```bash
   # Overwrite old key file multiple times
   shred -vfz -n 10 old_private_key.txt
   ```

## 🌐 RPC Endpoint Security

### Best Practices

1. **Use Dedicated API Keys**:
   - Create separate API key for this bot
   - Don't reuse keys across projects
   - Rotate keys periodically (monthly recommended)

2. **Implement Rate Limiting**:
   - Monitor API usage in provider dashboard
   - Set up alerts for unusual activity
   - Use paid tier for higher limits if needed

3. **Restrict API Key Permissions**:
   - Use read-only keys when possible
   - Limit to specific IP addresses if provider supports
   - Enable 2FA on RPC provider account

4. **Use HTTPS Only**:
   - Always use `https://` RPC endpoints
   - Never use unencrypted `http://` connections
   - Verify SSL certificates

### Recommended RPC Providers

**Alchemy** (Recommended):
- Free tier: 300M compute units/month
- Built-in DDoS protection
- Automatic failover
- Dashboard monitoring
- Sign up: https://www.alchemy.com

**Infura**:
- Free tier: 100k requests/day
- Reliable infrastructure
- Good documentation
- Sign up: https://infura.io

**QuickNode**:
- Free tier available
- Low latency
- Global endpoints
- Sign up: https://www.quicknode.com

### RPC Endpoint Configuration

```env
# Good - Alchemy with API key
RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY

# Good - Infura with project ID
RPC_URL=https://polygon-mainnet.infura.io/v3/YOUR_PROJECT_ID

# Bad - Public endpoint (unreliable, rate limited)
RPC_URL=https://polygon-rpc.com

# Bad - HTTP (unencrypted)
RPC_URL=http://polygon-rpc.com
```

## 🔐 Polymarket API Credentials

### Optional Credentials

Polymarket API credentials are optional - the bot can derive them from your private key. However, if you choose to use explicit credentials:

1. **Generate Credentials**:
   - Visit Polymarket API dashboard
   - Create new API key
   - Save key, secret, and passphrase securely

2. **Store in `.env`**:
   ```env
   POLY_API_KEY=your_api_key
   POLY_API_SECRET=your_api_secret
   POLY_API_PASSPHRASE=your_passphrase
   ```

3. **Rotate Regularly**:
   - Generate new credentials monthly
   - Delete old credentials from Polymarket dashboard
   - Update `.env` file

### API Key Permissions

If Polymarket supports permission scoping:
- Enable only "Trade" permission
- Disable "Withdraw" if available
- Disable "Transfer" if available
- Enable IP whitelisting if available

## 💻 System Security

### Operating System Hardening

1. **Keep System Updated**:
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt upgrade -y
   
   # macOS
   softwareupdate -i -a
   
   # Windows
   # Use Windows Update
   ```

2. **Enable Firewall**:
   ```bash
   # Ubuntu/Debian
   sudo ufw enable
   sudo ufw allow 8501/tcp  # Streamlit dashboard
   
   # macOS
   # System Preferences > Security & Privacy > Firewall
   
   # Windows
   # Windows Defender Firewall
   ```

3. **Disable Unnecessary Services**:
   ```bash
   # List running services
   systemctl list-units --type=service --state=running
   
   # Disable unused services
   sudo systemctl disable <service-name>
   ```

### Python Environment Security

1. **Use Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **Keep Dependencies Updated**:
   ```bash
   # Check for outdated packages
   pip list --outdated
   
   # Update all packages
   pip install --upgrade -r requirements.txt
   ```

3. **Verify Package Integrity**:
   ```bash
   # Check for known vulnerabilities
   pip install safety
   safety check
   ```

### File Permissions

Set appropriate permissions on sensitive files:

```bash
# Make .env readable only by owner
chmod 600 .env

# Make database readable/writable by owner only
chmod 600 trades.db

# Make config readable/writable by owner only
chmod 600 config.json

# Verify permissions
ls -la .env trades.db config.json
# Should show: -rw------- (600)
```

## 🖥️ Deployment Security

### Running on Local Machine

1. **Physical Security**:
   - Lock computer when away
   - Use full disk encryption
   - Enable screen lock timeout
   - Use strong login password

2. **Network Security**:
   - Use secure WiFi (WPA3 or WPA2)
   - Avoid public WiFi for trading
   - Use VPN for additional privacy
   - Enable router firewall

### Running on Cloud Server

1. **Choose Secure Provider**:
   - AWS, Google Cloud, DigitalOcean, Linode
   - Enable 2FA on cloud account
   - Use SSH keys (not passwords)
   - Enable audit logging

2. **Server Hardening**:
   ```bash
   # Disable password authentication
   sudo nano /etc/ssh/sshd_config
   # Set: PasswordAuthentication no
   
   # Restart SSH
   sudo systemctl restart sshd
   
   # Enable automatic security updates
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```

3. **Use SSH Keys**:
   ```bash
   # Generate SSH key pair
   ssh-keygen -t ed25519 -C "your_email@example.com"
   
   # Copy public key to server
   ssh-copy-id user@server_ip
   
   # Disable password auth (see above)
   ```

4. **Restrict SSH Access**:
   ```bash
   # Allow SSH only from specific IP
   sudo ufw allow from YOUR_IP to any port 22
   
   # Or use fail2ban to block brute force
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   ```

### Docker Deployment (Advanced)

For isolated environment:

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as non-root user
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

CMD ["python", "listener.py"]
```

```bash
# Build image
docker build -t polymirror .

# Run with environment file
docker run -d --env-file .env -v $(pwd)/trades.db:/app/trades.db polymirror
```

## 🚨 Monitoring and Alerts

### Set Up Monitoring

1. **Log Monitoring**:
   ```bash
   # Monitor listener logs
   tail -f listener.log
   
   # Search for errors
   grep -i error listener.log
   
   # Count failed trades
   grep -c FAILED listener.log
   ```

2. **Database Monitoring**:
   ```python
   # Check for unusual activity
   import sqlite3
   conn = sqlite3.connect("trades.db")
   cursor = conn.cursor()
   
   # Failed trades in last hour
   cursor.execute("""
       SELECT COUNT(*) FROM trades 
       WHERE status = 'FAILED' 
       AND timestamp > strftime('%s', 'now') - 3600
   """)
   print(f"Failed trades (1h): {cursor.fetchone()[0]}")
   
   # Large trades
   cursor.execute("""
       SELECT * FROM trades 
       WHERE size_usdc > 1000 
       ORDER BY timestamp DESC LIMIT 10
   """)
   print("Large trades:", cursor.fetchall())
   ```

3. **Balance Monitoring**:
   ```python
   # Check wallet balance
   from web3 import Web3
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
   
   # Your wallet address
   address = "0xYourAddress"
   
   # USDC contract on Polygon
   usdc_address = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
   usdc_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
   
   usdc = w3.eth.contract(address=usdc_address, abi=usdc_abi)
   balance = usdc.functions.balanceOf(address).call()
   print(f"USDC Balance: {balance / 1e6:.2f}")
   ```

### Set Up Alerts

**Email Alerts** (using Python):
```python
import smtplib
from email.mime.text import MIMEText

def send_alert(subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = 'bot@example.com'
    msg['To'] = 'you@example.com'
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('bot@example.com', 'app_password')
        server.send_message(msg)

# Alert on large trade
if trade_size > 1000:
    send_alert("Large Trade Alert", f"Trade size: ${trade_size}")
```

**Telegram Alerts**:
```python
import requests

def send_telegram(message):
    bot_token = "YOUR_BOT_TOKEN"
    chat_id = "YOUR_CHAT_ID"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message})

# Alert on error
send_telegram("⚠️ Bot error: Connection lost")
```

## 🔍 Incident Response

### If Private Key is Compromised

**Immediate Actions**:

1. **Stop the bot**:
   ```bash
   # Kill listener process
   pkill -f listener.py
   
   # Stop dashboard
   pkill -f streamlit
   ```

2. **Transfer funds**:
   - Create new wallet immediately
   - Transfer all USDC and MATIC to new wallet
   - Use Polygon wallet or MetaMask

3. **Revoke API credentials**:
   - Delete Polymarket API keys
   - Revoke RPC API keys
   - Generate new credentials

4. **Investigate**:
   - Check system logs for unauthorized access
   - Review recent transactions on PolygonScan
   - Scan system for malware

5. **Update credentials**:
   - Generate new private key
   - Update `.env` file
   - Restart bot with new credentials

### If System is Compromised

1. **Isolate system**:
   - Disconnect from network
   - Stop all running processes

2. **Secure funds**:
   - Transfer to hardware wallet
   - Use different computer if available

3. **Investigate**:
   - Run antivirus scan
   - Check for rootkits
   - Review system logs

4. **Rebuild**:
   - Reinstall operating system
   - Restore from clean backup
   - Update all software

## 📋 Security Checklist

Before running in production:

- [ ] Created dedicated trading wallet
- [ ] Stored private key in `.env` file
- [ ] Verified `.env` is in `.gitignore`
- [ ] Set appropriate file permissions (600)
- [ ] Using HTTPS RPC endpoint
- [ ] Enabled firewall
- [ ] System is fully updated
- [ ] Using virtual environment
- [ ] Dependencies are up to date
- [ ] Set reasonable max_cap_usdc
- [ ] Tested with small amounts first
- [ ] Set up monitoring and alerts
- [ ] Documented recovery procedures
- [ ] Backed up wallet securely
- [ ] Reviewed all security practices

## 📚 Additional Resources

- [Ethereum Security Best Practices](https://consensys.github.io/smart-contract-best-practices/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CryptoCurrency Security Standard (CCSS)](https://cryptoconsortium.github.io/CCSS/)
- [Hardware Wallet Guide](https://www.ledger.com/academy/hardwarewallet/best-practices)

## ⚠️ Disclaimer

Security is an ongoing process, not a one-time setup. Regularly review and update your security practices. The authors are not responsible for any losses due to security breaches. Always exercise caution when handling cryptocurrency and private keys.
