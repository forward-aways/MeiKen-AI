# 部署指南

本文档面向 Linux 服务器部署。本地开发只需参考 [README 快速开始](../README.md#快速开始)。

## 架构概览

```
浏览器
  │  :8080 / :80 / :443
  ▼
Nginx（反向代理，关闭缓冲以支持 SSE）
  │  127.0.0.1:8000
  ▼
FastAPI（backend/main.py）
  ├── /api/*           业务接口
  ├── /assets/*        前端构建产物（frontend/dist/assets）
  └── 其他路径          SPA 回退到 index.html（不缓存）
  │
  ├── chat.db          业务数据（SQLite WAL）
  ├── checkpoints.db   对话检查点
  ├── skills_store.db  技能与文件存储
  ├── chroma_db/       向量库
  ├── workspace/       用户文件工作区
  ├── config/fernet.key  API Key 加解密密钥
  └── logs/            日志（每日轮转）
```

后端在 `frontend/dist` 存在时自动托管前端，因此生产环境只需运行后端进程。

## 前置条件

- Linux 服务器（x86_64），可访问公网
- 已安装 [uv](https://docs.astral.sh/uv/getting-started/installation/) 与 Node.js >= 18
- 项目目录的启动用户需具备写权限（运行时会自动创建 `workspace/`、`logs/`、`chroma_db/` 及若干 `.db` 文件）
- 首次使用知识库需要下载 Chroma 嵌入模型（约 79MB），详见[常见问题](#常见问题)

## 安装

```bash
git clone https://github.com/forward-aways/MeiKen-AI.git
cd MeiKen-AI

# 后端依赖（uv 自动下载 Python 3.13 并创建虚拟环境）
uv python install 3.13
uv sync

# 前端构建
cd frontend && npm install && npm run build && cd ..
```

## 配置环境变量

```bash
cp .env.example .env
vi .env
```

生产环境至少需要修改：

| 变量 | 说明 |
|---|---|
| `JWT_SECRET` | 会话签名密钥，务必改为随机长字符串 |
| `ADMIN_PASSWORD` | 初始管理员密码 |
| `FRONTEND_URL` | 站点访问地址，用于密码重置链接 |

通常留空、由使用者在界面中配置的变量：

| 变量 | 说明 |
|---|---|
| `DEEPSEEK_API_KEY` | 仅首次启动时写入内置供应商；公共服务建议留空 |
| `BOCHA_API_KEY` | 联网搜索（博查）密钥 |

其余可选变量见 `.env.example` 注释。

> `.env` 已被 `.gitignore` 忽略，不会进入版本库。

## 首次启动检查清单

1. 启动后端

   ```bash
   uv run python main.py backend
   ```

2. 确认启动日志中出现：

   - `种子数据就绪（管理员 / 智能体 / 技能 / 内置供应商）`
   - `用户工作区就绪`
   - `检查点与技能存储就绪`

3. 确认自动生成的敏感文件：

   | 文件 | 说明 |
   |---|---|
   | `config/fernet.key` | API Key 加密密钥，权限 `0600`。**迁移或备份时必须一起保留，否则已存 Key 无法解密** |
   | `chat.db` | 业务数据库 |

4. 访问 `http://127.0.0.1:8000/docs` 验证接口可用。

5. 登录管理员账户（`admin@meiken.ai`），在「管理模型」中填入 API Key 并发起一次对话验证。

## systemd 服务（开机自启 + 崩溃重启）

按实际路径与用户修改 `WorkingDirectory`、`User`、`ExecStart`：

```bash
sudo tee /etc/systemd/system/meikenai.service > /dev/null << 'EOF'
[Unit]
Description=MeiKen AI Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ai-project/MeiKen-AI
ExecStart=/home/ubuntu/.local/bin/uv run python main.py backend
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable meikenai
sudo systemctl start meikenai
```

常用管理命令：

| 操作 | 命令 |
|---|---|
| 查看状态 | `sudo systemctl status meikenai` |
| 查看日志 | `sudo journalctl -u meikenai -f` |
| 重启 | `sudo systemctl restart meikenai` |
| 停止 | `sudo systemctl stop meikenai` |

> `ExecStart` 中的 `uv` 建议写绝对路径（`which uv` 查看），systemd 不会加载用户的 PATH。

## Nginx 反向代理

项目自带示例配置 `nginx/meikenai.conf`（监听 8080，代理到 `127.0.0.1:8000`）：

```bash
sudo cp nginx/meikenai.conf /etc/nginx/sites-available/meikenai.conf
sudo ln -sf /etc/nginx/sites-available/meikenai.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

配置要点（示例配置已包含）：

- `proxy_buffering off` 与 `proxy_cache off`：SSE 流式输出必须关闭缓冲，否则前端无法逐字显示
- `proxy_read_timeout 300s`：长任务运行时间较长，需放宽读超时
- `client_max_body_size 15M`：与文件上传大小匹配
- 修改 `server_name` 为你的域名

> 域名未备案时，国内云厂商会拦截 80 / 443 / 8080 等常见 Web 端口，可先用 `http://<服务器IP>:8080` 直连，或改用其他端口。

## 更新部署

```bash
# 后端
git pull && uv sync
sudo systemctl restart meikenai

# 前端（Nginx 无需重启）
cd frontend && npm install && npm run build
```

前端更新后，浏览器请强制刷新（Ctrl+Shift+R）。`index.html` 已设置为不缓存，但旧标签页仍需刷新。

## 安全建议

如果要把项目部署为公共服务：

1. 使用**全新数据库**，不要拷贝本地 `chat.db`（其中可能含个人对话与加密 Key）
2. `.env` 中**不要写** `DEEPSEEK_API_KEY`，让每位使用者在界面中配置自己的 Key
3. **不要拷贝** `config/fernet.key`，全新启动会自动生成；反之，若要还原数据库，则必须一并还原该文件
4. 修改默认 `ADMIN_PASSWORD`，并让其他使用者自行注册，不要共用管理员账户
5. 备份时同时备份 `chat.db`、`config/fernet.key`、`workspace/`（用户文件），三者缺一不可

## 常见问题

### 首次上传知识库（或运行测试）长时间卡住

Chroma 首次使用需要下载 `all-MiniLM-L6-v2` 嵌入模型（约 79MB），缓存于 `~/.cache/chroma/onnx_models/`。

- 若服务器网络受限，下载可能极慢或中断，表现是一直卡住
- 处理方式：提前在服务器上完成一次知识库上传以预热模型；或从可联网的机器复制整个 `all-MiniLM-L6-v2` 目录到服务器的同一路径
- 缓存不完整时（存在 `.tar.gz` 但体积远小于 79MB）Chroma 会重新下载，可删除该目录后重试

### 前端页面 404 或打开是旧版本

- 确认 `frontend/dist` 存在且已执行 `npm run build`
- 后端启动后再构建前端不会自动生效，需重启后端进程
- 浏览器强制刷新（Ctrl+Shift+R）

### 进程启动即退出

查看 `sudo journalctl -u meikenai -n 100`：

- `Permission denied`：检查 `WorkingDirectory` 的写权限
- `uv: command not found`：把 `ExecStart` 中的 `uv` 改为绝对路径
- 端口占用：`ss -lntp | grep 8000`

### 迁移服务器后 API Key 失效

`config/fernet.key` 未随 `chat.db` 一起迁移会导致已存 Key 无法解密，可在界面中重新填写。

### 对话中途断开 / 输出不流畅

多为 Nginx 缓冲未关闭，确认 `proxy_buffering off;` 生效并重载 Nginx。
