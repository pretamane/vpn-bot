# SingBox Client Setup Options

## Current Situation

You have **TWO** SingBox client setups:

### Option 1: Existing Systemd Service (Currently Failing)
- **Location**: `/home/guest/.config/sing-box/config.json`
- **Service**: `systemctl --user {start|stop|status} sing-box`
- **Aliases**: `sbstart`, `sbstop`, `sbstatus`, `sblogs`
- **Type**: TUN mode (system-wide VPN)
- **Proxy Port**: 7897 (mixed HTTP/SOCKS)
- **Status**: ❌ **Failing** - config has syntax error in DNS section
- **Servers**: Multiple outbounds including OLD `mumbai-reality-aws` (wrong UUID/keys)

### Option 2: New Simple Client (Working)
- **Location**: `/home/guest/.gemini/antigravity/scratch/client-test.json`
- **Start**: `sing-box run -c /path/to/client-test.json`
- **Type**: SOCKS5 proxy only
- **Proxy Port**: 10808
- **Status**: ✅ **Working** - tested successfully
- **Server**: Mumbai AWS with correct VLESS+REALITY config

---

## What's Wrong with Your Existing Setup?

**Line 159-177** has `mumbai-reality-aws` but with **WRONG credentials**:
```json
{
  "tag": "mumbai-reality-aws",
  "uuid": "e6a273ae-3adb-4a6e-af35-08320c3a06cd",  ← OLD UUID
  "public_key": "ebn5poHxOL6U1lLVXiZmLxDIlF4I6ChnqZ7KtM00DlM",  ← OLD KEY
  "short_id": "32155302"  ← OLD ID
}
```

**Should be:**
```json
{
  "tag": "mumbai-reality-aws",
  "uuid": "98132a92-dfcc-445f-a73e-aa7dddab3398",  ← CORRECT UUID
  "public_key": "O39-17lHzuq1bbpzUDcbwnzbBtd0P140Myeynito8Go",  ← CORRECT KEY
  "short_id": "e69f7ecf"  ← CORRECT ID
}
```

---

## Which Option Do You Want?

### Option A: Fix Existing System Service
**Advantages:**
- ✅ Use your familiar aliases (`sbstart`, `sbstatus`)
- ✅ TUN mode (ALL apps use VPN automatically)
- ✅ Mixed proxy on port 7897

**Steps:**
1. Fix DNS config syntax error
2. Update `mumbai-reality-aws` with correct credentials
3. Set `mumbai-reality-aws` as default
4. Restart service: `sbstart`

### Option B: Keep New Simple Client
**Advantages:**
- ✅ Already working
- ✅ Simple SOCKS5 on port 10808
- ✅ No root required

**Steps:**
1. Keep using: `sing-box run -c client-test.json &`
2. Configure browser to use SOCKS5 127.0.0.1:10808

---

##Decision Needed

Which do you prefer?
- **Option A**: Fix systemd service (TUN mode, `sbstart` commands)
- **Option B**: Use simple client (already working, port 10808)
