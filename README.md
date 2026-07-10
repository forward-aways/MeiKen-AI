# MeiKen AI

基于 FastAPI + LangChain + Vue 3 构建的智能对话平台，支持联网搜索、深度思考、多用户、流式输出与深浅主题切换。

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [API 文档](#api-文档)
- [数据库设计](#数据库设计)
- [License](#license)

## 功能特性

### AI 对话

- SSE 流式逐字输出，支持停止生成
- 多轮对话上下文记忆
- Markdown 渲染（标题 / 列表 / 表格 / 代码块 / 语法高亮）
- 代码块一键复制
- 错误重试
- 智能滚动（翻历史时不跟滚，生成完毕自动回到底部）

### 联网搜索

- 输入框胶囊开关，一键启用
- DeepSeek Function Calling 自动判断是否需要搜索
- 博查 API 实时搜索（新闻 / 天气 / 时事等）
- 搜索结果来源可折叠展示（网页标题 + 摘要 + 链接）
- AI 回答中引用来源链接

### 深度思考

- DeepSeek 思考模式，展示思维链推理过程
- AI 消息上方可折叠思考面板，显示思考耗时
- 思考 + 联网搜索组合模式

### 用户系统

- 注册 / 登录（邮箱或昵称 + 密码）
- JWT + httpOnly Cookie 认证
- 头像系统（上传图片 / 预设 emoji / 首字母 + 颜色兜底）
- 个人信息中心（基础信息 + 个性化 + 账号安全 + 修改密码）
- 忘记密码（SMTP 邮件重置）

### 对话管理

- 新建 / 切换 / 删除 / 重命名
- 对话置顶（右键菜单，localStorage 持久化）
- 全文搜索 + 侧边栏实时过滤
- 导出 Markdown

### 界面交互

- 深浅主题一键切换
- 中英文国际化
- 落地页打字机动效 + 层叠入场动画
- 输入框胶囊微交互（hover 浮起 + click 回弹）
- 侧边栏弹性收起 / 展开 + 悬浮操作栏
- 文字选中样式优化

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI |
| AI 引擎 | LangChain + DeepSeek（OpenAI 兼容） |
| 联网搜索 | 博查 Search API |
| 深度思考 | DeepSeek 思考模式（reasoning_content） |
| 数据库 | SQLite（WAL 模式） |
| 认证 | JWT + httpOnly Cookie + bcrypt |
| 前端 | Vue 3（Vite + SFC 组件化） |
| 代码高亮 | highlight.js |
| 包管理 | uv（Python）+ npm（前端） |

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/MeiKen_AI.git
cd MeiKen_AI
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
DEEPSEEK_API_KEY="sk-your-key"
DEEPSEEK_BASE_URL="https://api.deepseek.com"

# 联网搜索（可选）
BOCHA_API_KEY="sk-your-bocha-key"

# 密码重置邮件（可选，留空则终端打印重置链接）
# SMTP_HOST=smtp.qq.com
# SMTP_PORT=587
# SMTP_USER=you@qq.com
# SMTP_PASSWORD=你的授权码
```

### 3. 安装依赖

```bash
uv sync                    # Python 后端
cd frontend && npm install # 前端
```

### 4. 启动服务

```bash
# 终端 1 - 后端 (http://127.0.0.1:8000)
uv run python main.py backend

# 终端 2 - 前端开发模式 (http://127.0.0.1:3000)
cd frontend && npm run dev
```

### 5. 登录

| 邮箱 | 密码 |
|---|---|
| admin@meiken.ai | admin123 |

首次启动自动创建管理员账户，支持邮箱或昵称登录。

## 项目结构

```
MeiKen_AI/
├── main.py                  # 启动器
├── pyproject.toml           # Python 依赖管理
├── .env                     # 环境变量（不入库）
├── backend/
│   ├── main.py              # FastAPI 应用 + 路由
│   ├── chat.py              # 对话引擎（普通/搜索/思考/搜索+思考）
│   ├── database.py          # 数据库层（表定义 + CRUD）
│   ├── schemas.py           # Pydantic 模型
│   └── auth.py              # JWT 认证 + 密码重置
├── frontend/
│   ├── index.html           # Vite 入口
│   ├── package.json         # npm 依赖
│   ├── vite.config.js       # Vite 配置（含 /api 代理）
│   └── src/
│       ├── main.js          # 应用入口
│       ├── App.vue          # 根组件（状态编排 + SSE 流）
│       ├── store.js         # 全局响应式状态
│       ├── api.js           # API 工具函数
│       ├── i18n.js          # 中英文翻译表
│       ├── md.js            # Markdown 渲染器
│       ├── assets/main.css  # 全局样式（变量 / 重置 / 动画）
│       └── components/
│           ├── LoginPage.vue      # 登录 / 注册 / 忘记密码
│           ├── Sidebar.vue        # 对话列表 / 搜索 / 设置
│           ├── ChatMessage.vue    # 消息气泡 / 编辑 / 复制
│           ├── MessageInput.vue   # 输入框 / 发送 / 停止
│           ├── WelcomeScreen.vue  # 落地页 / 打字机动效
│           ├── SearchPage.vue     # 全文搜索
│           └── ProfilePage.vue    # 个人信息 / 头像 / 密码
└── FEATURES.md              # 功能迭代记录
```

## API 文档

启动后端后访问 `http://127.0.0.1:8000/docs` 查看 Swagger UI。

### 认证

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
| POST | `/api/chat/{id}` | 发送消息（SSE 流式响应） |

请求体：

```json
{
  "message": "Hello!",
  "system_prompt": "You are a helpful assistant.",
  "enable_search": false,
  "enable_thinking": false
}
```

SSE 事件类型：

| 事件 | 说明 |
|---|---|
| `{"token": "..."}` | AI 回答内容（流式） |
| `{"reasoning": "..."}` | 思考过程内容（深度思考模式） |
| `{"thinking_done": 3.0}` | 思考耗时（秒） |
| `{"status": "searching", "query": "..."}` | 开始搜索 |
| `{"status": "searched", "results": [...]}` | 搜索完成 + 结果 |
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

## 数据库设计

SQLite 数据库文件 `chat.db`（运行时自动生成），包含三张表：

| 表 | 说明 | 主要字段 |
|---|---|---|
| users | 用户 | id, email, nickname, password_hash, role, created_at, real_name, gender, birthday, bio, ai_address, avatar, avatar_color |
| conversations | 对话 | id, user_id, title, created_at, updated_at |
| messages | 消息 | id, conversation_id, role, content, created_at |

## License

MIT
