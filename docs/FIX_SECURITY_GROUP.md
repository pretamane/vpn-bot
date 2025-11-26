# AWS Security Group - Fix Guide

## Problem Identified
✅ **UFW Firewall**: Port 9388 is OPEN (rule #5)  
✅ **Server Local Test**: Can connect to itself on 9388  
❌ **External Connection**: FAILING (timing out)

**Root Cause**: AWS Security Group is blocking port 9388 from internet.

## Step-by-Step Fix

### Step 1: Access AWS Console
1. Go to https://console.aws.amazon.com/ec2
2. Select **Region**: `ap-south-1` (Mumbai)
3. Click **Instances** in left sidebar
4. Find your instance: `43.205.90.213`

### Step 2: Find Security Group
1. Click on your instance
2. Scroll down to **Security** tab
3. Note the **Security Group** name (e.g., `launch-wizard-1` or `vpn-sg`)
4. Click on the Security Group name

### Step 3: Edit Inbound Rules
1. Click **Inbound rules** tab
2. Click **Edit inbound rules** button
3. Check if rule exists for port 9388:
   - **Type**: Custom TCP
   - **Port**: 9388
   - **Source**: 0.0.0.0/0

### Step 4: Add Missing Rule (If Not Present)
1. Click **Add rule**
2. Set:
   - **Type**: Custom TCP
   - **Port range**: 9388
   - **Source**: Custom → `0.0.0.0/0`
   - **Description**: Shadowsocks VPN
3. Click **Save rules**

### Step 5: Verify Existing Rules
You should have these ports open:
- ✅ 22 (SSH)
- ✅ 8443 (VLESS - if needed)
- ✅ 9388 (Shadowsocks) ← **THIS ONE MUST BE PRESENT**

## Screenshots to Help

### What Inbound Rules Should Look Like:
```
Type         Protocol  Port Range  Source          Description
SSH          TCP       22          0.0.0.0/0       SSH Access
Custom TCP   TCP       8443        0.0.0.0/0       VLESS VPN
Custom TCP   TCP       9388        0.0.0.0/0       Shadowsocks VPN
```

## Testing After Fix

### Test 1: Port Scan (From Your PC)
```bash
nc -zv 43.205.90.213 9388
# Should show: Connected
```

### Test 2: v2rayNG Key
Use the test key again:
```
ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNToxOThiODI4MC1hMzljLTQ2MzktYWM4ZS0zMzA4ODkzMTYzOGI=@43.205.90.213:9388#VerifyTest
```

## Common Issues

### "I don't have permission to edit Security Group"
- You need IAM permissions for `ec2:AuthorizeSecurityGroupIngress`
- Contact your AWS admin

### "Port 9388 rule exists but still not working"
- Check **Source** is `0.0.0.0/0` not restricted IP
- Check **Protocol** is TCP not UDP
- Verify you saved the changes

### "Security Group has too many rules"
- Remove unused ports (like old 8388 if 9388 is new)
- AWS allows 60 rules per SG

## Quick Check Commands

**From your computer**:
```bash
# Test if port is open
telnet 43.205.90.213 9388

# Or with nc
nc -zv 43.205.90.213 9388
```

**Expected output if working**:
```
Connection to 43.205.90.213 9388 port [tcp/*] succeeded!
```

## Alternative: Use AWS CLI

If you have AWS CLI configured:
```bash
# Get Security Group ID
aws ec2 describe-instances \
  --filters "Name=ip-address,Values=43.205.90.213" \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --region ap-south-1

# Add rule (replace sg-xxxxxx with your SG ID)
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxx \
  --protocol tcp \
  --port 9388 \
  --cidr 0.0.0.0/0 \
  --region ap-south-1
```

## After Fixing

Once port 9388 is open in AWS Security Group:
1. **All existing keys will work immediately**
2. **No need to restart sing-box**
3. **Test with v2rayNG**
4. **Generate new keys via Telegram bot**

The server is ready - just waiting for AWS firewall to allow traffic!
