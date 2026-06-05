#!/usr/bin/env bash
# 一键推送代码到 GitHub 并配置 Actions Secrets（需已安装 gh 并完成 gh auth login）
set -euo pipefail

REPO_URL="${1:-https://github.com/Mesutozil/yang.git}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

if [[ ! -f .env ]]; then
  echo "错误：未找到 .env，请先复制 .env.example 并配置钉钉 Webhook"
  exit 1
fi

# shellcheck disable=SC1091
source .env

if [[ -z "${DINGTALK_WEBHOOK_URL:-}" ]]; then
  echo "错误：.env 中缺少 DINGTALK_WEBHOOK_URL"
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "未检测到 GitHub CLI (gh)。请先安装并登录："
  echo "  brew install gh"
  echo "  gh auth login"
  echo ""
  echo "或手动操作："
  echo "  1. git push -u origin main"
  echo "  2. 在 GitHub 仓库 Settings → Secrets 添加 DINGTALK_WEBHOOK_URL"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "请先运行: gh auth login"
  exit 1
fi

if [[ ! -d .git ]]; then
  git init -b main
fi

git add .gitignore .env.example README.md requirements.txt config.py main.py src/ .github/ scripts/
git diff --cached --quiet || git commit -m "Add CLS keyword monitor with GitHub Actions"

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REPO_URL"
else
  git remote add origin "$REPO_URL"
fi

echo ">>> 推送代码到 $REPO_URL"
git push -u origin main

REPO_SLUG="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "Mesutozil/yang")"

echo ">>> 配置 GitHub Secrets"
printf '%s' "$DINGTALK_WEBHOOK_URL" | gh secret set DINGTALK_WEBHOOK_URL --repo "$REPO_SLUG"
if [[ -n "${DINGTALK_SECRET:-}" ]]; then
  printf '%s' "$DINGTALK_SECRET" | gh secret set DINGTALK_SECRET --repo "$REPO_SLUG"
fi

echo ">>> 手动触发一次监测"
gh workflow run monitor.yml --repo "$REPO_SLUG"

echo ""
echo "完成！请到 GitHub Actions 查看运行状态："
echo "https://github.com/${REPO_SLUG}/actions"
