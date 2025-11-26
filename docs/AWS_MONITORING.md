# AWS Monitoring Guide

## Built-in AWS Monitoring Tools

### 1. CloudWatch (Primary Monitoring Tool)

**Access**: AWS Console → CloudWatch → Dashboards/Metrics/Logs

#### **EC2 Instance Metrics** (Free Tier)
Monitor your t3.nano instance:
- **CPU Utilization** - See if VPN traffic is maxing out CPU
- **Network In/Out** - Total bandwidth usage
- **Disk Read/Write** - Storage performance
- **Status Checks** - Instance health

**To View**:
```
AWS Console → EC2 → Select your instance → Monitoring tab
```

#### **Custom Metrics** (Optional - Requires Agent)
Install CloudWatch Agent for detailed metrics:
- Memory usage (RAM)
- Disk space usage
- Per-process CPU/memory

#### **CloudWatch Logs** (Recommended)
Stream your logs to CloudWatch:

**Setup**:
```bash
# Install CloudWatch agent on EC2
sudo yum install amazon-cloudwatch-agent  # Amazon Linux
sudo apt install amazon-cloudwatch-agent   # Ubuntu

# Configure to send logs
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
```

**Logs to Stream**:
- `/var/log/singbox/access.log` - VPN connections
- `journalctl -u vpn-bot` - Bot activity
- `journalctl -u watchdog` - Bandwidth monitoring
- `journalctl -u sing-box` - VPN server logs

### 2. VPC Flow Logs

**Purpose**: See all network traffic to/from your instance

**Setup**:
```
AWS Console → VPC → Flow Logs → Create Flow Log
- Resource: Select your VPC or subnet
- Destination: CloudWatch Logs or S3
```

**What You'll See**:
- Source/destination IPs
- Ports being accessed
- Bytes transferred
- Connection accept/reject

**Use Cases**:
- Detect DDoS attacks
- See which countries connect to you
- Identify port scanning attempts

### 3. Cost Explorer

**Access**: AWS Console → Billing → Cost Explorer

**Monitor**:
- Daily spend on EC2 instance
- Data transfer costs (egress bandwidth)
- Predict monthly bill

**Alerts**: Set billing alarms in CloudWatch

### 4. CloudWatch Alarms

**Recommended Alarms**:

#### **High CPU Usage**
```
Metric: CPUUtilization
Threshold: > 80% for 5 minutes
Action: Send SNS notification to your email
```

#### **High Network Out** (Bandwidth abuse)
```
Metric: NetworkOut
Threshold: > 10 GB/hour
Action: Email alert
```

#### **Instance Status Check Failed**
```
Metric: StatusCheckFailed
Threshold: >= 1
Action: Email alert + auto-restart instance
```

**Setup**:
```
CloudWatch → Alarms → Create Alarm → Select Metric → Set Threshold
```

### 5. Systems Manager (Session Manager)

**Purpose**: SSH without opening port 22 publicly

**Setup**:
1. Attach IAM role to EC2 instance
2. Install SSM agent (pre-installed on most AMIs)
3. Connect via AWS Console → Systems Manager → Session Manager

**Benefits**:
- No exposed SSH port
- All sessions logged
- Audit trail in CloudTrail

### 6. CloudTrail (API Activity)

**Purpose**: See who did what in your AWS account

**Tracks**:
- Instance start/stop
- Security group changes
- IAM changes

**Access**: AWS Console → CloudTrail → Event History

## Custom Monitoring Dashboard

### Option A: CloudWatch Dashboard (AWS Native)

**Create Custom Dashboard**:
```
CloudWatch → Dashboards → Create Dashboard
Add Widgets:
- Line graph: CPU Utilization
- Number: NetworkOut (current hour)
- Line graph: Disk space
- Log widget: Recent VPN connections from access.log
```

**Cost**: Free for basic metrics, ~$3/month for custom dashboard

### Option B: Grafana + Prometheus (Self-Hosted)

Install on your EC2 or separate instance:
- **Prometheus**: Scrape metrics from sing-box, system
- **Grafana**: Beautiful dashboards
- **Node Exporter**: System metrics

**Benefits**:
- Much prettier than CloudWatch
- More customizable
- Can show sing-box stats via V2Ray API

**Downside**: Uses resources on your t3.nano

## Quick Monitoring Commands (SSH)

**Current Connections**:
```bash
watch -n 5 "netstat -tn | grep -E ':(9388|8443)' | grep ESTABLISHED | wc -l"
```

**Bandwidth Today**:
```bash
# Outbound traffic (approximate)
cat /proc/net/dev | grep eth0 | awk '{print $10/(1024**3)" GB sent"}'
```

**Top Users by Bandwidth** (via database):
```bash
sqlite3 /home/ubuntu/vpn-bot/db/vpn_bot.db "
SELECT username, ROUND(SUM(bytes_used)/(1024.0**3),2) as total_gb
FROM usage_logs JOIN users ON usage_logs.uuid=users.uuid
GROUP BY username
ORDER BY total_gb DESC
LIMIT 10;
"
```

**Service Health**:
```bash
systemctl status sing-box vpn-bot watchdog --no-pager
```

## Recommended Setup

**Minimal (Free)**:
1. Enable EC2 basic monitoring (already on)
2. Set CloudWatch alarm for high CPU
3. Check AWS Cost Explorer weekly

**Standard ($5-10/month)**:
1. Stream logs to CloudWatch Logs
2. Create custom CloudWatch dashboard
3. Enable VPC Flow Logs
4. Set up billing alerts

**Advanced (Self-hosted)**:
1. Install Grafana + Prometheus
2. Custom dashboards for VPN stats
3. Alerting via Telegram bot
4. Integrate with watchdog service

## CloudWatch Logs Setup (Step-by-Step)

### 1. Create Log Group
```bash
aws logs create-log-group --log-group-name /vpn-bot/sing-box
aws logs create-log-group --log-group-name /vpn-bot/bot
aws logs create-log-group --log-group-name /vpn-bot/watchdog
```

### 2. Install CloudWatch Agent
```bash
ssh ubuntu@43.205.90.213
sudo apt install amazon-cloudwatch-agent -y
```

### 3. Configure Agent
```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/singbox/access.log",
            "log_group_name": "/vpn-bot/sing-box",
            "log_stream_name": "{instance_id}"
          }
        ]
      },
      "journal": {
        "log_group_name": "/vpn-bot/systemd",
        "log_stream_name": "{instance_id}",
        "filters": {
          "systemd_unit": ["vpn-bot.service", "watchdog.service", "sing-box.service"]
        }
      }
    }
  }
}
```

### 4. Start Agent
```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -c file:/path/to/config.json -s
```

Now all logs are in CloudWatch - searchable, alertable, and persistent!
