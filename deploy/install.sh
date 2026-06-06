#!/usr/bin/env bash
# 在阿里云 Ubuntu 24.04 上一键部署财联社关键词监测
# 用法: bash deploy/install.sh
set -euo pipefail

APP_DIR="/home/root/yangq"
SERVICE_NAME="monitorkeyword"
REPO_URL="https://github.com/Mesutozil/yang.git"

echo ">>> 安装系统依赖"
apt update
apt install -y python3 python3-venv python3-pip git

mkdir -p /home/root

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo ">>> 克隆代码到 $APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
else
  echo ">>> 更新代码"
  cd "$APP_DIR"
  git pull origin main
fi

cd "$APP_DIR"

if [[ ! -f .env ]]; then
  echo ">>> 创建 .env（请随后编辑填入钉钉 Webhook）"
  cp .env.example .env
  echo ""
  echo "重要：请编辑 $APP_DIR/.env"
  echo "  - DINGTALK_WEBHOOK_URL=你的两个Webhook，逗号分隔"
  echo "  - KEYWORDS=锂电,新能源,碳酸锂"
  echo ""
fi

echo ">>> 安装 Python 依赖"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo ">>> 测试拉取数据"
python main.py --once --dry-run

echo ">>> 安装 systemd 服务"
cp deploy/monitorkeyword.service /etc/systemd/system/${SERVICE_NAME}.service
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

echo ""
echo "=========================================="
echo "部署准备完成！"
echo ""
echo "1. 编辑配置:"
echo "   nano $APP_DIR/.env"
echo ""
echo "2. 测试钉钉推送:"
echo "   cd $APP_DIR && source .venv/bin/activate"
echo "   python main.py --test-notify"
echo ""
echo "3. 启动常驻监测:"
echo "   systemctl start ${SERVICE_NAME}"
echo ""
echo "4. 查看状态和日志:"
echo "   systemctl status ${SERVICE_NAME}"
echo "   journalctl -u ${SERVICE_NAME} -f"
echo "=========================================="
