# Server Services Status Report
**Generated:** 2025-11-22  
**Server IP:** 43.205.90.213  
**Checked via:** SSH connection

## Executive Summary

**Active VPN Software:** SingBox (running)  
**Inactive Software:** Xray (stopped/disabled)  
**Status:** ✅ SingBox is operational on port 443 (VLESS + REALITY)  
**Missing Services:** TUIC and SOCKS5 servers are NOT configured

---

## Active Services

### 1. SingBox Service
- **Status:** ✅ **ACTIVE (running)**
- **Service Name:** `sing-box.service`
- **Process ID:** 34047
- **Started:** Sat 2025-11-22 06:41:12 UTC (running for 1h 46min)
- **Config File:** `/etc/sing-box/config.json`
- **Memory Usage:** 11.6M (peak: 21.8M)
- **CPU Time:** 1.604s

### 2. SingBox Watchdog Service
- **Status:** ✅ **ACTIVE (running)**
- **Service Name:** `singbox-watchdog.service`
- **Process ID:** 15039
- **Started:** Fri 2025-11-21 22:49:14 UTC (running for 9h)
- **Script:** `/usr/local/bin/watchdog.py`
- **Memory Usage:** 17.8M (peak: 20.2M)
- **CPU Time:** 1min 42.551s
- **Purpose:** Traffic monitoring and speed limiting

### 3. Xray Service
- **Status:** ❌ **INACTIVE (stopped/disabled)**
- **Service Name:** `xray.service`
- **Last Active:** Nov 21 22:29:15 UTC (stopped)
- **Config File:** `/usr/local/etc/xray/config.json` (exists but not used)
- **Note:** Xray was previously running but has been replaced by SingBox

---

## Active Ports

### Listening Ports:
- **Port 443 (TCP):** ✅ **LISTENING** - SingBox VLESS + REALITY
  - Process: sing-box (PID 34047)
  - Protocol: VLESS + REALITY
  - IPv6 listener: `*:443`

### Not Listening:
- **Port 8443 (UDP):** ❌ **NOT LISTENING** - TUIC server not configured
- **Port 1080 (TCP):** ❌ **NOT LISTENING** - SOCKS5 server not configured

### Other Services:
- **Port 22 (TCP):** SSH daemon
- **Port 53 (TCP):** DNS resolver (systemd-resolve)
- **Port 8388 (TCP):** Shadowsocks server (ssserver) - separate service

---

## Current Server Configuration

### Active Config: `/etc/sing-box/config.json`

**Protocol:** VLESS + REALITY  
**Port:** 443  
**Server Name:** www.microsoft.com

**Credentials:**
- **UUID:** `98132a92-dfcc-445f-a73e-aa7dddab3398`
- **Flow:** `xtls-rprx-vision`
- **REALITY Private Key:** `SEHAuZ6QlJYk0CyKO5ONwEWQtIG-pbzn7FmaSqH7EEw`
- **REALITY Public Key:** `O39-17lHzuq1bbpzUDcbwnzbBtd0P140Myeynito8Go` (from documentation, needs verification)
- **REALITY Short ID:** `e69f7ecf`

**Inbounds:**
- Only VLESS + REALITY on port 443
- No TUIC inbound configured
- No SOCKS5 inbound configured

**Outbounds:**
- Direct connection to internet

---

## Inactive Config: `/usr/local/etc/xray/config.json`

**Status:** File exists but service is stopped

**Old Credentials (from Xray config):**
- **UUID:** `e6a273ae-3adb-4a6e-af35-08320c3a06cd` (OLD - not in use)
- **REALITY Private Key:** `iBHcIxAjtRQ0UA8q2puc5otTYVMGE_pswGH3gzNyJ0o` (OLD - not in use)
- **REALITY Short ID:** `32155302` (OLD - not in use)

**Note:** These are the OLD credentials that appear in most client configs but are NOT active on the server.

