<div align="center">

# MeiKen AI Harness

基于 FastAPI + Vue 3 + deepagents 的多代理 AI 工作站：内置专家代理、子代理委派、工具调用与人工审批，支持多模型供应商、联网搜索、私有知识库、技能系统与多模态输入。

<img src="https://img.shields.io/badge/Python-3.13-5b57d2?logo=python" alt="Python">
<img src="https://img.shields.io/badge/Vue-3.x-5b57d2?logo=vuedotjs" alt="Vue">
<img src="https://img.shields.io/badge/FastAPI-0.139-5b57d2?logo=fastapi" alt="FastAPI">
<img src="https://img.shields.io/badge/license-MIT-5b57d2" alt="License">

</div>

---

## 目录

- [核心亮点](#核心亮点)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [API 概览](#api-概览)
- [数据库](#数据库)
- [部署](#部署)
- [License](#license)

## 核心亮点

<table>
<tr>
<td width="50%" valign="top">

### 多代理系统（deepagents）

- 内置 5 个代理：通用助手 / 研究员 / 代码专家 / 数据分析师 / 写作助手
- 子代理委派（研究员、数据分析师）自动分工
- 工具调用可视化（调用卡片 + 结果折叠）
- 计划清单（write_todos）实时更新
- 人工审批（HITL）：敏感工具调用可批准 / 拒绝 / 修改参数
- 三种人格模式：通用 / 编程 / 办公

</td>
<td width="50%" valign="top">

### 模型供应商管理

- 多供应商：内置 DeepSeek + 任意 OpenAI 兼容接口
- API Key 使用 Fernet 对称加密存储，按用户隔离
- 一键连接测试、启用 / 停用、模型级上下文窗口配置
- 模型胶囊二级菜单直接切换模型
- 服务器部署可留空 Key，使用者自行配置

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 多模态输入

- 图片粘贴 / 拖拽 / 预览，单条消息最多 4 张
- 多模态模型直读图片（DeepSeek V4.1 Flash 原生支持）
- 消息图片渲染 + 点击灯箱查看
- 非多模态模型自动降级为纯文本

</td>
<td width="50%" valign="top">

### 深度思考与推理强度

- 思考模式三档：快速 / 标准 / 深度
- 推理强度独立调节，思考面板可折叠 + 耗时显示
- 兼容 DeepSeek reasoning_content 思维链
- 支持 思考 + 搜索 组合模式

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 联网搜索

- 博查 API 实时检索（新闻 / 天气 / 时事）
- 代理自动判断搜索时机（Function Calling）
- 搜索结果可折叠溯源（标题 + 摘要 + 链接）

</td>
<td width="50%" valign="top">

### 私有知识库（RAG）

- 上传 txt / md / pdf / docx 构建个人知识库
- 向量检索 + 来源引用
- 临时文件附加到单次对话

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 技能系统

- SKILL.md 格式，可创建 / 上传 / 编辑 / 启用停用
- 技能按用户存储在 LangGraph Store，随对话按需加载
- 内置技能校验与 `allowed-tools` 声明

</td>
<td width="50%" valign="top">

### 用户与对话管理

- 注册 / 登录（邮箱或昵称 + 密码）、JWT + httpOnly Cookie
- 头像系统、个人中心、忘记密码（SMTP 重置）
- 对话置顶 / 重命名 / 导出 Markdown / 全文搜索
- 消息删除、错误重试、编辑后重新生成

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 交互体验

- 液态玻璃 / 亚克力拟物质感（噪点 + 高光 + 多层投影）
- 悬浮玻璃顶栏：消息滚动到顶部渐隐消失
- 深浅主题切换 / 中英文双语
- SSE 流式输出，智能滚动（翻历史不跟滚，完成自动回底）

</td>
<td width="50%" valign="top">

### 可观测性

- 统一日志系统：控制台 + 文件每日轮转（默认保留 14 天）
- 请求级追踪（X-Request-Id + 用户上下文）
- 前端全局错误捕获上报

</td>
</tr>
</table>

## 技术栈

| 类别 | 选型 | 说明 |
|:---:|---|---|
| 后端 | FastAPI | 异步高性能 ASGI 框架 |
| 代理引擎 | deepagents + LangChain | 多代理编排、子代理、HITL |
| 模型 | DeepSeek V4.1 Flash（默认） | 原生多模态，OpenAI 兼容 |
| 多供应商 | OpenAI 兼容协议 | 任意第三方接口 + 自定义 Base URL |
| 密钥加密 | cryptography (Fernet) | API Key 对称加密存储 |
| 联网搜索 | 博查 Search API | 专为 AI 优化的搜索 |
| 知识库 | Chroma + 向量检索 | RAG 引用溯源 |
| 数据库 | SQLite | WAL 模式，零配置 |
| 认证 | bcrypt + JWT | httpOnly Cookie 传输 |
| 前端 | Vue 3 + Vite | SFC 组件化 |
| 高亮 | highlight.js | GitHub Dark 主题 |
| 包管理 | uv + npm | Python + Node.js |

## 快速开始

### 环境要求

| 依赖 | 版本 | 安装方式 |
|:---:|:---:|---|
| uv | latest | [官方安装指南](https://docs.astral.sh/uv/getting-started/installation/) |
| Node.js | >= 18 | [nodejs.org](https://nodejs.org/) |

> uv 会自动管理 Python 版本和虚拟环境，无需手动安装 Python。

### 安装与配置

```bash
# 克隆项目
git clone https://github.com/forward-aways/MeiKen-AI.git
cd MeiKen-AI

# 安装 Python（uv 自动下载所需版本）
uv python install 3.13

# 安装后端依赖（自动创建虚拟环境）
uv sync

# 安装前端依赖
cd frontend && npm install && cd ..
```

创建 `.env` 文件（所有项均可选，缺失时使用默认值）：

```ini
# 可选：首次启动时作为内置 DeepSeek 供应商的初始 Key
# 留空则登录后在「管理模型」界面中自行配置
DEEPSEEK_API_KEY="sk-your-key"
DEEPSEEK_BASE_URL="https://api.deepseek.com"

# 可选：联网搜索
BOCHA_API_KEY="sk-your-bocha-key"

# 生产环境务必修改
JWT_SECRET="change-me-in-production"
ADMIN_PASSWORD="admin123"

# 可选：密码重置邮件（留空则终端打印链接）
# SMTP_HOST=smtp.qq.com
# SMTP_PORT=587
# SMTP_USER=you@qq.com
# SMTP_PASSWORD=授权码

# 可选：日志与并发
# LOG_LEVEL=INFO            # DEBUG / INFO / WARNING / ERROR
# LOG_DIR=logs              # 日志目录（每日轮转，默认保留 14 天）
# LOG_DAYS=14
# MAX_CONCURRENT_RUNS=4
```

### 启动服务

```bash
# 终端 1：后端
uv run python main.py backend          # → http://127.0.0.1:8000

# 终端 2：前端
cd frontend && npm run dev             # → http://127.0.0.1:3000
```

> 启动后访问 `http://127.0.0.1:8000/docs` 可查看 Swagger API 文档。

### 默认管理员

首次启动且数据库无用户时会自动创建管理员账户：

- **邮箱**：`admin@meiken.ai`
- **密码**：由 `.env` 中的 `ADMIN_PASSWORD` 指定，默认为 `admin123`

> ⚠️ 生产环境请务必修改 `ADMIN_PASSWORD`，并让其他用户自行注册账号，不要共用管理员账户。

### 配置模型

登录后点击任意模型胶囊 → 「管理模型」：

1. 内置 DeepSeek 供应商已自动创建，点击卡片填入自己的 API Key 即可使用
2. 也支持添加任意 OpenAI 兼容供应商（自定义 Base URL、模型列表、上下文窗口）
3. API Key 加密存储于本地数据库，不会上传任何第三方

## 项目结构

```
MeiKen-AI/
├── main.py                         # 启动器
├── pyproject.toml                  # Python 依赖
│
├── backend/
│   ├── main.py                     # 应用装配（中间件 / 路由注册 / 生命周期）
│   ├── config.py                   # 集中配置（环境变量 / 路径 / 默认值）
│   ├── middleware.py               # 请求上下文中间件（请求 ID / 用户关联）
│   ├── runtime.py                  # 运行时单例（工厂 / 检查点 / 并发闸门）
│   ├── log.py                      # 日志系统（控制台高亮 + 文件每日轮转）
│   ├── auth.py                     # JWT 认证 + 密码重置
│   ├── crypto.py                   # API Key Fernet 加密
│   ├── schemas.py                  # Pydantic 模型
│   ├── skills.py                   # SKILL.md 校验 / 解析
│   ├── rag.py                      # 知识库向量检索
│   ├── db/                         # 数据访问层（按业务域拆分）
│   │   ├── _core.py                # 连接管理 / 建表 / 迁移
│   │   ├── users.py  convs.py  agents.py
│   │   ├── providers.py  skills.py  kb.py  images.py
│   ├── routes/                     # HTTP 路由
│   │   ├── auth.py  convs.py  chat.py  agents.py
│   │   ├── skills.py  kb.py  providers.py  images.py  misc.py
│   ├── services/
│   │   └── chat_stream.py          # SSE 编排（对话 / 审批共用）
│   └── agent/                      # 多代理引擎（deepagents）
│       ├── bridge.py               # 流式事件桥接（SSE 事件协议）
│       ├── factory.py              # 代理工厂 + 缓存 + 审批中断
│       ├── identity.py             # 人格 / 模式（general / code / work）
│       ├── llm.py                  # 供应商解析 + DeepSeek 双模式
│       ├── registry.py             # 内置代理与子代理定义
│       └── tools.py                # 工具（联网搜索 / 知识库）
│
├── tests/                          # 后端测试
│   └── test_smoke.py               # 核心接口冒烟测试（uv run --with pytest pytest tests/ -v）
│
├── frontend/
│   ├── package.json                # npm 依赖
│   ├── vite.config.js              # Vite 配置（含 /api 代理）
│   └── src/
│       ├── App.vue                 # 根组件 + SSE 流处理
│       ├── store.js                # 全局响应式状态
│       ├── api.js                  # 请求工具
│       ├── i18n.js                 # 中英翻译
│       ├── md.js                   # Markdown 渲染
│       ├── logger.js               # 前端日志 + 全局错误捕获
│       ├── experts.js              # 专家代理元数据
│       ├── assets/main.css         # 玻璃材质系统 / 动画
│       └── components/             # 页面与组件（约 20 个，见 frontend/src）
│
└── docs/                           # 参考文档（deepagents / DeepSeek API）
```

## API 概览

后端启动后，完整的 Swagger 文档位于 `http://127.0.0.1:8000/docs`。

<details>
<summary><b>认证接口</b></summary>

| Method | Endpoint | 说明 |
|---|---|---|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录（邮箱或昵称） |
| GET | `/api/auth/me` | 当前用户信息 |
| PUT | `/api/auth/profile` | 更新个人信息 |
| PUT | `/api/auth/password` | 修改密码 |
| POST | `/api/auth/logout` | 退出登录 |
| POST | `/api/auth/forgot-password` | 发送重置邮件 |
| POST | `/api/auth/reset-password` | 重置密码 |

</details>

<details>
<summary><b>对话接口</b></summary>

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `/api/conversations` | 对话列表 |
| POST | `/api/conversations` | 新建对话 |
| GET | `/api/conversations/{id}` | 对话详情 + 消息 |
| PATCH | `/api/conversations/{id}` | 重命名 / 置顶 |
| DELETE | `/api/conversations/{id}` | 删除对话 |
| DELETE | `/api/conversations/{id}/messages/{mid}` | 删除单条消息 |

</details>

<details>
<summary><b>聊天接口（核心）</b></summary>

```
POST /api/chat/{conversation_id}
```

**请求体：**

```json
{
  "message": "帮我分析这份数据",
  "image_ids": [],
  "enable_search": true,
  "enable_thinking": true,
  "enable_rag": false,
  "rag_files": [],
  "agent_id": 1,
  "model": "deepseek-flash",
  "reasoning_effort": "high",
  "mode": "general"
}
```

**SSE 事件流：**

| 事件 | 说明 |
|---|---|
| `{"type":"token","token":"..."}` | 回答内容（流式累加） |
| `{"type":"reasoning","reasoning":"..."}` | 思考过程 |
| `{"type":"todo","todos":[...]}` | 计划清单快照 |
| `{"type":"tool_call","tool":"...","args":{}}` | 工具调用卡片 |
| `{"type":"tool_result","tool":"...","result":"..."}` | 工具结果 |
| `{"status":"sub_started","subagent":"..."}` | 子代理开始 |
| `{"status":"sub_done","subagent":"..."}` | 子代理完成 |
| `{"type":"approval_request","action_id":1,...}` | 等待人工审批 |
| `{"status":"run_end","tokens":123}` | 运行结束 |
| `{"error":"..."}` | 异常信息 |

</details>

<details>
<summary><b>代理与运行</b></summary>

| Method | Endpoint | 说明 |
|---|---|---|
| GET / POST | `/api/agents` | 代理列表 / 创建 |
| PATCH / DELETE | `/api/agents/{id}` | 更新 / 删除代理 |
| POST | `/api/approvals/{action_id}` | 审批（approve / reject / edit） |
| POST | `/api/runs/{run_id}/stop` | 停止运行 |

</details>

<details>
<summary><b>知识库 / 技能 / 图片</b></summary>

| Method | Endpoint | 说明 |
|---|---|---|
| POST | `/api/kb/upload` | 上传知识库文件 |
| GET | `/api/kb/files` | 文件列表 |
| DELETE | `/api/kb/files/{id}` | 删除文件 |
| GET / POST | `/api/skills` | 技能列表 / 创建 |
| GET / PATCH / DELETE | `/api/skills/{id}` | 技能详情 / 更新 / 删除 |
| POST | `/api/skills/upload` | 上传 SKILL.md |
| POST | `/api/images` | 上传图片（多模态） |
| GET | `/api/images/{id}` | 获取图片（鉴权） |

</details>

<details>
<summary><b>模型供应商</b></summary>

| Method | Endpoint | 说明 |
|---|---|---|
| GET / POST | `/api/providers` | 供应商列表 / 添加 |
| PATCH / DELETE | `/api/providers/{id}` | 更新 / 删除（内置不可删） |
| POST | `/api/providers/{id}/test` | 连接测试 |

</details>

<details>
<summary><b>其他接口</b></summary>

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `/api/search?q=keyword` | 全文搜索消息 |
| GET | `/api/health` | 健康检查 |

</details>

## 数据库

SQLite WAL 模式，文件 `chat.db` 首次运行时自动创建。

| 表名 | 说明 |
|---|---|
| `users` | 用户账户（资料 / 头像 / 角色） |
| `conversations` | 对话记录（标题 / 置顶 / 时间） |
| `messages` | 消息内容（含图片引用） |
| `knowledge_files` | 知识库文件 |
| `agents` | 自定义代理配置 |
| `agent_runs` | 代理运行记录（工具 / 待办 / tokens） |
| `approvals` | 人工审批请求与决策 |
| `skills` | 技能（SKILL.md 元数据） |
| `skill_overrides` | 用户技能启用状态 |
| `providers` | 模型供应商（API Key 加密存储） |
| `images` | 上传图片（多模态消息） |

## 部署

### Nginx 反向代理

项目自带 Nginx 配置文件 `nginx/meikenai.conf`，将 8080 端口反向代理到 FastAPI 后端（127.0.0.1:8000）。

```bash
# 复制配置到 Nginx
sudo cp nginx/meikenai.conf /etc/nginx/sites-available/meikenai.conf
sudo ln -sf /etc/nginx/sites-available/meikenai.conf /etc/nginx/sites-enabled/

# 测试并重载
sudo nginx -t && sudo systemctl reload nginx
```

> 注意：域名未备案时，国内云厂商会拦截 80/443/8080 等常见 Web 端口。可临时使用 IP 直连访问，如 `http://<服务器IP>:8080`。

### 后端 systemd 服务（开机自启 + 崩溃重启）

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

### 更新部署

```bash
# 后端：拉取代码 + 重启服务
git pull && uv sync
sudo systemctl restart meikenai

# 前端：重新构建（Nginx 无需重启，浏览器 Ctrl+Shift+R 强制刷新）
cd frontend && npm install && npm run build
```

### 安全提示：不要在服务端携带个人 API Key

如果你要把项目部署为公共服务：

1. 使用**全新数据库**（不要拷贝本地 `chat.db`）
2. `.env` 中**不要写** `DEEPSEEK_API_KEY`，登录后在界面中配置
3. 不要拷贝 `config/fernet.key`（它用于解密数据库中的 Key）

这样内置供应商将以「未配置」状态运行，每位使用者在「管理模型」界面填入自己的 Key（加密存储，按用户隔离）。

## License

MIT
