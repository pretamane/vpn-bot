# SingBox VLESS+REALITY Connection Guide

## ✅ Server Status
- **Server Running**: YES
- **Protocol**: VLESS + Vision + REALITY
- **Port**: 443

## 🔑 Updated Credentials

> [!IMPORTANT]
> **The REALITY keypair has been corrected. Use these updated credentials:**

- **Server IP**: `43.205.90.213`
- **UUID**: `98132a92-dfcc-445f-a73e-aa7dddab3398`
- **Public Key**: `O39-17lHzuq1bbpzUDcbwnzbBtd0P140Myeynito8Go`
- **Short ID**: `e69f7ecf`
- **Server Name (SNI)**: `www.microsoft.com`
- **Flow**: `xtls-rprx-vision`

## 📱 SingBox Client Configuration

```json
{
  "type": "vless",
  "tag": "mumbai-reality",
  "server": "43.205.90.213",
  "server_port": 443,
  "uuid": "98132a92-dfcc-445f-a73e-aa7dddab3398",
  "flow": "xtls-rprx-vision",
  "tls": {
    "enabled": true,
    "server_name": "www.microsoft.com",
    "utls": {
      "enabled": true,
      "fingerprint": "chrome"
    },
    "reality": {
      "enabled": true,
      "public_key": "O39-17lHzuq1bbpzUDcbwnzbBtd0P140Myeynito8Go",
      "short_id": "e69f7ecf"
    }
  }
}
```

## 🔗 VLESS URI (for v2rayNG/NekoRay)

```
vless://98132a92-dfcc-445f-a73e-aa7dddab3398@YOUR_SERVER_IP:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=www.microsoft.com&fp=chrome&pbk=O39-17lHzuq1bbpzUDcbwnzbBtd0P140Myeynito8Go&sid=e69f7ecf&type=tcp&headerType=none#Mumbai-REALITY
```

## 🛡️ Watchdog Features
- **Max Devices**: 5 concurrent connections per UUID
- **Max Speed**: 8 Mbps (monitored via logs)
- **Service**: `sing-box-watchdog.service` (running)

## 🔧 Server Management

### View Logs
```bash
sudo tail -f /var/log/singbox/access.log
```

### Restart Server
```bash
sudo systemctl restart sing-box sing-box-watchdog
```

### Check Status
```bash
sudo systemctl status sing-box sing-box-watchdog
```
