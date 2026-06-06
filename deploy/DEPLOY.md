# 阿里云轻量服务器部署指南

适用于：**Ubuntu 24.04**，用户 **admin**，目录 **/home/admin/yangq**

## 一、SSH 登录服务器

在你本机 Mac 终端执行（把 `你的公网IP` 换成阿里云控制台里的 IP）：

```bash
ssh admin@你的公网IP
```

首次登录按提示输入密码。

## 二、一键部署

```bash
# 先单独克隆（install.sh 也可自动克隆）
git clone https://github.com/Mesutozil/yang.git /home/admin/yangq
cd /home/admin/yangq
bash deploy/install.sh
```

## 三、配置 .env

```bash
nano /home/admin/yangq/.env
```

参考内容（把 Webhook 换成你的真实地址）：

```env
NOTIFY_CHANNEL=dingtalk

DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=第一个token,https://oapi.dingtalk.com/robot/send?access_token=第二个token
DINGTALK_SECRET=

KEYWORDS=锂电,新能源,碳酸锂
POLL_INTERVAL_SEC=60
CLS_RN=50
STATE_DB_PATH=data/state.db
```

保存：`Ctrl+O` 回车，`Ctrl+X` 退出。

## 四、测试

```bash
cd /home/admin/yangq
source .venv/bin/activate

# 测试能否拉取财联社数据
python main.py --once --dry-run

# 测试钉钉推送（需近期有匹配文章，或见下方说明）
python main.py --test-notify
```

## 五、启动常驻监测

```bash
sudo systemctl start monitorkeyword
sudo systemctl status monitorkeyword
```

实时看日志：

```bash
journalctl -u monitorkeyword -f
```

按 `Ctrl+C` 退出日志查看（服务继续运行）。

## 六、常用命令

| 操作 | 命令 |
|------|------|
| 启动 | `sudo systemctl start monitorkeyword` |
| 停止 | `sudo systemctl stop monitorkeyword` |
| 重启 | `sudo systemctl restart monitorkeyword` |
| 状态 | `sudo systemctl status monitorkeyword` |
| 日志 | `journalctl -u monitorkeyword -f` |
| 更新代码 | `cd /home/admin/yangq && git pull && sudo systemctl restart monitorkeyword` |

## 七、关闭 GitHub Actions（避免重复推送）

VPS 上线后，建议在 GitHub 仓库：

1. 打开 https://github.com/Mesutozil/yang/actions
2. 左侧 **CLS Keyword Monitor** → 右上角 **⋯** → **Disable workflow**

或在仓库 Settings → Actions → 关闭 scheduled workflows。

## 八、防火墙说明

本程序只主动访问外网，**无需在阿里云安全组开放入站端口**。
