# Mumbai Shadowsocks Setup - READY TO TEST

## ✅ Installation Complete

### Server Details
- **Location**: AWS Mumbai (43.205.90.213)
- **Protocol**: Shadowsocks (TCP-based)
- **Port**: 8388 (TCP)
- **Encryption**: chacha20-ietf-poly1305
- **Password**: `W+UUieKAlVMtz0JS4RA1u7o2b75dVjBF`
- **Status**: ✅ Running and listening on 0.0.0.0:8388

### Client Configuration
Added to Sing-Box as: **`mumbai-shadowsocks`**

## Test Now

```bash
# List available proxies
sbox list

# Switch to Mumbai Shadowsocks
sbox use mumbai-shadowsocks

# Test if it works
curl ipinfo.io
# Expected: Should show Mumbai IP (43.205.90.213)
```

## Why This Test Matters

This test will reveal the REAL root cause:

### ✅ If Mumbai Shadowsocks WORKS:
**Root Cause**: Myanmar ISP blocks **UDP traffic** (QUIC protocol)
- TUIC uses UDP → Blocked ❌
- VLESS/REALITY might have other issues
- Shadowsocks uses TCP → Works ✅

**Solution**: Use TCP-based protocols only (Shadowsocks, VLESS)

### ❌ If Mumbai Shadowsocks ALSO FAILS:
**Root Cause**: Myanmar ISP blocks **Mumbai AWS IP** specifically
- Location-based blocking (AWS Mumbai datacenter)
- All protocols to 43.205.90.213 are blocked
- Thailand works because different IP/location

**Solution**: Use Thailand server, or deploy to different region

## Current Working Configuration

```json
{
  "tag": "thailand-outline",
  "server": "119.59.127.129",
  "server_port": 990,
  "method": "chacha20-ietf-poly1305"
}
```
This works because:
- TCP protocol (not UDP)
- Thailand location (not blocked)
- Non-standard port 990

## Files Modified
- Server: `/etc/shadowsocks/config.json`
- Client: `~/.config/sing-box/config.json`
- Service: `/etc/systemd/system/shadowsocks.service`
