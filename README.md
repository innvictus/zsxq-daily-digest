# ZSXQ Daily Digest - 知识星球AI日报生成器

每天自动抓取知识星球内容，AI 分析后生成结构化日报，输出 HTML + PDF，支持邮件推送。

## 功能

- 增量抓取知识星球指定星球的全部帖子（游标分页 + 反爬重试）
- AI 分析生成 7 板块日报：
  1. 今日要点
  2. 风格总结与板块热度（含首推标的排名）
  3. 估值指引
  4. 精选文章（含原文链接）
  5. 脱水文件与附件
  6. 值得关注的观点
  7. 综合推荐买入（3 个确定性最高的标的）
- 输出 HTML + PDF，自动适配暗色模式
- 支持 Claude / OpenAI / DeepSeek 多 AI 切换
- 邮件推送日报到手机
- Docker 部署到 NAS / 服务器，定时执行

## 快速开始

### 1. 获取 Token

**知识星球 access_token:**
浏览器登录 wx.zsxq.com → F12 → Network → 复制 Cookie 中的 `zsxq_access_token`

**AI API Key（推荐 DeepSeek，便宜）:**
https://platform.deepseek.com/api_keys → 注册送 500 万 tokens

### 2. 配置文件

```bash
cp config/config.example.yaml config/config.yaml
```

编辑 `config/config.yaml`：

```yaml
zsxq:
  access_token: "你的ZSXQ_TOKEN"

ai:
  provider: "deepseek"
  deepseek:
    api_key: "sk-你的key"
```

编辑 `config/groups.yaml`：

```yaml
groups:
  - group_id: "你的星球ID"
    name: "星球名称"
    enabled: true
```

### 3. 本地运行

```bash
pip install -r requirements.txt

# 一键抓取 + 生成日报
python main.py run

# 只抓取
python main.py fetch

# 只生成日报（用已有数据，不重新爬）
python main.py report --date 2026-05-23

# 搜索帖子
python main.py search "关键词"
```

### 4. macOS 定时任务

```bash
cp com.zsxq.daily.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.zsxq.daily.plist
# 每天凌晨 1:00 自动执行
```

## Docker 部署（极空间 / NAS）

### 拉取代码

```bash
# 直连 GitHub
git clone https://github.com/innvictus/zsxq-daily-digest.git

# 国内加速（GitHub 慢或连不上时用）
git clone https://ghproxy.com/https://github.com/innvictus/zsxq-daily-digest.git
```

### 配置

```bash
cd zsxq-daily-digest

# 创建配置文件（含真实 Token，不会上传到 GitHub）
cp config/config.example.yaml config/config.yaml
# 编辑 config.yaml，填入 zsxq_access_token 和 AI api_key
# 编辑 config/groups.yaml，填入星球ID
```

### 构建启动

```bash
docker compose up -d --build
```

容器会每天凌晨 1:00 自动执行。修改执行时间：

```yaml
# docker-compose.yml
environment:
  - RUN_HOUR=6       # 改成早上 6 点
  - RUN_ON_START=true # 启动时立即执行一次，用于测试
```

### 查看状态

```bash
# 查看日志
docker compose logs -f

# 手动执行一次
docker compose exec zsxq-daily python3 main.py run
```

输出文件在 `output/` 目录：

```
output/
├── 2026-05-23.html
├── 2026-05-23.pdf
├── 2026-05-24.html
└── 2026-05-24.pdf
```

## 邮件推送

编辑 `config/config.yaml`：

```yaml
notify:
  enabled: true
  smtp_host: "smtp.qq.com"       # QQ邮箱
  smtp_port: 465
  sender_email: "你的QQ@qq.com"
  sender_password: "QQ邮箱授权码"  # 不是QQ密码！去QQ邮箱设置里生成
  recipient_email: "接收推送的邮箱"
```

| 邮箱 | smtp_host | port |
|------|-----------|------|
| QQ | smtp.qq.com | 465 |
| 163 | smtp.163.com | 465 |
| Gmail | smtp.gmail.com | 465 |

## 自定义 AI 规则

编辑 `config/rules.yaml` 调整日报风格、板块结构、关注领域。改完后下次生成自动生效，不需要重新部署。

## 注意事项

1. **不要上传 config.yaml 和 groups.yaml**（含 Token），已在 `.gitignore` 中排除
2. 知识星球 API 有频率限制，抓取间隔默认 2-3 秒，不要调太激进
3. 第一次部署建议 `RUN_ON_START=true` 测试是否正常
4. Docker 基础镜像 `python:3.11-slim` 在国内可能拉取慢，在极空间 Docker 设置里配置镜像加速器
5. 生成的日报仅供参考，不构成投资建议
6. MP3 录音文件默认忽略，不在日报中展示

## 项目结构

```
zsxq-daily-digest/
├── config/
│   ├── config.example.yaml   # 配置模板
│   ├── rules.yaml            # AI 日报规则
│   └── groups.yaml           # 星球列表（自建）
├── src/
│   ├── crawler/              # ZSXQ API 客户端 + 抓取器
│   ├── storage/              # SQLite 数据库
│   ├── ai/                   # AI Provider（Claude/OpenAI/DeepSeek）
│   ├── report/               # 日报生成器 + HTML 模板
│   └── notify/               # 邮件推送
├── output/                   # 生成的日报（挂载到NAS）
├── data/                     # 数据库文件
├── Dockerfile                # ARM64 兼容
├── docker-compose.yml        # 一键部署
├── scheduler.py              # 定时任务
└── main.py                   # 命令行入口
```
