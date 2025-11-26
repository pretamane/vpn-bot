# SingBox API-Enabled System - Quick Reference

## ✅ System Status

**SingBox Server**: Running with V2Ray API enabled  
**Watchdog Service**: Active, monitoring every 5s  
**API Endpoint**: `127.0.0.1:10085` (gRPC)

## 🔧 Management Commands

### Check Status
```bash
# Both services
sudo systemctl status sing-box sing-box-watchdog

# Individual
sudo systemctl status sing-box
sudo systemctl status sing-box-watchdog
```

### View Logs
```bash
# Watchdog (real-time)
sudo journalctl -u sing-box-watchdog -f

# SingBox server
sudo journalctl -u sing-box -f

# Last 50 lines
sudo journalctl -u sing-box-watchdog -n 50
```

### Restart Services
```bash
# Restart both
sudo systemctl restart sing-box sing-box-watchdog

# Individual
sudo systemctl restart sing-box
sudo systemctl restart sing-box-watchdog
```

### Test Watchdog Manually
```bash
# Run in foreground (Ctrl+C to stop)
sudo python3 /usr/local/bin/watchdog.py
```

## 📊 What the Watchdog Monitors

1. **Download Speed**: Per-user downlink (Mbps)
2. **Upload Speed**: Per-user uplink (Mbps)
3. **Active Devices**: Unique IPs connected to port 443
4. **Total Traffic**: Cumulative MB transferred

## ⚙️ Current Limits

- **Max Devices**: 5 concurrent IPs per UUID
- **Max Speed**: 8 Mbps per direction (down/up)
- **Check Interval**: 5 seconds

## 🔑 Connection Credentials

**Server**: `43.205.90.213:443`  
**UUID**: `98132a92-dfcc-445f-a73e-aa7dddab3398`  
**Public Key**: `O39-17lHzuq1bbpzUDcbwnzbBtd0P140Myeynito8Go`  
**Short ID**: `e69f7ecf`  
**SNI**: `www.microsoft.com`

## 📁 Important Files

- **Server Config**: `/etc/sing-box/config.json`
- **Watchdog Script**: `/usr/local/bin/watchdog.py`
- **Proto Files**: `/home/guest/.gemini/antigravity/scratch/v2ray-proto/`
- **Services**: `/etc/systemd/system/sing-box*.service`

## 🚨 Troubleshooting

### Watchdog Not Starting
```bash
# Check for import errors
sudo python3 /usr/local/bin/watchdog.py

# Verify gRPC installed system-wide
sudo pip3 list | grep grpc
```

### API Not Responding
```bash
# Test API endpoint
nc -zv 127.0.0.1 10085

# Check SingBox version has API support
/usr/local/bin/sing-box version | grep with_v2ray_api
```

### No Traffic Stats
```bash
# Verify stats are enabled in config
sudo cat /etc/sing-box/config.json | grep -A 10 experimental

# Check if user UUID matches
sudo journalctl -u sing-box-watchdog -n 20
```

## 📈 Next Steps

To enable **hard enforcement** (currently only logs violations):

1. **Modify Watchdog**: Add blocking logic in `enforce_limits()`
2. **Options**:
   - Restart SingBox service to drop connections
   - Use `iptables` to block violating IPs
   - Integrate with `tc` for traffic shaping
3. **Alert System**: Add webhook/email notifications

## 📝 Sample Watchdog Output

```
[STATS] Down: 5.23 Mbps | Up: 1.45 Mbps | Total: 125.3MB down, 32.1MB up
[OK] 2 active IPs (within limit)
```

**Violation Example**:
```
[VIOLATION] Download 12.45 Mbps > 8.0 Mbps | 6 active IPs > 5 limit
[VIOLATION] Active IPs: {'192.168.1.10', '192.168.1.11', '192.168.1.12', '192.168.1.13', '192.168.1.14', '192.168.1.15'}
```
