#!/bin/bash
# Check AWS Bandwidth Usage for Mumbai VPN

INSTANCE_ID="i-071f6e8701ed1ad2c"
REGION="ap-south-1"

echo "========================================"
echo "🇮🇳 AWS Mumbai VPN - Bandwidth Usage"
echo "========================================"
echo "Checking data transfer (OUT) for last 30 days..."

USAGE=$(aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name NetworkOut \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --start-time $(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 2592000 \
  --statistics Sum \
  --region $REGION \
  --query 'Datapoints[0].Sum' \
  --output text)

if [ "$USAGE" == "None" ] || [ -z "$USAGE" ]; then
    echo "Usage: 0.00 GB"
    PERCENT=0
else
    # Calculate GB
    GB=$(echo $USAGE | awk '{printf "%.2f", $1/1024/1024/1024}')
    echo "Used:  $GB GB"
    
    # Calculate percentage of 100GB Free Tier
    PERCENT=$(echo $USAGE | awk '{printf "%.0f", ($1/1024/1024/1024 / 100) * 100}')
fi

echo "Limit: 100.00 GB (Free Tier)"
echo "========================================"

# Progress bar
BAR_LENGTH=20
FILLED_LENGTH=$((PERCENT * BAR_LENGTH / 100))
UNFILLED_LENGTH=$((BAR_LENGTH - FILLED_LENGTH))

printf "Status: ["
for ((i=0; i<FILLED_LENGTH; i++)); do printf "#"; done
for ((i=0; i<UNFILLED_LENGTH; i++)); do printf "."; done
printf "] %d%%\n" $PERCENT

if [ $PERCENT -ge 90 ]; then
    echo "⚠️ WARNING: You are approaching the free tier limit!"
elif [ $PERCENT -ge 50 ]; then
    echo "ℹ️ You have used over half your monthly allowance."
else
    echo "✅ Usage is within safe limits."
fi
echo "========================================"
