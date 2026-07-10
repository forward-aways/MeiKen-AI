<p align="center">

# MeiKen AI

基于 FastAPI + Vue 3 的 AI 对话平台，集成 DeepSeek 大模型，支持联网搜索、深度思考、流式输出与多用户管理。

<img src="https://img.shields.io/badge/Python-3.13-5b57d2?logo=python" alt="Python">
<img src="https://img.shields.io/badge/Vue-3.x-5b57d2?logo=vuedotjs" alt="Vue">
<img src="https://img.shields.io/badge/FastAPI-0.139-5b57d2?logo=fastapi" alt="FastAPI">
<img src="https://img.shields.io/badge/license-MIT-5b57d2" alt="License">

</p>

---

## 目录

- [核心亮点](#核心亮点)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
  - [环境要求](#环境要求)
  - [安装与配置](#安装与配置)
  - [启动服务](#启动服务)
  - [默认账户](#默认账户)
- [项目结构](#项目结构)
- [API 概览](#api-概览)
  - [聊天接口](#聊天接口)
- [数据库](#数据库)
- [License](#license)

## 核心亮点

**AI 能力**
- SSE 流式对话，支持中途停止生成
- 多轮上下文记忆，自动维护对话历史
- Markdown 完整渲染（表格 / 代码高亮 / 列表 / 公式）
- 错误重试 + 消息编辑后重新生成
- **联网搜索**：博查 API 实时检索，AI 自动判断搜索时机，结果可折叠溯源
- **深度思考**：DeepSeek reasoning 模式，展示思维链 + 推理耗时

**用户与数据**
- 注册 / 登录（邮箱或昵称），JWT + httpOnly Cookie 鉴权
- 头像系统（上传图片 / 预设 emoji / 首字母兜底）
- 个人中心（昵称、签名、AI 称呼、修改密码）
- 忘记密码（SMTP 邮件重置）

**对话管理**
- 延迟创建：发送首条消息时才写入数据库
- 置顶 / 重命名 / 导出 Markdown / 右键菜单
- 侧边栏实时过滤 + 全文消息搜索

**交互体验**
- 深浅主题切换 / 中英文双语
- 落地页打字机动效 + 入场动画
- 胶囊按钮微交互（hover 浮起 + click 回弹）
- 侧边栏弹性折叠，滚动智能跟底

## 技术栈

| 类别 | 选型 |
|---|---|
| 后端框架 | FastAPI |
| AI 引擎 | LangChain + DeepSeek |
| 联网搜索 | 博查 Search API |
| 深度思考 | DeepSeek reasoning_content |
| 数据库 | SQLite（WAL 模式） |
| 认证 | bcrypt + JWT + httpOnly Cookie |
| 前端 | Vue 3 + Vite |
| 代码高亮 | highlight.js |
| 包管理 | uv + npm |

## 快速开始

### 环境要求

- Python >= 3.13
- Node.js >= 18
- [uv](https://docs.astral.sh/uv/) 包管理器

### 安装与配置

```bash
git clone https://github.com/你的用户名/MeiKen_AI.git
cd MeiKen_AI

# 安装依赖
uv sync
cd frontend && npm install && cd ..
```

创建 `.env` 文件：

```ini
DEEPSEEK_API_KEY="sk-your-key"
DEEPSEEK_BASE_URL="https://api.deepseek.com"

# 可选：联网搜索
BOCHA_API_KEY="sk-your-bocha-key"

# 可选：密码重置邮件
# SMTP_HOST=smtp.qq.com
# SMTP_PORT=587
# SMTP_USER=you@qq.com
# SMTP_PASSWORD=授权码
```

### 启动服务

```bash
# 终端 1：后端 → http://127.0.0.1:8000
uv run python main.py backend

# 终端 2：前端 → http://127.0.0.1:3000
cd frontend && npm run dev
```

### 默认账户

| 邮箱 | 密码 | 角色 |
|---|---|---|
| admin@meiken.ai | admin123 | admin |

首次启动且数据库无用户时自动创建。

## 项目结构

```
MeiKen_AI/
├── main.py                     # 启动器
├── pyproject.toml              # Python 依赖
├── backend/
│   ├── main.py                 # FastAPI 路由
│   ├── chat.py                 # 对话引擎（普通/搜索/思考四模式）
│   ├── database.py             # 数据库 CRUD
│   ├── schemas.py              # Pydantic 模型
│   └── auth.py                 # JWT 认证
├── frontend/
│   ├── package.json            # npm 依赖
│   ├── vite.config.js          # Vite 配置（含 /api 代理）
│   └── src/
│       ├── App.vue             # 根组件 + SSE 流处理
│       ├── store.js            # 全局响应式状态
│       ├── api.js              # 请求工具
│       ├── i18n.js             # 中英翻译
│       ├── md.js               # Markdown 渲染
│       ├── assets/main.css     # CSS 变量 / 动画
│       └── components/
│           ├── LoginPage.vue       # 登录 / 注册 / 重置
│           ├── Sidebar.vue         # 对话列表 / 搜索 / 设置
│           ├── ChatMessage.vue     # 消息 / 编辑 / 思考面板
│           ├── MessageInput.vue    # 输入框 / 胶囊按钮
│           ├── WelcomeScreen.vue   # 落地页 / 动画
│           ├── SearchPage.vue      # 全文搜索
│           └── ProfilePage.vue     # 个人信息
└── FEATURES.md                 # 功能迭代记录
```

## API 概览

后端启动后，完整的 Swagger 文档位于 `http://127.0.0.1:8000/docs`。

### 聊天接口

```
POST /api/chat/{conversation_id}
```

**请求体：**

```json
{
  "message": "今天天气怎么样？",
  "system_prompt": "你是一个有用的助手",
  "enable_search": true,
  "enable_thinking": false
}
```

**SSE 事件流：**

| 事件 | 说明 |
|---|---|
| `{"token":"..."}` | 回答 token（流式累加） |
| `{"reasoning":"..."}` | 思考过程（thinking 模式） |
| `{"thinking_done":3.5}` | 思考耗时（秒） |
| `{"status":"searching","query":"..."}` | 开始联网搜索 |
| `{"status":"searched","results":[...]}` | 搜索完成，附带来源 |
| `{"done":true,"id":42}` | 消息已持久化 |
| `{"error":"..."}` | 异常信息 |

## 数据库

三张核心表，SQLite WAL 模式，文件 `chat.db` 首次运行时自动创建。

| 表 | 核心字段 |
|---|---|
| users | id, email, nickname, password_hash, role, real_name, gender, birthday, bio, ai_address, avatar, avatar_color |
| conversations | id, user_id, title, created_at, updated_at |
| messages | id, conversation_id, role(user/assistant), content, created_at |

## License

MIT
