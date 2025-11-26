# Bandwidth Limiting - Implementation Guide

## Overview
The VPN bot now enforces **5GB daily bandwidth limits** per user with automatic blocking when exceeded.

## How It Works

### 1. V2Ray API Stats Collection
Sing-Box exposes traffic stats via V2Ray-compatible API on `127.0.0.1:10085`.

### 2. Watchdog Service Monitoring
Every 60 seconds, the watchdog:
1. Queries uplink/downlink traffic for all active users
2. Updates `usage_logs` table with bytes used
3. Checks if `daily_gb > data_limit_gb`
4. If exceeded: Sets `is_active = 0` to block user

### 3. Database Schema
```sql
CREATE TABLE users (
    uuid TEXT PRIMARY KEY,
    telegram_id INTEGER,
    data_limit_gb REAL DEFAULT 5.0,    -- Daily limit
    speed_limit_mbps REAL DEFAULT 12.0, -- Future use
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE usage_logs (
    uuid TEXT,
    date DATE,
    bytes_used INTEGER DEFAULT 0,
    UNIQUE(uuid, date)
);
```

### 4. Automatic Reset
Usage resets daily (midnight) as `date` changes in `usage_logs`.

## Services Running

| Service | Status | Purpose |
|---|---|---|
| `sing-box` | ✅ Active | VPN server + API stats |
| `vpn-bot` | ✅ Active | Telegram bot |
| `watchdog` | ✅ Active | Bandwidth monitor |

## Configuration

**Default Limits** (set in `database.py`):
- `data_limit_gb`: 5.0 GB/day
- `speed_limit_mbps`: 12.0 Mbps (not yet enforced)

**To Change Limits**:
```sql
UPDATE users SET data_limit_gb = 10.0 WHERE uuid = '<UUID>';
```

## Monitoring

**Check Watchdog Logs**:
```bash
sudo journalctl -u watchdog -f
```

**Check User Usage**:
```sql
SELECT u.uuid, u.data_limit_gb, l.bytes_used / (1024*1024*1024) as daily_gb
FROM users u
LEFT JOIN usage_logs l ON u.uuid = l.uuid AND l.date = DATE('now')
WHERE u.is_active = 1;
```

## Limitations & Future Enhancements

**Current**:
- ✅ Daily bandwidth tracking
- ✅ Automatic blocking when exceeded
- ❌ No Telegram notification to user
- ❌ No automatic config removal (user stays in config but inactive in DB)

**Future**:
- Send Telegram message when limit hit
- Remove user from Sing-Box config dynamically
- Device limiting (track concurrent IPs/connections)  
- Speed throttling (not just blocking)

## Testing

Simulate high usage:
```python
from db.database import update_usage
update_usage('test-uuid', 6 * 1024**3)  # 6 GB
# Watchdog will detect on next check (60s) and block
```
