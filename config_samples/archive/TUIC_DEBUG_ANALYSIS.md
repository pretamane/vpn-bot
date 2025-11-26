# TUIC Connection Failure Root Cause Analysis

## Problem Statement
TUIC connection hangs and blocks all internet traffic, while Shadowsocks works fine on the same machine.

## Key Findings

### ✅ What's Working
1. **TUIC Server**: Running successfully on AWS Mumbai (confirmed via SSH)
2. **TUIC Client**: Sing-Box recognizes TUIC as available proxy
3. **Client-Side Routing**: TUIC tunnel attempts to route traffic (logs show outbound connections)
4. **UDP Capability**: Local machine can send UDP packets to network

### ❌ What's Failing
1. **Server Never Receives Packets**: `journalctl -u tuic` shows ZERO incoming connections
2. **All Traffic Times Out**: 300ms delays on every connection attempt
3. **Complete Network Blackhole**: When TUIC is active, even this chat stops working

## Protocol Comparison

### Working: Shadowsocks (Thailand)
```json
{
  "type": "shadowsocks",
  "server": "119.59.127.129",
  "server_port": 990,           ← TCP port
  "method": "chacha20-ietf-poly1305"
}
```
- **Protocol**: TCP-based
- **Port**: 990 (non-standard)
- **Result**: ✅ Works perfectly

### Failing: TUIC (Mumbai)  
```json
{
  "type": "tuic",
  "server": "43.205.90.213",
  "server_port": 443,           ← UDP port (SAME as VLESS!)
  "tls": {
    "enabled": true,
    "insecure": true,
    "alpn": ["h3"]              ← HTTP/3 over QUIC
  }
}
```
- **Protocol**: UDP-based (QUIC)
- **Port**: 443 (shared with VLESS TCP)
- **Result**: ❌ Hangs, server receives nothing

### Working: VLESS (Mumbai)
```json
{
  "type": "vless",
  "server": "43.205.90.213",    ← SAME SERVER
  "server_port": 443,           ← TCP port 443
  "tls": { "reality": {...} }
}
```
- **Protocol**: TCP-based (REALITY)
- **Port**: 443 (shared with TUIC UDP)
- **Result**: ✅ Works (not currently tested but was default)

## Root Cause Hypotheses

### 🔴 HYPOTHESIS 1: Port Conflict (Most Likely)
**Both TUIC (UDP) and VLESS (TCP) use port 443 on the same server**

The AWS security group allows both:
- TCP 443 (for VLESS/REALITY)
- UDP 443 (for TUIC)

However, **only ONE service can truly bind to port 443 on the server**!

**Evidence**:
- VLESS service is likely running and bound to TCP :443
- TUIC service claims to listen on `[::]:443` (all interfaces, both TCP and UDP)
- But if VLESS is already running, TUIC might not actually bind successfully
- **Problem**: We changed the systemd user from `nobody` to `root`, which allowed TUIC to start, but didn't check if VLESS is also running!

### 🟡 HYPOTHESIS 2: UDP Blocked in Transit
Your ISP (Fortune Broadband, Myanmar) may be blocking:
- UDP port 443 specifically (QUIC/HTTPS)
- All QUIC traffic (common in censored regions)

**Evidence**:
- UDP traceroute times out at intermediate hop
- Server has NO logs of incoming TUIC packets
- TCP-based protocols (VLESS, Shadowsocks) work fine

### 🟡 HYPOTHESIS 3: NAT/Firewall UDP Timeout
UDP requires stateful tracking, which may be:
- Timing out too quickly
- Not mapping correctly for QUIC handshake
- Blocked by local firewall rules

## Diagnostic Commands Run

```bash
# Server status - TUIC running ✅
sudo systemctl status tuic
# Output: active (running), listening on [::]:443

# Server logs - NO incoming connections ❌
sudo journalctl -u tuic --since "5 minutes ago"
# Output: -- No entries --

# Client logs - Attempts but times out ⚠️
journalctl --user -u sing-box -n 50 | grep tuic
# Output: outbound/tuic[tuic-mumbai]: outbound connection (300ms delays)

# UDP traceroute - Times out ❌
traceroute -U -p 443 43.205.90.213
# Output: reaches hop 9, then * * *
```

## Solution Paths

### 🎯 Solution 1: Use Different Port for TUIC (RECOMMENDED)
**Change TUIC to use a non-conflicting UDP port**

#### On Server:
```json
{
  "server": "[::]:8443",  ← Change from 443
  ...
}
```

#### On Client:
```json
{
  "server": "43.205.90.213",
  "server_port": 8443,  ← Match server
  ...
}
```

**Why this works**:
- No port conflict with VLESS
- UDP 8443 already allowed in security group
- Clean separation of services

### 🎯 Solution 2: Stop VLESS, Use Only TUIC
**If you don't need VLESS, disable it**

```bash
# On server - check if VLESS is running
sudo systemctl status vless  # or whatever the service name is
sudo systemctl stop vless
```

### 🎯 Solution 3: Test UDP Reachability First
**Before fixing TUIC, verify UDP works at all**

```bash
# On server - run a simple UDP echo server
nc -u -l 8443

# On client - send test packet
echo "test" | nc -u 43.205.90.213 8443
```

If this fails, UDP is blocked by ISP/firewall.

### 🎯 Solution 4: Use TCP Fallback
**Some TUIC clients support TCP mode**

Check if Sing-Box TUIC supports `udp_relay_mode: "tcp"` mode.

## Next Steps Priority

1. **IMMEDIATE**: Check if VLESS is running on server (port conflict)
2. **TEST**: Change TUIC to port 8443 and retry
3. **VERIFY**: Test raw UDP connectivity to server
4. **FALLBACK**: If UDP is blocked, consider switching to TCP-based protocol only

## File Locations

- **Server Config**: `/etc/tuic/server.json`
- **Client Config**: `~/.config/sing-box/config.json`
- **Server Service**: `/etc/systemd/system/tuic.service`
- **Client Logs**: `journalctl --user -u sing-box`
