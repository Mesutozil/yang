#!/usr/bin/env bash
# 阿里云服务器完整一键部署（root + /home/root/yangq）
set -euo pipefail

APP_DIR="/home/root/yangq"
SERVICE_NAME="monitorkeyword"
REPO_URL="https://github.com/Mesutozil/yang.git"

echo "========== 1/7 安装系统依赖 =========="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git curl

mkdir -p /home/root

echo "========== 2/7 拉取代码 =========="
if [[ -d "$APP_DIR/.git" ]]; then
  cd "$APP_DIR"
  git pull origin main
else
  git clone "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

echo "========== 3/7 写入 .env =========="
if [[ -z "${DINGTALK_WEBHOOK_URL:-}" ]]; then
  echo "错误: 请先设置 DINGTALK_WEBHOOK_URL 环境变量"
  exit 1
fi

cat > "$APP_DIR/.env" << EOF
NOTIFY_CHANNEL=dingtalk

DINGTALK_WEBHOOK_URL=${DINGTALK_WEBHOOK_URL}
DINGTALK_SECRET=${DINGTALK_SECRET:-}

KEYWORDS=${KEYWORDS:-锂电,新能源,碳酸锂}
POLL_INTERVAL_SEC=${POLL_INTERVAL_SEC:-60}
CLS_RN=${CLS_RN:-50}
STATE_DB_PATH=data/state.db
EOF
chmod 600 "$APP_DIR/.env"
echo ".env 已写入 $APP_DIR/.env"

echo "========== 4/7 安装 Python 依赖 =========="
python3 -m venv "$APP_DIR/.venv"
# shellcheck disable=SC1091
source "$APP_DIR/.venv/bin/activate"
pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

echo "========== 5/7 测试拉取财联社 =========="
python main.py --once --dry-run

echo "========== 6/7 安装并启动 systemd =========="
cp deploy/monitorkeyword.service /etc/systemd/system/${SERVICE_NAME}.service
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "========== 7/7 检查服务状态 =========="
sleep 2
systemctl status "${SERVICE_NAME}" --no-pager || true

echo ""
echo "=========================================="
echo "部署完成！监测服务已启动（每 60 秒轮询）"
echo ""
echo "查看实时日志: journalctl -u ${SERVICE_NAME} -f"
echo "重启服务:     systemctl restart ${SERVICE_NAME}"
echo "=========================================="
