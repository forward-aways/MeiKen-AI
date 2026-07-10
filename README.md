<div align="center">

# MeiKen AI

基于 FastAPI + Vue 3 的 AI 对话平台，集成 DeepSeek 大模型，支持联网搜索、深度思考、流式输出与多用户管理。

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
- [License](#license)

## 核心亮点

<table>
<tr>
<td width="50%" valign="top">

### AI 对话

- SSE 流式逐字输出，支持中途停止
- 多轮上下文记忆，自动维护历史
- Markdown 完整渲染（表格 / 代码高亮 / 列表）
- 错误重试 + 消息编辑后重新生成
- 智能滚动（翻历史不跟滚，完成自动回底）

</td>
<td width="50%" valign="top">

### 联网搜索

- 输入框胶囊开关，一键启用
- DeepSeek Function Calling 自动判断搜索时机
- 博查 API 实时检索（新闻 / 天气 / 时事）
- 搜索结果可折叠溯源（标题 + 摘要 + 链接）

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 深度思考

- DeepSeek reasoning 模式，展示思维链推理
- AI 消息上方可折叠思考面板
- 思考耗时显示（"思考了 X 秒"）
- 支持 思考 + 搜索 组合模式

</td>
<td width="50%" valign="top">

### 用户系统

- 注册 / 登录（邮箱或昵称 + 密码）
- JWT + httpOnly Cookie 鉴权
- 头像系统（上传 / emoji / 首字母兜底）
- 个人中心 + 忘记密码（SMTP 重置）

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 对话管理

- 延迟创建（首条消息时才入库）
- 置顶 / 重命名 / 导出 Markdown
- 右键菜单（置顶 / 重命名 / 导出 / 删除）
- 全文搜索 + 侧边栏实时过滤

</td>
<td width="50%" valign="top">

### 交互体验

- 深浅主题切换 / 中英文双语
- 落地页打字机动效 + 入场动画
- 胶囊微交互（hover 浮起 + click 回弹）
- 侧边栏弹性折叠 + 悬浮操作栏

</td>
</tr>
</table>

## 技术栈

| 类别 | 选型 | 说明 |
|:---:|---|---|
| 后端 | FastAPI | 异步高性能 ASGI 框架 |
| AI 引擎 | LangChain + DeepSeek | OpenAI 兼容接口 |
| 联网搜索 | 博查 Search API | 专为 AI 优化的搜索 |
| 深度思考 | DeepSeek reasoning_content | 思维链推理 |
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
git clone git@github.com:forward-aways/MeiKen-AI.git
cd MeiKen_AI

# 安装 Python（uv 自动下载所需版本）
uv python install 3.13

# 安装后端依赖（自动创建虚拟环境）
uv sync

# 安装前端依赖
cd frontend && npm install && cd ..
```

创建 `.env` 文件：

```ini
DEEPSEEK_API_KEY="sk-your-key"
DEEPSEEK_BASE_URL="https://api.deepseek.com"

# 可选：联网搜索
BOCHA_API_KEY="sk-your-bocha-key"

# 可选：密码重置邮件（留空则终端打印链接）
# SMTP_HOST=smtp.qq.com
# SMTP_PORT=587
# SMTP_USER=you@qq.com
# SMTP_PASSWORD=授权码
```

### 启动服务

```bash
# 终端 1：后端
uv run python main.py backend          # → http://127.0.0.1:8000

# 终端 2：前端
cd frontend && npm run dev             # → http://127.0.0.1:3000
```

> 启动后访问 `http://127.0.0.1:8000/docs` 可查看 Swagger API 文档。

### 默认账户

| 邮箱 | 密码 | 角色 |
|---|---|:---:|
| admin@meiken.ai | admin123 | admin |

> 首次启动且数据库无用户时自动创建，支持邮箱或昵称登录。

## 项目结构

```
MeiKen_AI/
├── main.py                         # 启动器
├── pyproject.toml                  # Python 依赖
│
├── backend/
│   ├── main.py                     # FastAPI 路由
│   ├── chat.py                     # 对话引擎（普通 / 搜索 / 思考 / 搜索+思考）
│   ├── database.py                 # SQLite CRUD
│   ├── schemas.py                  # Pydantic 模型
│   └── auth.py                     # JWT 认证 + 密码重置
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
│       ├── assets/main.css         # CSS 变量 / 动画
│       └── components/
│           ├── LoginPage.vue       # 登录 / 注册 / 重置
│           ├── Sidebar.vue         # 对话列表 / 搜索 / 设置
│           ├── ChatMessage.vue     # 消息 / 编辑 / 思考面板
│           ├── MessageInput.vue    # 输入框 / 胶囊按钮
│           ├── WelcomeScreen.vue   # 落地页 / 动画
│           ├── SearchPage.vue      # 全文搜索
│           └── ProfilePage.vue     # 个人信息
│
└── FEATURES.md                     # 功能迭代记录
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
| PATCH | `/api/conversations/{id}` | 重命名对话 |
| DELETE | `/api/conversations/{id}` | 删除对话 |

</details>

<details>
<summary><b>聊天接口（核心）</b></summary>

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
| `{"token":"..."}` | 回答内容（流式累加） |
| `{"reasoning":"..."}` | 思考过程（thinking 模式） |
| `{"thinking_done":3.5}` | 思考耗时（秒） |
| `{"status":"searching","query":"..."}` | 开始联网搜索 |
| `{"status":"searched","results":[...]}` | 搜索完成，附带来源 |
| `{"done":true,"id":42}` | 消息已持久化 |
| `{"error":"..."}` | 异常信息 |

</details>

<details>
<summary><b>其他接口</b></summary>

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `/api/search?q=keyword` | 全文搜索消息 |
| GET | `/api/health` | 健康检查 |

</details>

## 数据库

三张核心表，SQLite WAL 模式，文件 `chat.db` 首次运行时自动创建。

| 表名 | 说明 | 核心字段 |
|---|---|---|
| `users` | 用户账户 | `id` `email` `nickname` `password_hash` `role` `real_name` `gender` `birthday` `bio` `ai_address` `avatar` `avatar_color` |
| `conversations` | 对话记录 | `id` `user_id` `title` `created_at` `updated_at` |
| `messages` | 消息内容 | `id` `conversation_id` `role` `content` `created_at` |

## License

MIT
