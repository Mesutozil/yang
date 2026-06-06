#!/usr/bin/env bash
# 仅保留第一个钉钉 Webhook，并测试推送
set -euo pipefail

APP_DIR="/home/root/yangq"
WEBHOOK1="https://oapi.dingtalk.com/robot/send?access_token=8fa813f60c4a5cc598f6734ab4b34258769cc79e48dc934dd35fcca5c0041753"

cd "$APP_DIR"

cat > .env << EOF
NOTIFY_CHANNEL=dingtalk

DINGTALK_WEBHOOK_URL=${WEBHOOK1}
DINGTALK_SECRET=

KEYWORDS=锂电,新能源,碳酸锂
POLL_INTERVAL_SEC=60
CLS_RN=50
STATE_DB_PATH=data/state.db
EOF
chmod 600 .env

echo ">>> .env 已更新（仅第一个钉钉 Webhook）"
grep DINGTALK_WEBHOOK_URL .env

source .venv/bin/activate
echo ">>> 测试拉取数据"
python main.py --once --dry-run

echo ">>> 测试钉钉推送"
python main.py --test-notify

echo ">>> 重启监测服务"
systemctl restart monitorkeyword
systemctl status monitorkeyword --no-pager
