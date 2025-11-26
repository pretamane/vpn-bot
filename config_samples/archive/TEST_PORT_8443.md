# Quick Test Summary

## Changes Made
- ✅ TUIC server moved from UDP 443 → UDP 8443
- ✅ TUIC client updated to connect to port 8443  
- ✅ Server restarted and listening on [::]:8443

## Test Now
```bash
# Start TUIC connection
sbox use tuic-mumbai

# In another terminal, test if it works
curl ipinfo.io

# If it hangs again:
# 1. Press Ctrl+C on curl
# 2. Stop sing-box: sbox down
# 3. Check server logs for incoming connections
```

## Expected Outcomes

### ✅ Success Signs
- `curl ipinfo.io` shows Mumbai IP (43.205.90.213)
- This chat interface still works
- Server logs show incoming TUIC connections

### ❌ Failure Signs (Same as before)
- Connection hangs
- Chat stops working
- Server logs still show NO incoming connections
- **Conclusion**: Myanmar ISP is blocking ALL outbound UDP to international destinations

## Fallback Plan
If port 8443 also fails, the root cause is confirmed as **ISP UDP blocking**.

**Solutions if UDP is blocked**:
1. Use TCP-only protocols (VLESS/REALITY, Shadowsocks) ← Current working option
2. Try Hysteria2 (has better UDP obfuscation)
3. Use a UDP proxy/tunnel service
4. Switch ISP or use mobile data

## Files Modified
- Server: `/etc/tuic/server.json`
- Client: `~/.config/sing-box/config.json`
