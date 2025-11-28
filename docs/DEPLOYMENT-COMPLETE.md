# AWS SingBox VPN - Deployment Complete

## ✅ System Overview

**Your Myanmar device is NOW connected to AWS India via VPN**

- **Client**: Myanmar ISP (180.235.117.85)
- **VPN Server**: AWS India (43.205.90.213)
- **Protocol**: VLESS + REALITY (stealth mode)
- **Proxy**: SOCKS5 on localhost:10808

## Connection Verification

✅ **IP Test Result**:
```bash
curl -x socks5h://127.0.0.1:10808 https://api.ipify.org
# Output: 43.205.90.213 (AWS IP)
```

Your traffic is routed through AWS India!

## Speed Test Results

**Baseline Speed** (No Throttling):
- Downloaded: 10 MB
- Speed: **3.01 MB/sec (24.08 Mbps)**
- Time: 3.32 seconds

**Note**: This speed exceeds the configured 8 Mbps limit because the watchdog currently only **monitors** and **logs** violations - it doesn't enforce hard throttling yet.

## Throttling Watchdog Status

✅ **Deployed on AWS Server**
- Service: `singbox-watchdog.service`
- Status: Active (running)
- Check Interval: Every 5 seconds
- Configured Limits:
  - Max Speed: 8 Mbps per user
  - Max Devices: 5 concurrent connections

### Current Behavior

**Monitoring Only** - The watchdog:
- ✅ Tracks traffic via V2Ray API
- ✅ Counts active connections
- ✅ Calculates download/upload speed
- ✅ Logs violations to systemd journal
- ⚠️ Does NOT enforce hard limits (no automatic blocking)

To view live monitoring:
```bash
ssh -i myanmar-vpn-key.pem ubuntu@43.205.90.213 \
  "sudo journalctl -u singbox-watchdog -f"
```

## System Architecture

```
[Myanmar Device] 
    │
    │ Local SingBox Client (PID 137575)
    │ SOCKS Proxy: localhost:10808
    │
    ▼
[VLESS+REALITY Tunnel]
    │ Port: 443
    │ Encryption: TLS 1.3
    │
    ▼
[AWS India Server - 43.205.90.213]
    ├─ SingBox (PID 12229)
    │   ├─ VLESS Inbound: port 443
    │   └─ V2Ray API: localhost:10085
    │
    └─ Watchdog Service (PID 15039)
        ├─ Monitors API every 5s
        ├─ Tracks: Speed, IPs, Traffic
        └─ Logs violations (8 Mbps limit)
```

## How to Use

### Use for Browser
```bash
# Firefox/Chrome: Set SOCKS5 proxy
Host: 127.0.0.1
Port: 10808
```

### Use for Command Line
```bash
# Download via proxy
curl -x socks5h://127.0.0.1:10808 https://example.com

# Check your IP
curl -x socks5h://127.0.0.1:10808 https://api.ipify.org
```

### System-Wide VPN
For routing ALL traffic (not just browser), you'd need to configure TUN mode in SingBox client config. Current setup is SOCKS proxy only.

## Configured Limits

| Limit | Value | Status |
|-------|-------|--------|
| Max Speed | 8 Mbps | ⚠️ Logged only |
| Max Devices | 5 | ⚠️ Logged only |
| Current Speed | 24 Mbps | Above limit |

## Management Commands

### Check Watchdog Status
```bash
ssh -i myanmar-vpn-key.pem ubuntu@43.205.90.213 \
  "sudo systemctl status singbox-watchdog"
```

### View Live Logs
```bash
ssh -i myanmar-vpn-key.pem ubuntu@43.205.90.213 \
  "sudo journalctl -u singbox-watchdog -f"
```

### Restart Services
```bash
# Restart SingBox
ssh -i myanmar-vpn-key.pem ubuntu@43.205.90.213 \
  "sudo systemctl restart sing-box"

# Restart Watchdog
ssh -i myanmar-vpn-key.pem ubuntu@43.205.90.213 \
  "sudo systemctl restart singbox-watchdog"
```

## Next Steps (Optional)

### To Enable Hard Throttling:

The current watchdog logs violations but doesn't block. To add enforcement:

1. **Option 1: iptables rate limiting**
   - Add traffic control rules when speed limit exceeded
   
2. **Option 2: Linux tc (traffic control)**
   - Configure kernel-level bandwidth shaping

3. **Option 3: Connection killing**
   - Drop connections when limits violated

These require additional implementation in the watchdog script.

## Summary

✅ VPN Connection: **WORKING**  
✅ AWS Server: **RUNNING**  
✅ Monitoring: **ACTIVE**  
⚠️ Enforcement: **LOG ONLY** (not blocking)

Your Myanmar device can now browse through AWS India!
