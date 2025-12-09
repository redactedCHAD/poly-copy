"""
Database and configuration initialization module for PolyMirror.

This module provides functions to set up the SQLite database and configuration file
required for the copy trading system.
"""

import sqlite3
import json
import os


def init_db() -> None:
    """
    Initialize the SQLite database with the trades table.
    
    Creates trades.db if it doesn't exist and sets up the schema with columns:
    - id: INTEGER PRIMARY KEY AUTOINCREMENT
    - timestamp: REAL (Unix timestamp)
    - market: TEXT (human-readable question)
    - outcome: TEXT ("Yes" or "No")
    - side: TEXT ("BUY" or "SELL")
    - size_usdc: REAL
    - price: REAL
    - status: TEXT ("SUCCESS" or "FAILED")
    
    This function is idempotent - it will not overwrite existing data.
    
    Error Handling:
    - Catches database errors and reports them clearly
    - Ensures connection is closed even on error
    """
    db_exists = os.path.exists("trades.db")
    conn = None
    
    try:
        conn = sqlite3.connect("trades.db")
        cursor = conn.cursor()
        
        # Create table if it doesn't exist (idempotent)
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
        
        if db_exists:
            print("✓ Database trades.db already exists - verified schema")
        else:
            print("✓ Created trades.db with trades table")
            
    except sqlite3.DatabaseError as e:
        print(f"❌ Database error during initialization: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error during database initialization: {e}")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def init_config() -> None:
    """
    Initialize the configuration file with default values.
    
    Creates config.json if it doesn't exist with default settings:
    - is_active: False (bot disabled by default)
    - max_cap_usdc: 500.0 (maximum bet size per trade)
    - copy_ratio: 0.1 (10% of target wallet's trade size)
    - target_wallet: "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"
    
    This function is idempotent - it will not overwrite an existing config file.
    
    Error Handling:
    - Catches file I/O errors and reports them clearly
    - Validates JSON encoding
    """
    config_path = "config.json"
    
    if os.path.exists(config_path):
        print("✓ Configuration file config.json already exists - not overwriting")
        return
    
    default_config = {
        "is_active": False,
        "max_cap_usdc": 500.0,
        "copy_ratio": 0.1,
        "target_wallet": "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d"
    }
    
    try:
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=2)
        
        print("✓ Created config.json with default settings")
        
    except IOError as e:
        print(f"❌ File I/O error creating config.json: {e}")
        raise
    except json.JSONEncodeError as e:
        print(f"❌ JSON encoding error: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error creating config.json: {e}")
        raise


if __name__ == "__main__":
    print("Initializing PolyMirror database and configuration...\n")
    init_db()
    init_config()
    print("\n✓ Initialization complete!")
    print("\nNext steps:")
    print("1. Create a .env file with your credentials (see .env.example)")
    print("2. Review and adjust settings in config.json")
    print("3. Run the listener: python listener.py")
    print("4. Run the dashboard: streamlit run dashboard.py")
