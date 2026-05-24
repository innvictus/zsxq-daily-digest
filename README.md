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

### 3. 各平台部署

#### Windows 本地部署

**步骤 1：安装 Python**

下载安装 Python 3.11+：https://www.python.org/downloads/

安装时 **务必勾选** `Add Python to PATH`，然后一路下一步。

验证安装：

```powershell
python --version
# 应输出 Python 3.11.x 或更高
```

**步骤 2：安装 Git**

下载安装 Git：https://git-scm.com/downloads/win

一路默认选项即可。

**步骤 3：拉取代码**

```powershell
# 打开 PowerShell，进入你想要放项目的目录
cd D:\
git clone https://github.com/innvictus/zsxq-daily-digest.git
cd zsxq-daily-digest
```

**步骤 4：配置文件**

```powershell
# 复制配置模板
copy config\config.example.yaml config\config.yaml
```

然后用记事本编辑 `config\config.yaml`，填入 Token 和 API Key。再创建 `config\groups.yaml`：

```yaml
groups:
  - group_id: "你的星球ID"
    name: "星球名称"
    enabled: true
```

**步骤 5：安装依赖**

```powershell
pip install -r requirements.txt
```

**步骤 6：测试运行**

```powershell
python main.py run
```

如果正常生成了 `output\日期.html`，说明配置没问题。

**步骤 7：设置每天自动执行**

打开 **任务计划程序（Task Scheduler）** → 创建基本任务：

| 设置 | 值 |
|------|-----|
| 名称 | ZSXQ Daily Digest |
| 触发器 | 每天，凌晨 1:00 |
| 操作 | 启动程序 |
| 程序/脚本 | `python` |
| 参数 | `main.py run` |
| 起始于 | `D:\zsxq-daily-digest`（你克隆的路径） |

勾选"不管用户是否登录都要运行"，这样锁屏也会执行。

也可以用一条命令创建（**PowerShell 管理员模式**，注意替换路径）：

```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "main.py run" -WorkingDirectory "D:\zsxq-daily-digest"
$trigger = New-ScheduledTaskTrigger -Daily -At "01:00"
Register-ScheduledTask -TaskName "ZSXQ Daily Digest" -Action $action -Trigger $trigger -Description "知识星球日报"
```

> 也可以用 **run.bat** 双击一键运行（测试用，不能定时）。

#### macOS 本地部署

```bash
# 安装 Python 3.11+
brew install python@3.11

# 拉代码
git clone https://github.com/innvictus/zsxq-daily-digest.git
cd zsxq-daily-digest

# 配置
cp config/config.example.yaml config/config.yaml
# 编辑 config.yaml 和 config/groups.yaml

# 安装依赖
pip3 install -r requirements.txt

# 测试
python3 main.py run

# 设置每天 1:00 自动执行
cp com.zsxq.daily.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.zsxq.daily.plist
```

#### Linux 本地部署

```bash
git clone https://github.com/innvictus/zsxq-daily-digest.git
cd zsxq-daily-digest
cp config/config.example.yaml config/config.yaml
# 编辑配置文件
pip install -r requirements.txt
python main.py run

# 定时任务
crontab -e
# 添加: 0 1 * * * cd /path/to/zsxq-daily-digest && python main.py run
```

### 4. 命令行参考

```bash
python main.py run              # 一键抓取 + 生成日报
python main.py fetch            # 只抓取
python main.py report --date 2026-05-23  # 只生成日报
python main.py search "关键词"   # 搜索帖子
```

## Docker 部署（极空间 / NAS / Windows）

### 前置条件

- **极空间/NAS**：Docker 已内置
- **Windows**：先安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)，安装后重启电脑
- **macOS**：Docker Desktop 或 OrbStack

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
4. Docker 基础镜像 `python:3.11-slim` 在国内可能拉取慢，需配置镜像加速器：
   - 极空间：Docker 设置 → 镜像源 → 添加阿里云/中科大镜像
   - Windows Docker Desktop：Settings → Docker Engine → 添加 `registry-mirrors`
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
