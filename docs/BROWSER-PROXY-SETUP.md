# Browser Proxy Setup - Myanmar VPN

## Problem
Your VPN is working, but your browser doesn't know to use it!

## Quick Test (Confirmed Working)
```bash
curl -x socks5h://127.0.0.1:10808 https://www.facebook.com
# ✅ This works - Facebook is accessible via proxy
```

---

## Option 1: Firefox (Recommended)

### Manual Configuration
1. Open Firefox
2. Go to **Settings** (☰ menu → Settings)
3. Scroll down to **Network Settings** → Click **Settings**
4. Select **Manual proxy configuration**
5. Set:
   - **SOCKS Host**: `127.0.0.1`
   - **Port**: `10808`
   - Select: **SOCKS v5**
   - ✅ Check: **Proxy DNS when using SOCKS v5**
6. Click **OK**

### Quick Command
```bash
firefox --new-instance -P vpn &
```
Then configure manually as above.

---

## Option 2: Chrome/Chromium

### Launch with Proxy
```bash
# Chrome
google-chrome --proxy-server="socks5://127.0.0.1:10808" &

# Chromium
chromium-browser --proxy-server="socks5://127.0.0.1:10808" &
```

### System Proxy (All Apps)
```bash
# Set environment variables
export http_proxy="socks5h://127.0.0.1:10808"
export https_proxy="socks5h://127.0.0.1:10808"
export all_proxy="socks5h://127.0.0.1:10808"

# Then launch browser
google-chrome &
```

---

## Option 3: Browser Extension (FoxyProxy)

### Firefox
1. Install **FoxyProxy Standard**: https://addons.mozilla.org/firefox/addon/foxyproxy-standard/
2. Add proxy:
   - Type: SOCKS5
   - Host: 127.0.0.1
   - Port: 10808
3. Enable proxy

### Chrome
1. Install **Proxy SwitchyOmega**: https://chrome.google.com/webstore/detail/proxy-switchyomega/
2. Create new profile:
   - Protocol: SOCKS5
   - Server: 127.0.0.1
   - Port: 10808
3. Apply changes

---

## Option 4: System-Wide Proxy (GNOME/KDE)

### GNOME Settings
```bash
gsettings set org.gnome.system.proxy mode 'manual'
gsettings set org.gnome.system.proxy.socks host '127.0.0.1'
gsettings set org.gnome.system.proxy.socks port 10808
```

### Reset
```bash
gsettings set org.gnome.system.proxy mode 'none'
```

---

## Verification Steps

### 1. Check Your IP
Open browser and visit:
- https://api.ipify.org
- Should show: **43.205.90.213** (AWS India)

### 2. Test Facebook
- Visit: https://www.facebook.com
- Should load normally (bypassing Myanmar censorship)

### 3. Check DNS Leaks
- Visit: https://dnsleaktest.com
- Should show AWS/India location

---

## Quick Start Script

Save this as `start-vpn-browser.sh`:
```bash
#!/bin/bash
# Make sure SingBox client is running
if ! pgrep -f "sing-box.*client-test" > /dev/null; then
    /usr/local/bin/sing-box run -c /home/guest/.gemini/antigravity/scratch/client-test.json &
    sleep 2
fi

# Launch Firefox with proxy
firefox --new-instance -P vpn --proxy-server="socks5://127.0.0.1:10808" &
```

Make executable:
```bash
chmod +x start-vpn-browser.sh
./start-vpn-browser.sh
```

---

## Troubleshooting

### Browser still shows Myanmar IP?
- Make sure you selected **SOCKS v5** (not HTTP proxy)
- Enable **Proxy DNS when using SOCKS v5**
- Restart browser after changing settings

### Connection refused?
```bash
# Check if client is running
ps aux | grep sing-box | grep client-test

# If not running, start it:
/usr/local/bin/sing-box run -c /home/guest/.gemini/antigravity/scratch/client-test.json &
```

### Slow connection?
- Normal - traffic routes Myanmar → AWS India → Internet
- Speed: ~24 Mbps (tested)

---

## Summary

**Current Status**:
- ✅ VPN Tunnel: Working
- ✅ SOCKS Proxy: Running on 127.0.0.1:10808
- ❌ Browser: Not configured

**Action Required**: Configure browser to use SOCKS5 proxy at `127.0.0.1:10808`
