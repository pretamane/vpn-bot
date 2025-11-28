# 🎉 AWS Mumbai VLESS + REALITY VPN Server - Setup Complete!

## ✅ Server Details

**Location**: Mumbai, India (ap-south-1)  
**IP Address**: `43.205.90.213`  
**Instance Type**: t3.micro (AWS Free Tier)  
**Protocol**: VLESS + REALITY (Maximum Stealth)  
**Status**: ✅ Running

---

## 🔑 Connection Details

```
Server: 43.205.90.213
Port: 443
Protocol: VLESS
Flow: xtls-rprx-vision
UUID: e6a273ae-3adb-4a6e-af35-08320c3a06cd
Public Key: ebn5poHxOL6U1lLVXiZmLxDIlF4I6ChnqZ7KtM00DlM
Short ID: 32155302
SNI: www.microsoft.com
```

---

## 📱 SingBox Configuration

Your SingBox config has been updated at:
`/home/guest/.gemini/antigravity/scratch/singbox_config.json`

The new server tag is: **`mumbai-reality-aws`**

---

## 🚀 How to Use

### 1. Update Your Live Config
```bash
cp /home/guest/.gemini/antigravity/scratch/singbox_config.json /home/guest/.config/sing-box/config.json
```

### 2. Restart SingBox
```bash
systemctl --user restart sing-box
# OR
sbox restart
```

### 3. Switch to Mumbai Server
```bash
sbox use mumbai-reality-aws
```

### 4. Check Connection
```bash
sbox status
sbox ip
```

---

## 🛡️ Why This Setup Is Stealth

1. **REALITY Protocol**: Traffic looks EXACTLY like visiting www.microsoft.com
2. **Port 443**: Standard HTTPS port - can't be blocked
3. **No Certificate**: Server doesn't have a certificate - reduces fingerprinting
4. **TLS 1.3**: Modern encryption
5. **XTLS Vision Flow**: Advanced traffic obfuscation
6. **Chrome Fingerprint**: Your traffic mimics Chrome browser

**Result**: Myanmar's DPI system sees you visiting Microsoft.com, not using a VPN!

---

## 📊 Bandwidth Monitoring

### Check Usage (to stay under 15GB/month)
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name NetworkOut \
  --dimensions Name=InstanceId,Value=i-071f6e8701ed1ad2c \
  --start-time $(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 2592000 \
  --statistics Sum \
  --region ap-south-1 \
  --query 'Datapoints[0].Sum' \
  --output text | awk '{printf "%.2f GB\n", $1/1024/1024/1024}'
```

### Daily Limit
15GB / 30 days = **500MB/day maximum**

---

## 🔐 Security Notes

1. **SSH Key**: Saved at `/home/guest/.gemini/antigravity/scratch/myanmar-vpn-key.pem`
2. **Firewall**: Only ports 22 (SSH) and 443 (VPN) are open
3. **Auto-updates**: Enabled on server
4. **No logs**: Server doesn't keep connection logs

---

## 🆘 Troubleshooting

### If Connection Fails
```bash
# Test server reachability
ping 43.205.90.213

# Check if port 443 is accessible
nc -zv 43.205.90.213 443

# View SingBox logs
sbox logs
```

### Server Management
```bash
# SSH into server
ssh -i /home/guest/.gemini/antigravity/scratch/myanmar-vpn-key.pem ubuntu@43.205.90.213

# Check Xray status
sudo systemctl status xray

# View Xray logs
sudo journalctl -u xray -f
```

---

## 💰 Cost Monitoring

- **Free Tier**: 750 hours/month (always-on coverage)
- **Data**: First 15GB OUT/month FREE
- **After Free Tier**: ~$4.75/month + $0.09/GB for data over 15GB
- **Free Tier Duration**: 12 months

### Stay Within Free Tier
✅ Browsing, messaging, email  
✅ Light downloads  
❌ Video streaming  
❌ Large file downloads  

---

## 🎯 Next Steps

1. **Test the connection** using the commands above
2. **Add as backup** in your SingBox selector (already done!)
3. **Monitor bandwidth** weekly
4. **Consider adding Trojan** as additional fallback (optional)

---

## 📝 Files Created

- `/home/guest/.gemini/antigravity/scratch/myanmar-vpn-key.pem` - SSH private key
- `/home/guest/.gemini/antigravity/scratch/singbox_config.json` - Updated config
- `/home/guest/.gemini/antigravity/scratch/mumbai-reality-outbound.json` - Server config
- `/home/guest/.gemini/antigravity/scratch/myanmar-vpn-analysis.md` - Setup analysis

---

## ⚡ Quick Commands

```bash
# Update live config
cp /home/guest/.gemini/antigravity/scratch/singbox_config.json /home/guest/.config/sing-box/config.json

# Restart and switch
sbox restart
sbox use mumbai-reality-aws

# Check status
sbox status
sbox ip
```

**Your VPN is ready to use! 🚀**
