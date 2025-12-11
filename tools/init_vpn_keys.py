import sqlite3
import os

DB_PATH = "src/db/vpn_bot.db"

def init_vpn_keys():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("Creating vpn_keys table...")
    c.execute('''
        CREATE TABLE IF NOT EXISTS vpn_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_uuid TEXT,
            key_name TEXT,
            protocol TEXT,
            server_address TEXT,
            server_port INTEGER,
            key_uuid TEXT,
            key_password TEXT,
            config_link TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    init_vpn_keys()
