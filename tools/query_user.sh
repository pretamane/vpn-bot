#!/bin/bash
INSTANCE_ID="i-071f6e8701ed1ad2c"
REGION="us-east-1"
QUERY="SELECT uuid, username, email, protocol, is_active, created_at FROM users WHERE email LIKE '%paypalusbychrisnapier%' OR username LIKE '%paypalusbychrisnapier%';"

echo "Running query: $QUERY"

CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[\"sqlite3 -header -column /home/ubuntu/vpn-bot/src/db/vpn_bot.db \\\"$QUERY\\\"\"]" \
  --region "$REGION" \
  --output json | jq -r '.Command.CommandId')

echo "Command ID: $CMD_ID"
sleep 5

aws ssm get-command-invocation \
  --command-id "$CMD_ID" \
  --instance-id "$INSTANCE_ID" \
  --region "$REGION" \
  --output json | jq -r '.StandardOutputContent'
