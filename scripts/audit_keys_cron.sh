#!/bin/bash
# Daily audit wrapper to detect phantom keys
# Run via cron: 0 2 * * * /home/ubuntu/vpn-bot/scripts/audit_keys_cron.sh

CD=/home/ubuntu/vpn-bot
LOG=/tmp/audit_last_run.log

cd $CD
python3 scripts/audit_keys.py > $LOG 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "[$(date)] ⚠️  Phantom keys detected! Exit code: $EXIT_CODE" >> /tmp/phantom_keys_alert.log
    # Can add email/telegram notification here
    # echo "Phantom keys found! See $LOG" | mail -s "VPN Bot Alert" admin@example.com
fi

exit $EXIT_CODE