---

## Client-Server Alignment Status

### ✅ CORRECT Credentials (Active on Server):
- **UUID:** `98132a92-dfcc-445f-a73e-aa7dddab3398`
- **REALITY Public Key:** Must match private key `SEHAuZ6QlJYk0CyKO5ONwEWQtIG-pbzn7FmaSqH7EEw`
- **REALITY Short ID:** `e69f7ecf`

### ❌ INCORRECT Credentials (In Client Configs):
- **UUID:** `e6a273ae-3adb-4a6e-af35-08320c3a06cd` (OLD Xray UUID)
- **REALITY Public Key:** `ebn5poHxOL6U1lLVXiZmLxDIlF4I6ChnqZ7KtM00DlM` (OLD key)
- **REALITY Short ID:** `32155302` (OLD short ID)

**Client Config Status:**
- `client-test.json`: ✅ Uses CORRECT credentials
- `fixed_config.json`: ❌ Uses OLD credentials
- `singbox_config.json`: ❌ Uses OLD credentials
- `user-config-backup.json`: ❌ Likely uses OLD credentials

---

## Missing Services

### 1. TUIC Server
- **Status:** ❌ **NOT CONFIGURED**
- **Port:** 8443 (UDP) - Not listening
- **Action Required:** Add TUIC inbound to `/etc/sing-box/config.json`

### 2. SOCKS5 Server
- **Status:** ❌ **NOT CONFIGURED**
- **Port:** 1080 (TCP) - Not listening
- **Action Required:** Add SOCKS5 inbound to `/etc/sing-box/config.json`

---

## Recommendations

1. **Align Client Configs:**
   - Update all client configs to use the CORRECT credentials:
     - UUID: `98132a92-dfcc-445f-a73e-aa7dddab3398`
     - REALITY Public Key: (needs to be derived from private key)
     - Short ID: `e69f7ecf`

2. **Add Missing Protocols:**
   - Configure TUIC server on port 8443
   - Configure SOCKS5 server on port 1080
   - Update firewall to allow ports 8443 (UDP) and 1080 (TCP)

3. **Verify REALITY Public Key:**
   - The server has private key `SEHAuZ6QlJYk0CyKO5ONwEWQtIG-pbzn7FmaSqH7EEw`
   - Documentation shows public key `O39-17lHzuq1bbpzUDcbwnzbBtd0P140Myeynito8Go`
   - **IMPORTANT:** Need to verify these keypair match (private/public key relationship)
   - If they don't match, server may have been reconfigured and client configs need updating

4. **Clean Up:**
   - Remove or archive old Xray config (not in use)
   - Document which credentials are active

---

## Service Management Commands

### Check SingBox Status
```bash
ssh -i myanmar-vpn-key.pem ubuntu@43.205.90.213 "sudo systemctl status sing-box"
```

### View SingBox Logs
```bash
ssh -i myanmar-vpn-key.pem ubuntu@43.205.90.213 "sudo tail -f /var/log/singbox/access.log"
```

### Restart SingBox
```bash
ssh -i myanmar-vpn-key.pem ubuntu@43.205.90.213 "sudo systemctl restart sing-box"
```

### Check Watchdog Status
```bash
ssh -i myanmar-vpn-key.pem ubuntu@43.205.90.213 "sudo systemctl status singbox-watchdog"
```

---

## Summary

**What's Working:**
- ✅ SingBox is running and operational
- ✅ VLESS + REALITY on port 443 is active
- ✅ Watchdog service is monitoring traffic
- ✅ Server is accessible and responding

**What's Not Working:**
- ❌ Most client configs use outdated credentials
- ❌ TUIC server not configured
- ❌ SOCKS5 server not configured

**Next Steps:**
1. Generate REALITY public key from private key
2. Update all client configs with correct credentials
3. Add TUIC and SOCKS5 server configurations
4. Test all three protocols end-to-end

