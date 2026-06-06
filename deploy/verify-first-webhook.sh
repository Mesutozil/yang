#!/usr/bin/env bash
# 一键：更新代码 → 仅第一个钉钉 Webhook → 测试推送 → 重启服务
set -euo pipefail

APP_DIR="/home/root/yangq"
REPO_URL="https://github.com/Mesutozil/yang.git"
WEBHOOK1="https://oapi.dingtalk.com/robot/send?access_token=8fa813f60c4a5cc598f6734ab4b34258769cc79e48dc934dd35fcca5c0041753"

echo "========== 1/6 准备目录与代码 =========="
mkdir -p /home/root
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git

if [[ -d "$APP_DIR/.git" ]]; then
  cd "$APP_DIR"
  git pull origin main
else
  git clone "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

echo "========== 2/6 写入 .env（仅第一个钉钉） =========="
cat > .env << EOF
NOTIFY_CHANNEL=dingtalk

DINGTALK_WEBHOOK_URL=${WEBHOOK1}
DINGTALK_SECRET=

KEYWORDS=锂电,新能源,碳酸锂
POLL_INTERVAL_SEC=300
CLS_RN=20
STATE_DB_PATH=data/state.db
EOF
chmod 600 .env
echo "Webhook: ${WEBHOOK1:0:60}..."

echo "========== 3/6 安装依赖 =========="
python3 -m venv .venv
source .venv/bin/activate
pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

echo "========== 4/6 测试拉取财联社 =========="
python main.py --once --dry-run

echo "========== 5/6 测试钉钉推送（第一个群） =========="
python main.py --test-notify

echo "========== 6/6 安装/重启常驻服务 =========="
cp deploy/monitorkeyword.service /etc/systemd/system/monitorkeyword.service
systemctl daemon-reload
systemctl enable monitorkeyword
systemctl restart monitorkeyword
sleep 2
systemctl status monitorkeyword --no-pager

echo ""
echo "=========================================="
echo "完成！请到第一个钉钉群确认是否收到测试消息。"
echo "查看日志: journalctl -u monitorkeyword -f"
echo "=========================================="
