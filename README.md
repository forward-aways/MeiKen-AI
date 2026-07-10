# MeiKen AI

基于 **FastAPI + LangChain + Vue 3** 构建的智能对话平台，支持多用户、联网搜索、深度思考、Markdown 渲染、流式输出、深浅主题切换。

## 技术栈

| 层 | 技术 |
|---|---|---|
| 后端框架 | FastAPI |
| AI 引擎 | LangChain + DeepSeek (OpenAI 兼容) |
| 联网搜索 | 博查 Search API (bochaai.com) |
| 深度思考 | DeepSeek 思考模式 (reasoning_content) |
| 数据库 | SQLite (WAL 模式) |
| 认证 | JWT + httpOnly Cookie + bcrypt |
| 前端 | Vue 3 (Vite + SFC 组件化) |
| 代码高亮 | highlight.js (GitHub Dark) |
| 包管理 | uv (Python) + npm (前端) |

## 功能

### 核心
- [x] SSE 流式对话 (DeepSeek)
- [x] 多轮对话上下文记忆
- [x] Markdown 渲染 (标题/列表/表格/代码块/粗斜体)
- [x] 表格内 Markdown 格式支持
- [x] 代码块语法高亮 + 一键复制
- [x] 停止生成 (AbortController)
- [x] 错误重试
- [x] 智能滚动 (用户翻历史时不跟滚，生成完毕后自动滚到底部)

### 联网搜索
- [x] 联网搜索开关 (输入框左下角胶囊按钮)
- [x] DeepSeek Function Calling 自动判断是否需要搜索
- [x] 博查 API 实时搜索 (新闻/天气/时事等)
- [x] 搜索结果来源展示 (可折叠面板，显示网页标题+摘要+链接)
- [x] AI 回答中引用搜索来源 (markdown 链接)
- [x] 搜索中状态指示器 ("正在搜索…")

### 深度思考
- [x] 深度思考开关 (输入框左下角胶囊按钮)
- [x] DeepSeek 思考模式 (reasoning_content 思维链)
- [x] 思考过程展示 (AI 消息上方可折叠面板)
- [x] 思考耗时显示 ("思考了 X 秒")
- [x] 思考 + 联网搜索组合模式 (思考模式下支持工具调用)

### 用户系统
- [x] 注册 / 登录 (邮箱或昵称 + 密码)
- [x] JWT + httpOnly Cookie 认证
- [x] 默认管理员账户
- [x] 个人信息卡片 (昵称编辑、邮箱查看)
- [x] 个人信息中心 (头像 + 基础信息 + 个性化 + 账号信息 + 修改密码)
- [x] 头像系统 (上传图片 / 预设 emoji / 首字母 + 颜色兜底)
- [x] 基础信息 (昵称、真实姓名、性别、生日)
- [x] 个性化 (个性签名、AI 称呼)
- [x] 账号信息 (邮箱、角色、注册时间、对话数)
- [x] 忘记密码 (SMTP 邮件重置)
- [x] 退出登录

### 对话管理
- [x] 新建对话 (延迟创建: 发送首个消息时才写入数据库)
- [x] 切换 / 删除对话
- [x] 对话重命名
- [x] 对话置顶 (右键菜单，localStorage 持久化)
- [x] 对话搜索 (侧边栏实时过滤)
- [x] 全文搜索 (搜索所有消息内容)
- [x] 对话导出 Markdown
- [x] 右键菜单 (置顶 / 重命名 / 导出 / 删除)

### 消息操作
- [x] 编辑已发送消息并重新生成
- [x] 用户消息复制 + 编辑按钮
- [x] AI 回复操作 (复制 / 复制 Markdown / 重新生成)
- [x] AI 消息头部显示 "MeiKen AI" 名称

### 个性化
- [x] 深浅主题切换
- [x] 中英文切换
- [x] 自定义系统提示词 (智能体)
- [x] 设置弹窗 (主题 / 语言)

### 交互
- [x] Enter 发送 / Shift+Enter 换行 / Esc 停止
- [x] 落地页 (大输入框 + 推荐问题 + 浮动动效)
- [x] 落地页打字机动效 (标题逐字 + 光标)
- [x] 落地页层叠入场动画 (可回放)
- [x] 落地页输入框内置联网搜索/深度思考胶囊
- [x] 消息入场动画
- [x] 打字指示器
- [x] textarea 自适应撑高
- [x] 发送按钮内置在输入框中 (圆形纸飞机图标)
- [x] 输入框胶囊微交互 (hover 浮起 + click 回弹动效)
- [x] 侧边栏弹性收起/展开动画
- [x] 收起后显示悬浮操作栏 (展开 / 搜索 / 新建对话)
- [x] 回到底部按钮 (矢量图标)
- [x] 系统 Logo / Favicon
- [x] 文字选中样式优化 (透明背景 + 加深选中色)

## 快速开始

### 1. 配置环境

```bash
# .env 文件
DEEPSEEK_API_KEY="sk-your-key"
DEEPSEEK_BASE_URL="https://api.deepseek.com"

# 联网搜索（可选，留空则搜索功能不可用）
BOCHA_API_KEY="sk-your-bocha-key"

# 密码重置邮件（可选，留空则终端打印重置链接）
# SMTP_HOST=smtp.qq.com
# SMTP_PORT=587
# SMTP_USER=you@qq.com
# SMTP_PASSWORD=你的授权码
```

### 2. 安装依赖

```bash
uv sync                    # Python 后端依赖
cd frontend && npm install # 前端依赖
```

### 3. 启动

