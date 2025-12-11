#!/bin/bash
# Deploy updated files to AWS via SSM

INSTANCE_ID="i-071f6e8701ed1ad2c"

echo "=== Deploying notifications.py ===" 
ENCODED=$(base64 -w 0 src/bot/notifications.py)
CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[\"echo '$ENCODED' | base64 -d > /home/ubuntu/vpn-bot/src/bot/notifications.py\"]" \
  --output json | jq -r '.Command.CommandId')
sleep 3
aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" | jq -r '.Status'

echo "=== Deploying database.py ==="
ENCODED=$(base64 -w 0 src/db/database.py)
CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[\"echo '$ENCODED' | base64 -d > /home/ubuntu/vpn-bot/src/db/database.py\"]" \
  --output json | jq -r '.Command.CommandId')
sleep 3
aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" | jq -r '.Status'

echo "=== Deploying server.py ==="
ENCODED=$(base64 -w 0 src/api/server.py)
CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[\"echo '$ENCODED' | base64 -d > /home/ubuntu/vpn-bot/src/api/server.py\"]" \
  --output json | jq -r '.Command.CommandId')
sleep 3
aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" | jq -r '.Status'

echo "=== Deploying watchdog service.py ==="
ENCODED=$(base64 -w 0 src/watchdog/service.py)
CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[\"echo '$ENCODED' | base64 -d > /home/ubuntu/vpn-bot/watchdog/service.py\"]" \
  --output json | jq -r '.Command.CommandId')
sleep 3
aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" | jq -r '.Status'

echo "=== Running database migrations ==="
CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["cd /home/ubuntu/vpn-bot && python3 -c \"from src.db.database import init_db; init_db(); print(\"Database migrated\")\""]' \
  --output json | jq -r '.Command.CommandId')
sleep 5
aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" | jq -r '.StandardOutputContent'

echo "=== Restarting API server ==="
CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["sudo systemctl restart mmvpn-api && sleep 2 && systemctl status mmvpn-api"]' \
  --output json | jq -r '.Command.CommandId')
sleep 5
aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" | jq -r '.StandardOutputContent'

echo "=== Restarting watchdog ==="
CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["sudo systemctl restart vpn-watchdog && sleep 2 && systemctl status vpn-watchdog"]' \
  --output json | jq -r '.Command.CommandId')
sleep 5
aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" | jq -r '.StandardOutputContent'

echo "=== Deployment Complete ===" 
