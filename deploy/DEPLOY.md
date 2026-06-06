# 阿里云轻量服务器部署指南

适用于：**Ubuntu 24.04**，用户 **root**，目录 **/home/root/yangq**

## 一、SSH 登录服务器

在你本机 Mac 终端执行：

```bash
ssh root@47.101.198.188
```

## 二、一键部署

```bash
git clone https://github.com/Mesutozil/yang.git /home/root/yangq
cd /home/root/yangq
bash deploy/install.sh
```

## 三、配置 .env

```bash
nano /home/root/yangq/.env
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
cd /home/root/yangq
source .venv/bin/activate

python main.py --once --dry-run
python main.py --test-notify
```

## 五、启动常驻监测

```bash
systemctl start monitorkeyword
systemctl status monitorkeyword
```

实时看日志：

```bash
journalctl -u monitorkeyword -f
```

## 六、常用命令

| 操作 | 命令 |
|------|------|
| 启动 | `systemctl start monitorkeyword` |
| 停止 | `systemctl stop monitorkeyword` |
| 重启 | `systemctl restart monitorkeyword` |
| 状态 | `systemctl status monitorkeyword` |
| 日志 | `journalctl -u monitorkeyword -f` |
| 更新代码 | `cd /home/root/yangq && git pull && systemctl restart monitorkeyword` |

## 七、关闭 GitHub Actions（避免重复推送）

1. 打开 https://github.com/Mesutozil/yang/actions
2. **CLS Keyword Monitor** → **⋯** → **Disable workflow**

## 八、防火墙说明

本程序只主动访问外网，**无需开放入站端口**。
