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
            protocol TEXT DEFAULT 'ss',
            expiry_date TIMESTAMP,
            data_limit_gb REAL DEFAULT 5.0,
            speed_limit_mbps REAL DEFAULT 12.0,
            is_active BOOLEAN DEFAULT 1,
            language_code TEXT,
            is_premium BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migration: Add protocol column if it doesn't exist (for existing databases)
    try:
        c.execute("ALTER TABLE users ADD COLUMN protocol TEXT DEFAULT 'ss'")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Migration: Add language_code column if it doesn't exist
    try:
        c.execute("ALTER TABLE users ADD COLUMN language_code TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Migration: Add is_premium column if it doesn't exist
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass

    # Migration: Add email column if it doesn't exist
    try:
        c.execute("ALTER TABLE users ADD COLUMN email TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Migration: Add grace_period_start for 24-hour grace period tracking
    try:
        c.execute("ALTER TABLE users ADD COLUMN grace_period_start TIMESTAMP")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Migration: Add expiry_reason to track why a key expired
    try:
        c.execute("ALTER TABLE users ADD COLUMN expiry_reason TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Migration: Add expired_at timestamp
    try:
        c.execute("ALTER TABLE users ADD COLUMN expired_at TIMESTAMP")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Migration: Add data_warnings_sent to track which warning thresholds were triggered
    try:
        c.execute("ALTER TABLE users ADD COLUMN data_warnings_sent TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass

    # Migration: Add phone column for SIM-based login
    try:
        c.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
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
    
    # Payment transactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            provider TEXT,
            transaction_id TEXT UNIQUE,
            amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # VPN Keys table (for auto-provisioning)
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

def add_transaction(user_id, provider, transaction_id, amount, status='approved'):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO payment_transactions (user_id, provider, transaction_id, amount, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, provider, transaction_id, amount, status))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def is_transaction_used(transaction_id):
    conn = get_db_connection()
    row = conn.execute('SELECT id FROM payment_transactions WHERE transaction_id = ?', (transaction_id,)).fetchone()
    conn.close()
    return row is not None

def add_user(uuid, telegram_id, username, protocol='ss', language_code=None, is_premium=False, expiry_days=30, email=None, speed_limit_mbps=12.0, data_limit_gb=5.0, phone=None):
    conn = get_db_connection()
    c = conn.cursor()
    expiry_date = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
    try:
        c.execute('''
            INSERT INTO users (uuid, telegram_id, username, protocol, expiry_date, language_code, is_premium, email, speed_limit_mbps, data_limit_gb, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (uuid, telegram_id, username, protocol, expiry_date, language_code, is_premium, email, speed_limit_mbps, data_limit_gb, phone))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding user: {e}")
        return False
    finally:
        conn.close()

def get_user(uuid):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE uuid = ?', (uuid,)).fetchone()
    conn.close()
    return user

def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user

def get_user_by_phone(phone):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE phone = ?', (phone,)).fetchone()
    conn.close()
    return user

def get_all_users():
    """Get all registered users."""
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return users

def get_active_users():
    """Get all active users."""
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM users WHERE is_active = 1').fetchall()
    conn.close()
    return [dict(row) for row in rows]

def expire_user(uuid, reason='data_limit_exceeded'):
    """
    Expire a user's VPN access and log the reason.
    
    Args:
        uuid: User's UUID
        reason: Reason for expiration (e.g., 'data_limit_exceeded', 'grace_period_ended')
    
    Returns:
        bool: True if successful
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        UPDATE users 
        SET is_active = 0,
            expiry_reason = ?,
            expired_at = CURRENT_TIMESTAMP
        WHERE uuid = ?
    ''', (reason, uuid))
    
    conn.commit()
    conn.close()
    return True

def start_grace_period(uuid):
    """
    Start the 24-hour grace period for a user who exceeded their data limit.
    
    Args:
        uuid: User's UUID
    
    Returns:
        bool: True if successful
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        UPDATE users 
        SET grace_period_start = CURRENT_TIMESTAMP
        WHERE uuid = ?
    ''', (uuid,))
    
    conn.commit()
    conn.close()
    return True

def end_grace_period(uuid):
    """
    End the grace period and expire the user.
    
    Args:
        uuid: User's UUID
    
    Returns:
        bool: True if successful
    """
    return expire_user(uuid, reason='grace_period_ended')

def is_in_grace_period(user):
    """
    Check if a user is currently in their 24-hour grace period.
    
    Args:
        user: User dict with grace_period_start field
    
    Returns:
        bool: True if in grace period, False otherwise
    """
    if not user.get('grace_period_start'):
        return False
    
    grace_start = datetime.datetime.fromisoformat(user['grace_period_start'])
    grace_end = grace_start + datetime.timedelta(hours=24)
    now = datetime.datetime.now()
    
    return now < grace_end

def get_grace_period_remaining(user):
    """
    Get remaining time in grace period.
    
    Args:
        user: User dict with grace_period_start field
    
    Returns:
        timedelta: Remaining time, or None if not in grace period
    """
    if not user.get('grace_period_start'):
        return None
    
    grace_start = datetime.datetime.fromisoformat(user['grace_period_start'])
    grace_end = grace_start + datetime.timedelta(hours=24)
    now = datetime.datetime.now()
    
    if now < grace_end:
        return grace_end - now
    return None

def update_data_warning(uuid, threshold):
    """
    Record that a data usage warning has been sent for a specific threshold.
    
    Args:
        uuid: User's UUID
        threshold: Warning threshold percentage (e.g., 30, 65, 95)
    
    Returns:
        bool: True if successful
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get current warnings
    row = c.execute('SELECT data_warnings_sent FROM users WHERE uuid = ?', (uuid,)).fetchone()
    if not row:
        conn.close()
        return False
    
    current_warnings = row['data_warnings_sent'] or ''
    warnings_list = current_warnings.split(',') if current_warnings else []
    
    # Add new threshold if not already present
    threshold_str = str(threshold)
    if threshold_str not in warnings_list:
        warnings_list.append(threshold_str)
        new_warnings = ','.join(warnings_list)
        
        c.execute('''
            UPDATE users 
            SET data_warnings_sent = ?
            WHERE uuid = ?
        ''', (new_warnings, uuid))
        
        conn.commit()
    
    conn.close()
    return True

def has_warning_been_sent(user, threshold):
    """
    Check if a warning has already been sent for a specific threshold.
    
    Args:
        user: User dict with data_warnings_sent field
        threshold: Warning threshold percentage (e.g., 30, 65, 95)
    
    Returns:
        bool: True if warning was already sent
    """
    warnings_sent = user.get('data_warnings_sent', '') or ''
    warnings_list = warnings_sent.split(',') if warnings_sent else []
    return str(threshold) in warnings_list

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
        
        # Handle protocol column safely (might not exist in older databases)
        try:
            protocol = user['protocol'] if user['protocol'] else 'ss'
        except (KeyError, IndexError):
            protocol = 'ss'  # Default to ss for backward compatibility
        
        stats.append({
            'uuid': uuid,
            'protocol': protocol,
            'is_active': user['is_active'],
            'data_limit_gb': user['data_limit_gb'],
            'daily_usage_bytes': daily_usage,
            'expiry_date': user['expiry_date']
        })
    conn.close()
    return stats

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

def get_all_users():
    """Get all registered users."""
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return users

def delete_user(uuid):
    """Delete a user and their usage logs."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('DELETE FROM usage_logs WHERE uuid = ?', (uuid,))
        c.execute('DELETE FROM users WHERE uuid = ?', (uuid,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def activate_user(uuid):
    """Activate a user's key."""
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_active = 1 WHERE uuid = ?', (uuid,))
    conn.commit()
    conn.close()
    return True

if __name__ == '__main__':
    init_db()
    print("Database initialized.")

