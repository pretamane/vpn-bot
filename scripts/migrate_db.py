import sqlite3

conn = sqlite3.connect('src/db/vpn_bot.db')
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    conn.commit()
    print("Column 'phone' added successfully.")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
