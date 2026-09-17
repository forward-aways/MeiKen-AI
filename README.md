<div align="center">

# MeiKen AI Harness

可自托管的多智能体 AI 工作站：deepagents 编排、多模型供应商、联网搜索、私有知识库、技能系统与多模态输入。

<img src="https://img.shields.io/badge/Python-3.13-5b57d2?logo=python" alt="Python">
<img src="https://img.shields.io/badge/Vue-3.x-5b57d2?logo=vuedotjs" alt="Vue">
<img src="https://img.shields.io/badge/FastAPI-0.139-5b57d2?logo=fastapi" alt="FastAPI">
<img src="https://img.shields.io/badge/version-2.0.0-5b57d2" alt="Version">
<img src="https://img.shields.io/badge/license-MIT-5b57d2" alt="License">

**中文** · [English](README.en.md) · [部署文档](docs/DEPLOYMENT.md) · [API 文档](docs/API.md)

</div>

---

## 简介

MeiKen AI Harness 是一个可自托管的多智能体对话平台。后端基于 [deepagents](https://github.com/langchain-ai/deepagents)（LangGraph）编排多代理工作流，前端提供液态玻璃质感的交互界面。

它把「代理编排」与「可落地部署」放在同等重要的位置：既可以本地开发，也可以直接跑在服务器上（后端同时托管前端构建产物），并且不强制携带任何个人 API Key——每位使用者在界面中配置自己的模型供应商。

- 快速体验：见 [快速开始](#快速开始)
- 服务器部署：见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- 接口细节：见 [docs/API.md](docs/API.md)，或运行后的 `/docs`

## 功能特性

### 多智能体引擎
- 内置 5 个代理：通用助手 / 研究员 / 代码专家 / 数据分析师 / 写作助手
- 子代理委派：协调者通过 `task` 工具把独立子任务分派给研究员、分析师
- 执行时间线：工具调用、子代理与计划以时间线呈现，可展开查看参数与结果
- 计划清单：`write_todos` 实时更新待办进度
- 人工审批（HITL）：敏感工具调用可批准 / 拒绝 / 修改参数
- 三种人格模式：通用 / 编程 / 办公

### 模型与多模态
- 多供应商：内置 DeepSeek + 任意 OpenAI 兼容接口（自定义 Base URL、模型列表、上下文窗口）
- API Key 使用 Fernet 对称加密存储，按用户隔离，不落明文
- 一键连接测试、启用 / 停用，模型胶囊二级菜单直接切换
- 图片粘贴 / 拖拽 / 预览，多模态模型直读图片，非多模态模型自动降级为纯文本
- 思考模式三档（快速 / 标准 / 深度）与独立推理强度，思维链可折叠并显示耗时

### 知识库与技能
- 知识库（RAG）：支持 PDF / Word / Excel / PPT / CSV / HTML / Markdown / 纯文本等格式，向量检索并回溯来源
- 用户文件工作区：上传文件与 AI 生成文件按用户隔离落盘，支持列表 / 预览 / 下载
- 技能系统：`SKILL.md` 格式，可创建 / 上传 / 编辑 / 启停，按用户存储并按需加载

### 交互与工程
- 液态玻璃 / 亚克力拟物质感，深浅主题切换，中英文双语
- SSE 流式输出，智能滚动（翻看历史不跟随，完成后自动回底）
- 对话置顶 / 重命名 / 导出 Markdown / 全文搜索，消息删除与重新生成
- 注册 / 登录（邮箱或昵称）、JWT + httpOnly Cookie、头像与个人中心、忘记密码
- 统一日志（控制台着色 + 文件每日轮转），请求级追踪 `X-Request-Id`

## 技术栈

| 类别 | 选型 |
|:---:|---|
| 后端框架 | FastAPI（ASGI） |
| 代理引擎 | deepagents + LangGraph + LangChain |
| 默认模型 | DeepSeek V4.1 Flash（OpenAI 兼容） |
| 多供应商 | 任意 OpenAI 兼容接口 |
| 密钥加密 | cryptography（Fernet） |
| 联网搜索 | 博查 Search API |
| 知识库 | Chroma + 向量检索 |
| 数据库 | SQLite（WAL 模式） |
| 认证 | bcrypt + JWT |
| 前端 | Vue 3 + Vite |
| 代码高亮 | highlight.js |
| 包管理 | uv + npm |

## 快速开始

### 环境要求

| 依赖 | 版本 | 说明 |
|:---:|:---:|---|
| uv | latest | 自动管理 Python 版本与虚拟环境（[安装指南](https://docs.astral.sh/uv/getting-started/installation/)） |
| Node.js | >= 18 | 仅构建前端时需要 |

### 安装

```bash
git clone https://github.com/forward-aways/MeiKen-AI.git
cd MeiKen-AI

# 后端依赖（uv 自动下载 Python 3.13 并创建虚拟环境）
uv python install 3.13
uv sync

# 前端依赖
cd frontend && npm install && cd ..
```

### 配置

```bash
cp .env.example .env
```

按需修改 `.env`，生产环境至少修改 `JWT_SECRET` 与 `ADMIN_PASSWORD`。`DEEPSEEK_API_KEY` 与 `BOCHA_API_KEY` 可留空，登录后在界面中配置。

### 启动

```bash
# 后端：http://127.0.0.1:8000
uv run python main.py backend

# 前端（开发模式，热更新）：http://127.0.0.1:3000
uv run python main.py frontend
```

`main.py frontend` 会在 `frontend/dist` 不存在时自动构建，并以静态服务器方式启动。
生产部署时更推荐先 `npm run build`，由后端直接托管构建产物。

接口文档：`http://127.0.0.1:8000/docs`。

### 默认管理员

首次启动且数据库无用户时自动创建管理员账户：

| 项目 | 值 |
|---|---|
| 邮箱 | `admin@meiken.ai` |
| 密码 | `.env` 中的 `ADMIN_PASSWORD`（默认 `admin123`） |

> 生产环境请修改 `ADMIN_PASSWORD`，并让其他使用者自行注册，不要共用管理员账户。

### 配置模型

登录后点击模型胶囊 → 「管理模型」：

1. 内置 DeepSeek 供应商已自动创建，填入自己的 API Key 即可使用
2. 也可添加任意 OpenAI 兼容供应商（自定义 Base URL、模型列表、上下文窗口）
3. API Key 加密存储于本地数据库，不会上传任何第三方

## 项目结构

<details>
<summary>展开查看目录说明</summary>

```
MeiKen-AI/
├── main.py                      # 启动器（backend / frontend）
├── pyproject.toml               # Python 依赖（uv）
├── .env.example                 # 环境变量模板
├── LICENSE
├── README.md / README.en.md
│
├── backend/
│   ├── main.py                  # 应用装配（中间件 / 路由 / 生命周期 / 静态托管）
│   ├── config.py                # 集中配置（环境变量 / 路径 / 默认值）
│   ├── middleware.py            # 请求上下文中间件（X-Request-Id / 用户关联）
│   ├── runtime.py               # 运行时单例（代理工厂 / 检查点 / 并发闸门）
│   ├── log.py                   # 日志系统（控制台着色 + 文件每日轮转）
│   ├── auth.py                  # JWT 认证 / 密码哈希 / 密码重置
│   ├── crypto.py                # API Key Fernet 加密
│   ├── schemas.py               # Pydantic 请求 / 响应模型
│   ├── skills.py                # SKILL.md 校验与解析
│   ├── rag.py                   # 知识库：切分 / 向量化 / 检索
│   ├── workspace.py             # 用户文件工作区（路径安全 / 旧文件迁移）
│   ├── db/                      # 数据访问层（按业务域拆分）
│   │   ├── _core.py             # 连接管理 / 建表 / 列迁移
│   │   └── users / convs / agents / providers / skills / kb / images
│   ├── routes/                  # HTTP 路由层
│   │   └── auth / convs / chat / agents / skills / kb / providers / images / files / misc
│   ├── services/
│   │   └── chat_stream.py       # SSE 编排（对话与审批共用）
│   ├── documents/               # 多格式文档解析
│   │   └── parsers/             # text / csv / pdf / docx / xlsx / pptx / html + 注册表
│   └── agent/                   # 多智能体引擎（deepagents）
│       ├── bridge.py            # 流式事件桥接（SSE 事件协议）
│       ├── factory.py           # 代理工厂 / 缓存 / 审批中断 / 文件系统后端
│       ├── identity.py          # 人格与模式（general / code / work）
│       ├── llm.py               # 供应商解析 + 模型构建
│       ├── registry.py          # 内置代理与子代理定义
│       └── tools.py             # 工具（联网搜索 / 知识库）
│
├── tests/                       # 后端测试（pytest）
│   ├── test_smoke.py            # 核心接口冒烟测试
│   ├── test_documents.py        # 文档解析测试
│   └── test_files.py            # 文件工作区测试
│
├── frontend/
│   ├── package.json             # npm 依赖
│   ├── vite.config.js           # Vite 配置（开发模式 /api 代理）
│   └── src/
│       ├── App.vue              # 根组件 + SSE 流处理
│       ├── store.js / api.js / i18n.js / md.js / logger.js / experts.js
│       ├── assets/main.css      # 玻璃材质系统 / 全局动画
│       └── components/          # 页面与组件（约 20 个）
│
├── nginx/
│   └── meikenai.conf            # Nginx 反向代理示例
│
└── docs/                        # 文档
    ├── DEPLOYMENT.md            # 部署指南
    ├── API.md                   # 接口清单
    ├── DATABASE.md              # 数据库结构
    ├── deepagents官方参考文档/
    └── deepseekAPI参考文档/
```

</details>

## 运行测试

```bash
uv run --with pytest python -m pytest tests/ -v
```

> 首次运行包含知识库的测试时，Chroma 会下载一个约 79MB 的嵌入模型，耗时取决于网络。
> Windows 下若出现临时目录权限错误，追加 `--basetemp=%TEMP%\pytest-tmp -p no:cacheprovider`。

## 部署

生产形态：Nginx 反向代理 → FastAPI（后端同时托管前端构建产物）。

```bash
# 1. 安装依赖
uv sync
cd frontend && npm install && npm run build && cd ..

# 2. 配置环境变量（至少修改 JWT_SECRET / ADMIN_PASSWORD）
cp .env.example .env && vi .env

# 3. 启动
uv run python main.py backend
```

完整的服务器部署步骤（前置条件、systemd 开机自启、Nginx 配置、更新流程、常见问题）见 **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**。

**服务器安全要点**

- 使用全新数据库，不要拷贝本地 `chat.db`
- `.env` 中不要写 `DEEPSEEK_API_KEY`，由使用者登录后自行配置
- 不要拷贝 `config/fernet.key`（它用于解密数据库中的 API Key）

## 文档

| 文档 | 内容 |
|---|---|
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | 服务器部署、Nginx、systemd、更新与排错 |
| [docs/API.md](docs/API.md) | 全部 HTTP 接口与 SSE 事件协议 |
| [docs/DATABASE.md](docs/DATABASE.md) | SQLite 表结构与字段说明 |
| [docs/deepagents官方参考文档/](docs/deepagents官方参考文档) | deepagents 参考资料 |
| [docs/deepseekAPI参考文档/](docs/deepseekAPI参考文档) | DeepSeek API 参考资料 |

## 贡献

欢迎提交 Issue 与 Pull Request。提交前请：

1. 运行 `uv run --with pytest python -m pytest tests/ -v` 确保测试通过
2. 保持代码注释与日志使用中文（工具 docstring 保持英文）

## 致谢

本项目基于以下开源项目与平台构建：

- [deepagents](https://github.com/langchain-ai/deepagents) / [LangGraph](https://github.com/langchain-ai/langgraph) / [LangChain](https://github.com/langchain-ai/langchain)
- [FastAPI](https://github.com/fastapi/fastapi) / [Vue 3](https://github.com/vuejs/core) / [Vite](https://github.com/vitejs/vite)
- [Chroma](https://github.com/chroma-core/chroma) 向量库
- [DeepSeek](https://www.deepseek.com/) 模型服务与 [博查](https://bochaai.com/) 搜索 API

## License

[MIT](LICENSE)
