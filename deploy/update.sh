#!/usr/bin/env bash
# 从 GitHub 拉取最新代码并重启监测服务
# 用法: bash deploy/update.sh
set -euo pipefail

APP_DIR="/home/root/yangq"
SERVICE_NAME="monitorkeyword"

cd "$APP_DIR"

echo ">>> 拉取最新代码"
git pull origin main

if [[ -f requirements.txt ]]; then
  echo ">>> 更新 Python 依赖"
  source .venv/bin/activate
  pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
fi

echo ">>> 重启服务"
systemctl restart "${SERVICE_NAME}"
sleep 2
systemctl status "${SERVICE_NAME}" --no-pager

echo ""
echo "更新完成。查看日志: journalctl -u ${SERVICE_NAME} -f"
