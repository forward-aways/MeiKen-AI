<div align="center">

# MeiKen AI

基于 FastAPI + LangChain + Vue 3 的智能对话平台

支持联网搜索 · 深度思考 · 多用户 · 流式输出 · 深浅主题

</div>

## ✨ 功能特性

### AI 对话
- **流式输出** - SSE 逐字渲染，支持停止生成
- **多轮记忆** - 自动维护对话上下文
- **Markdown 渲染** - 标题/列表/表格/代码块/语法高亮
- **深度思考** - DeepSeek 思考模式，展示思维链推理过程及耗时
- **联网搜索** - 博查 API 实时搜索，结果来源可折叠展示

### 用户系统
- 注册/登录（邮箱或昵称 + 密码）
- JWT + httpOnly Cookie 认证
- 头像系统（上传图片 / emoji / 首字母兜底）
- 个人信息中心（基础信息 + 个性化 + 账号安全）

### 对话管理
- 新建 / 切换 / 删除 / 重命名
- 对话置顶 + 右键菜单
- 全文搜索 + 侧边栏实时过滤
- 导出 Markdown

### 界面交互
- 深浅主题一键切换
- 中英文国际化
- 落地页打字机动效 + 层叠入场动画
- 输入框胶囊微交互（hover 浮起 + click 回弹）
- 智能滚动 + 回到底部

## 🛠 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + LangChain + DeepSeek |
| 前端 | Vue 3 + Vite |
| 数据库 | SQLite (WAL) |
| 认证 | JWT + httpOnly Cookie + bcrypt |
| 联网搜索 | 博查 Search API |
| 包管理 | uv + npm |

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/MeiKen_AI.git
cd MeiKen_AI
```

### 2. 配置环境变量

```bash
# .env
DEEPSEEK_API_KEY="sk-your-key"
DEEPSEEK_BASE_URL="https://api.deepseek.com"
BOCHA_API_KEY="sk-your-bocha-key"       # 联网搜索（可选）
```

### 3. 安装依赖

```bash
uv sync                    # Python
cd frontend && npm install # 前端
```

### 4. 启动

```bash
# 后端
uv run python main.py backend

# 前端（开发模式）
cd frontend && npm run dev
```

### 5. 登录

| 邮箱 | 密码 |
|---|---|
| admin@meiken.ai | admin123 |

## 📁 项目结构

```
├── main.py                 # 启动器
├── backend/
│   ├── main.py             # FastAPI 路由
│   ├── chat.py             # 对话引擎（普通/搜索/思考/搜索+思考）
│   ├── database.py         # SQLite CRUD
│   ├── schemas.py          # Pydantic 模型
│   └── auth.py             # JWT 认证
├── frontend/src/
│   ├── App.vue             # 根组件 + SSE 流处理
│   ├── store.js            # 全局状态
│   ├── components/         # 7 个 SFC 组件
│   └── assets/main.css     # CSS 变量体系
└── FEATURES.md             # 功能迭代记录
```

## 📖 API 文档

启动后端后访问 `http://127.0.0.1:8000/docs` 查看 Swagger UI。

## 📄 License

MIT
