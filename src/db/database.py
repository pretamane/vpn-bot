import sqlite3
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'vpn_bot.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            uuid TEXT PRIMARY KEY,
            telegram_id INTEGER,
            username TEXT,
            expiry_date TIMESTAMP,
            data_limit_gb REAL DEFAULT 5.0,
            speed_limit_mbps REAL DEFAULT 12.0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Usage logs table (daily usage)
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT,
            date DATE,
            bytes_used INTEGER DEFAULT 0,
            FOREIGN KEY (uuid) REFERENCES users (uuid),
            UNIQUE(uuid, date)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(uuid, telegram_id, username, expiry_days=30):
    conn = get_db_connection()
    c = conn.cursor()
    expiry_date = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
    try:
        c.execute('''
            INSERT INTO users (uuid, telegram_id, username, expiry_date)
            VALUES (?, ?, ?, ?)
        ''', (uuid, telegram_id, username, expiry_date))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(uuid):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE uuid = ?', (uuid,)).fetchone()
    conn.close()
    return user

def get_active_key_count(telegram_id):
    """Get count of active keys for a Telegram user."""
    conn = get_db_connection()
    count = conn.execute(
        'SELECT COUNT(*) as count FROM users WHERE telegram_id = ? AND is_active = 1',
        (telegram_id,)
    ).fetchone()['count']
    conn.close()
    return count

def deactivate_user(uuid):
    """Deactivate a user's key."""
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_active = 0 WHERE uuid = ?', (uuid,))
    conn.commit()
    conn.close()
    return True

def get_user_stats(telegram_id):
    """Get detailed stats for all keys of a Telegram user."""
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)).fetchall()
    
    stats = []
    for user in users:
        uuid = user['uuid']
        daily_usage = get_daily_usage(uuid)
        stats.append({
            'uuid': uuid,
            'is_active': user['is_active'],
            'data_limit_gb': user['data_limit_gb'],
            'daily_usage_bytes': daily_usage,
            'expiry_date': user['expiry_date']
        })
    conn.close()
    return stats

def deactivate_user(uuid):
    """Deactivate a user's key."""
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_active = 0 WHERE uuid = ?', (uuid,))
    conn.commit()
    conn.close()
    return True

def update_usage(uuid, bytes_added, date=None):
    if date is None:
        date = datetime.date.today()
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Ensure record exists
    c.execute('''
        INSERT OR IGNORE INTO usage_logs (uuid, date, bytes_used)
        VALUES (?, ?, 0)
    ''', (uuid, date))
    
    # Update usage
    c.execute('''
        UPDATE usage_logs 
        SET bytes_used = bytes_used + ?
        WHERE uuid = ? AND date = ?
    ''', (bytes_added, uuid, date))
    
    conn.commit()
    conn.close()

def get_daily_usage(uuid, date=None):
    if date is None:
        date = datetime.date.today()
        
    conn = get_db_connection()
    row = conn.execute('''
        SELECT bytes_used FROM usage_logs 
        WHERE uuid = ? AND date = ?
    ''', (uuid, date)).fetchone()
    conn.close()
    
    return row['bytes_used'] if row else 0

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
