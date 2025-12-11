#!/bin/bash
INSTANCE_ID="i-071f6e8701ed1ad2c"
REGION="ap-south-1"
EMAIL="thawzin@myday.group"

# Update the protocol to 'account' for this user
QUERY="UPDATE users SET protocol = 'account' WHERE email = '$EMAIL';"

echo "Fixing user $EMAIL..."

CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[\"sqlite3 /home/ubuntu/vpn-bot/src/db/vpn_bot.db \\\"$QUERY\\\"\"]" \
  --region "$REGION" \
  --output json | jq -r '.Command.CommandId')

echo "Command ID: $CMD_ID"
sleep 5

aws ssm get-command-invocation \
  --command-id "$CMD_ID" \
  --instance-id "$INSTANCE_ID" \
  --region "$REGION" \
  --output json | jq -r '.StandardOutputContent'