```bash
# 终端 1 - 后端 (http://127.0.0.1:8000)
uv run python main.py backend

# 终端 2 - 前端 (http://127.0.0.1:3000)
uv run python main.py frontend    # 自动构建并启动
# 或开发模式（热更新）
cd frontend && npm run dev
```

### 4. 登录

| 账户 | 邮箱 | 密码 |
|---|---|---|
| 管理员 | admin@meiken.ai | admin123 |

首次启动自动创建管理员账户。支持邮箱或昵称+密码登录。

## 项目结构

```
MeiKen_AI/
├── main.py                  # 启动器
├── pyproject.toml           # Python 依赖管理
├── .env                     # 环境变量 (API Key)
├── chat.db                  # SQLite 数据库 (自动生成)
│
├── backend/
│   ├── main.py              # FastAPI 应用 + 路由
│   ├── database.py          # 数据库层 (表定义 + CRUD)
│   ├── schemas.py           # Pydantic 模型
│   ├── chat.py              # 对话引擎 (普通/联网搜索/深度思考/搜索+思考)
│   └── auth.py              # JWT 认证 + 密码重置
│
├── frontend/
│   ├── index.html           # Vite 入口
│   ├── package.json         # npm 依赖
│   ├── vite.config.js       # Vite 配置（含 /api 代理）
│   ├── src/
│   │   ├── main.js          # 应用入口
│   │   ├── App.vue          # 根组件（状态编排 + SSE 流）
│   │   ├── store.js         # 全局响应式状态
│   │   ├── api.js           # API 工具函数
│   │   ├── i18n.js          # 中英文翻译表
│   │   ├── md.js            # Markdown 渲染器
│   │   ├── assets/main.css  # 全局样式（变量/重置/动画）
│   │   └── components/
│   │       ├── LoginPage.vue      # 登录/注册/忘记密码
│   │       ├── Sidebar.vue        # 对话列表/搜索/设置/用户区
│   │       ├── ChatMessage.vue    # 消息气泡/编辑/复制
│   │       ├── MessageInput.vue   # 输入框/发送/停止
│   │       ├── WelcomeScreen.vue  # 落地页/打字机动效
│   │       ├── SearchPage.vue     # 全文搜索
│   │       └── ProfilePage.vue    # 个人信息/头像/密码修改
│   └── dist/                # Vite 构建产物
│
└── FEATURES.md              # 功能设计文档
```

## API 文档

启动后端后访问 `http://127.0.0.1:8000/docs` (Swagger UI)。

### 认证

| Method | Endpoint | 说明 |
|---|---|---|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录 (邮箱或昵称) |
| GET | `/api/auth/me` | 当前用户信息 |
| PUT | `/api/auth/profile` | 更新个人信息 (昵称/真实姓名/性别/生日/签名/AI称呼/头像/头像色) |
| PUT | `/api/auth/password` | 修改密码 (需旧密码) |
| POST | `/api/auth/logout` | 退出 (清除 Cookie) |
| POST | `/api/auth/forgot-password` | 发送重置邮件 |
| POST | `/api/auth/reset-password` | 重置密码 |

### 对话

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `/api/conversations` | 对话列表 |
| POST | `/api/conversations` | 新建对话 |
| GET | `/api/conversations/{id}` | 对话详情 + 消息 |
| PATCH | `/api/conversations/{id}` | 重命名对话 |
| DELETE | `/api/conversations/{id}` | 删除对话 |

### 聊天

| Method | Endpoint | 说明 |
|---|---|---|
| POST | `/api/chat/{id}` | 发送消息 (SSE 流式响应) |

请求体:
```json
{
  "message": "Hello!",
  "system_prompt": "You are a helpful assistant.",
  "enable_search": false,
  "enable_thinking": false
}
```

SSE 事件类型:
| 事件 | 说明 |
|---|---|
| `{"token": "..."}` | AI 回答内容 (流式) |
| `{"reasoning": "..."}` | 思考过程内容 (深度思考模式) |
| `{"thinking_done": 3.0}` | 思考耗时 (秒) |
| `{"status": "searching", "query": "..."}` | 开始搜索 |
| `{"status": "searched", "query": "...", "results": [...]}` | 搜索完成 + 结果 |
| `{"done": true, "id": 123}` | 消息保存完成 |
| `{"error": "..."}` | 错误 |

### 搜索

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `/api/search?q=keyword` | 全文搜索消息 |

### 健康检查

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `/api/health` | 服务状态 |

## 数据库

SQLite 数据库文件 `chat.db` 包含三张表:

- **users** — 用户 (id, email, nickname, password_hash, role, created_at, real_name, gender, birthday, bio, ai_address, avatar, avatar_color)
- **conversations** — 对话 (id, user_id, title, created_at, updated_at)
- **messages** — 消息 (id, conversation_id, role, content, created_at)

## 默认管理员

| 字段 | 值 |
|---|---|
| 邮箱 | admin@meiken.ai |
| 密码 | admin123 |
| 角色 | admin |

仅在数据库无用户时自动创建，不会重复。

## 设计参考

前端设计参考了 ChatGPT、Claude 等主流 AI 对话产品的交互模式:

- 左侧对话列表 + 右侧聊天区域
- 落地页居中大输入框 + 打字机动效
- 消息气泡 (用户紫色 / AI 透明)
- AI 消息头像 + 名称标识
- SSE 流式逐字输出
- 深浅主题一键切换
- 侧边栏弹性收起/展开，收起后显示悬浮操作栏
- 对话置顶、个人信息管理
