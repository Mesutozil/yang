# 财联社关键词监测

轮询 [财联社电报](https://www.cls.cn/telegraph)，匹配指定关键词（默认：电池、新能源），命中后推送通知。

支持两种**免费**通知渠道：

| 渠道 | 推送到 | 费用 | 推荐度 |
|------|--------|------|--------|
| **钉钉群机器人** | 钉钉群 | 免费 | ⭐ 首选，配置最简单 |
| **WxPusher** | 个人微信 | 免费 | 需注册并关注主题 |

## 快速开始

### 1. 安装依赖

```bash
cd /Users/ozil/monitorkeyword
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 选择通知渠道并配置

```bash
cp .env.example .env
```

#### 方案 A：钉钉（推荐，完全免费）

1. 打开钉钉，创建一个群（可以只有你自己）
2. 进入群聊 → 右上角 **「…」** → **「智能群助手」**
3. 点击 **「添加机器人」** → 选择 **「自定义」**
4. 设置机器人名称，安全设置选 **「自定义关键词」**（填 `财联社`）或 **「加签」**
5. 复制 **Webhook 地址**，填入 `.env`：

```env
NOTIFY_CHANNEL=dingtalk
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxxxx
# 若选了「加签」安全设置，还需填 SECRET：
DINGTALK_SECRET=SECxxxxx
```

6. 在钉钉群里应能看到机器人加入成功

#### 方案 B：个人微信（WxPusher，免费）

1. 打开 [https://wxpusher.zjiecode.com](https://wxpusher.zjiecode.com) 注册
2. **创建应用** → 复制 `appToken`（形如 `AT_xxx`）
3. **创建主题** → 复制 `topicId`（数字）
4. 用微信扫描主题二维码完成关注
5. 填入 `.env`：

```env
NOTIFY_CHANNEL=wxpusher
WXPUSHER_APP_TOKEN=AT_xxxxxxxx
WXPUSHER_TOPIC_IDS=12345
```

#### 方案 C：钉钉 + 微信同时推送

```env
NOTIFY_CHANNEL=dingtalk,wxpusher
DINGTALK_WEBHOOK_URL=...
WXPUSHER_APP_TOKEN=...
WXPUSHER_TOPIC_IDS=...
```

### 3. 配置项说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `NOTIFY_CHANNEL` | `dingtalk` / `wxpusher` / `dingtalk,wxpusher` | `dingtalk` |
| `DINGTALK_WEBHOOK_URL` | 钉钉机器人 Webhook | 钉钉渠道必填 |
| `DINGTALK_SECRET` | 钉钉加签密钥（可选） | 空 |
| `WXPUSHER_APP_TOKEN` | WxPusher 应用 Token | 微信渠道必填 |
| `WXPUSHER_TOPIC_IDS` | WxPusher 主题 ID，逗号分隔 | 与 UID 二选一 |
| `WXPUSHER_UIDS` | WxPusher 用户 UID，逗号分隔 | 与主题 ID 二选一 |
| `KEYWORDS` | 监测关键词 | `电池,新能源` |
| `POLL_INTERVAL_SEC` | 轮询间隔（秒） | `60` |
| `CLS_RN` | 每次拉取条数 | `50` |

### 4. 运行

```bash
# 验证拉取数据
python main.py --once --dry-run

# 推送一条真实含关键词的文章（验证钉钉/微信）
python main.py --test-notify

# 正式监测单次轮询
python main.py --once

# 持续监测
python main.py
```

**冷启动说明**：首次运行会将当前批次电报写入本地数据库但不推送，避免历史消息刷屏。

## 项目结构

```
monitorkeyword/
├── main.py
├── config.py
├── requirements.txt
├── .env.example
└── src/
    ├── cls_fetcher.py
    ├── matcher.py
    ├── notifier.py    # 钉钉 + WxPusher
    └── state.py
```

## 24 小时监测（电脑不必常开）

| 方案 | 费用 | 监测频率 | 难度 | 推荐 |
|------|------|----------|------|------|
| **GitHub Actions** | 免费 | 每 5 分钟 | ⭐ 简单 | ✅ 首选 |
| **云服务器 VPS** | ~30 元/月起 | 可设 60 秒 | 中等 | 要更高实时性 |
| **本机 Mac** | 免费 | 可设 60 秒 | 简单 | 需电脑常开 |

### 方案 A：GitHub Actions（推荐，电脑关机也能跑）

项目已自带工作流：[`.github/workflows/monitor.yml`](.github/workflows/monitor.yml)

**步骤：**

1. 把代码推到 GitHub（建议建**私有仓库**，避免泄露配置）
   ```bash
   cd /Users/ozil/monitorkeyword
   git init
   git add .
   git commit -m "财联社关键词监测"
   # 在 GitHub 新建仓库后：
   git remote add origin https://github.com/你的用户名/monitorkeyword.git
   git push -u origin main
   ```

2. 在 GitHub 仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**，添加：

   | Secret 名称 | 值 |
   |-------------|-----|
   | `DINGTALK_WEBHOOK_URL` | 你的钉钉 Webhook 完整地址 |
   | `DINGTALK_SECRET` | 若机器人用了加签则填，否则可留空或不建 |

3. 打开 **Actions** 标签页，找到 **CLS Keyword Monitor**，点 **Run workflow** 手动跑一次

4. 之后每 **5 分钟**自动执行，有新匹配文章就推送到钉钉

> GitHub Actions 最短只能 5 分钟一次，比本机 60 秒略慢，但个人监测完全够用。工作流会用缓存保存 `data/state.db`，避免重复推送。

### 方案 B：阿里云轻量服务器（推荐，实时性最好）

已提供一键部署，详见 **[deploy/DEPLOY.md](deploy/DEPLOY.md)**（用户 `root`，目录 `/home/root/yangq`）。

```bash
ssh root@你的公网IP
git clone https://github.com/Mesutozil/yang.git /home/root/yangq
cd /home/root/yangq
bash deploy/install.sh
nano .env
systemctl start monitorkeyword
```

可保持 `POLL_INTERVAL_SEC=60`。上线后请关闭 GitHub Actions 定时任务，避免重复推送。

### 方案 C：本机 Mac（需电脑常开）

创建 `~/Library/LaunchAgents/com.monitorkeyword.cls.plist` 用 launchd 保活，仅适合电脑长期开机时使用。

## 验证清单

1. `python main.py --once --dry-run` — 确认能拉到电报
2. 临时设 `KEYWORDS=财联社`，运行 `python main.py --once` — 确认钉钉/微信能收到
3. 改回 `KEYWORDS=电池,新能源`，启动持续监测
4. 重启进程，确认不重复推送

## 注意事项

- 财联社接口为非官方 API，程序内置 sign 签名与移动端 fallback
- 钉钉机器人限频：20 条/分钟
- WxPusher 免费，但需关注主题才能收到微信消息
- `.env` 含密钥，请勿提交到 git
