import sqlite3
import os

DB_PATH = "/home/ubuntu/vpn-bot/src/db/vpn_bot.db"

try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- Recent VPN Keys ---")
    cursor.execute("SELECT id, user_uuid, key_name, protocol, created_at, is_active FROM vpn_keys ORDER BY created_at DESC LIMIT 10")
    keys = cursor.fetchall()
    for k in keys:
        print(f"ID: {k['id']}, User: {k['user_uuid']}, Name: {k['key_name']}, Proto: {k['protocol']}, Active: {k['is_active']}")
        
    print("\n--- User Count ---")
    cursor.execute("SELECT count(*) as count FROM users")
    print(f"Total Users: {cursor.fetchone()['count']}")

    conn.close()
except Exception as e:
    print(f"Error: {e}")
