<div align="center">

# MeiKen AI Harness

A self-hostable multi-agent AI workstation: deepagents orchestration, multi-provider models, web search, private knowledge base, skills, and multimodal input.

<img src="https://img.shields.io/badge/Python-3.13-5b57d2?logo=python" alt="Python">
<img src="https://img.shields.io/badge/Vue-3.x-5b57d2?logo=vuedotjs" alt="Vue">
<img src="https://img.shields.io/badge/FastAPI-0.139-5b57d2?logo=fastapi" alt="FastAPI">
<img src="https://img.shields.io/badge/version-2.0.0-5b57d2" alt="Version">
<img src="https://img.shields.io/badge/license-MIT-5b57d2" alt="License">

[中文](README.md) · **English** · [Deployment](docs/DEPLOYMENT.md) · [API](docs/API.md)

</div>

---

## Overview

MeiKen AI Harness is a self-hostable multi-agent chat platform. The backend orchestrates multi-agent workflows with [deepagents](https://github.com/langchain-ai/deepagents) (LangGraph), and the frontend provides a liquid-glass style interface.

It treats "agent orchestration" and "deployability" as equally important: it runs locally for development, or directly on a server (the backend also serves the built frontend), and never ships with personal API keys — each user configures their own model provider in the UI.

- Quick start: see [Getting Started](#getting-started)
- Server deployment: see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- API details: see [docs/API.md](docs/API.md), or `/docs` at runtime

## Features

### Multi-agent engine
- 5 built-in agents: General Assistant / Researcher / Coder / Data Analyst / Writer
- Subagent delegation: the coordinator dispatches isolated subtasks via the `task` tool
- Execution timeline: tool calls, subagents, and plans are shown on a timeline with expandable details
- Todo list: live progress through the `write_todos` tool
- Human-in-the-loop: sensitive tool calls can be approved / rejected / edited
- Three persona modes: General / Coding / Office

### Models and multimodality
- Multiple providers: built-in DeepSeek plus any OpenAI-compatible endpoint (custom Base URL, model list, context window)
- API keys encrypted at rest with Fernet, isolated per user, never stored in plaintext
- One-click connection test, enable / disable, and switching via the model capsule menu
- Paste / drag / preview images; multimodal models read them directly, others fall back to text
- Three thinking levels (fast / standard / deep) with separate reasoning effort, collapsible chain-of-thought

### Knowledge base and skills
- Knowledge base (RAG): PDF / Word / Excel / PowerPoint / CSV / HTML / Markdown / plain text, with vector retrieval and source attribution
- Per-user file workspace: uploads and AI-generated files are stored per user, with list / preview / download
- Skills: `SKILL.md` format, create / upload / edit / toggle, stored per user and loaded on demand

### UX and engineering
- Liquid-glass / acrylic materials, light and dark themes, bilingual UI (Chinese / English)
- SSE streaming with smart scrolling (stays put while reading history, snaps back when done)
- Pin / rename / export Markdown / full-text search, delete and regenerate messages
- Sign up / sign in (email or nickname), JWT + httpOnly cookie, avatars, profile, password reset
- Unified logging (colored console + daily rotating files) with request tracing via `X-Request-Id`

## Tech Stack

| Category | Choice |
|:---:|---|
| Backend | FastAPI (ASGI) |
| Agent engine | deepagents + LangGraph + LangChain |
| Default model | DeepSeek V4.1 Flash (OpenAI-compatible) |
| Providers | Any OpenAI-compatible endpoint |
| Secret encryption | cryptography (Fernet) |
| Web search | Bocha Search API |
| Knowledge base | Chroma + vector retrieval |
| Database | SQLite (WAL mode) |
| Auth | bcrypt + JWT |
| Frontend | Vue 3 + Vite |
| Syntax highlighting | highlight.js |
| Package managers | uv + npm |

## Getting Started

### Requirements

| Dependency | Version | Notes |
|:---:|:---:|---|
| uv | latest | Manages the Python version and virtualenv ([install guide](https://docs.astral.sh/uv/getting-started/installation/)) |
| Node.js | >= 18 | Only needed to build the frontend |

### Install

```bash
git clone https://github.com/forward-aways/MeiKen-AI.git
cd MeiKen-AI

# Backend (uv downloads Python 3.13 and creates the virtualenv)
uv python install 3.13
uv sync

# Frontend
cd frontend && npm install && cd ..
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` as needed. In production, change at least `JWT_SECRET` and `ADMIN_PASSWORD`. `DEEPSEEK_API_KEY` and `BOCHA_API_KEY` may be left empty and configured in the UI after signing in.

### Run

```bash
# Backend: http://127.0.0.1:8000
uv run python main.py backend

# Frontend (dev mode with HMR): http://127.0.0.1:3000
uv run python main.py frontend
```

`main.py frontend` builds `frontend/dist` automatically if missing, then serves it statically. For production, prefer `npm run build` and let the backend serve the build output.

API docs: `http://127.0.0.1:8000/docs`.

### Default administrator

On first start with an empty database, an administrator account is created:

| Field | Value |
|---|---|
| Email | `admin@meiken.ai` |
| Password | `ADMIN_PASSWORD` from `.env` (default `admin123`) |

> Change `ADMIN_PASSWORD` in production and let other users register their own accounts instead of sharing the admin account.

### Configure a model

Click a model capsule → "Manage models":

1. The built-in DeepSeek provider already exists; enter your own API key to use it
2. You can also add any OpenAI-compatible provider (custom Base URL, model list, context window)
3. API keys are encrypted and stored in the local database, never sent to third parties

## Project Structure

<details>
<summary>Expand the directory layout</summary>

```
MeiKen-AI/
├── main.py                      # Launcher (backend / frontend)
├── pyproject.toml               # Python dependencies (uv)
├── .env.example                 # Environment template
├── LICENSE
├── README.md / README.en.md
│
├── backend/
│   ├── main.py                  # App assembly (middleware / routers / lifespan / static hosting)
│   ├── config.py                # Central config (env vars / paths / defaults)
│   ├── middleware.py            # Request context middleware (X-Request-Id / user context)
│   ├── runtime.py               # Runtime singletons (agent factory / checkpointer / concurrency gate)
│   ├── log.py                   # Logging (colored console + daily rotation)
│   ├── auth.py                  # JWT auth / password hashing / password reset
│   ├── crypto.py                # Fernet encryption for API keys
│   ├── schemas.py               # Pydantic request / response models
│   ├── skills.py                # SKILL.md validation and parsing
│   ├── rag.py                   # Knowledge base: split / embed / retrieve
│   ├── workspace.py             # Per-user file workspace (path safety / legacy migration)
│   ├── db/                      # Data access layer (split by domain)
│   │   ├── _core.py             # Connections / schema / column migrations
│   │   └── users / convs / agents / providers / skills / kb / images
│   ├── routes/                  # HTTP routes
│   │   └── auth / convs / chat / agents / skills / kb / providers / images / files / misc
│   ├── services/
│   │   └── chat_stream.py       # SSE orchestration (shared by chat and approvals)
│   ├── documents/               # Multi-format document parsing
│   │   └── parsers/             # text / csv / pdf / docx / xlsx / pptx / html + registry
│   └── agent/                   # Multi-agent engine (deepagents)
│       ├── bridge.py            # Streaming event bridge (SSE event protocol)
│       ├── factory.py           # Agent factory / cache / approval interrupts / filesystem backend
│       ├── identity.py          # Persona and modes (general / code / work)
│       ├── llm.py               # Provider resolution + model construction
│       ├── registry.py          # Built-in agents and subagents
│       └── tools.py             # Tools (web search / knowledge base)
│
├── tests/                       # Backend tests (pytest)
│   ├── test_smoke.py            # Core API smoke tests
│   ├── test_documents.py        # Document parsing tests
│   └── test_files.py            # File workspace tests
│
├── frontend/
│   ├── package.json             # npm dependencies
│   ├── vite.config.js           # Vite config (dev /api proxy)
│   └── src/
│       ├── App.vue              # Root component + SSE handling
│       ├── store.js / api.js / i18n.js / md.js / logger.js / experts.js
│       ├── assets/main.css      # Glass material system / global animations
│       └── components/          # Pages and components (~20)
│
├── nginx/
│   └── meikenai.conf            # Nginx reverse proxy example
│
└── docs/                        # Documentation
    ├── DEPLOYMENT.md            # Deployment guide
    ├── API.md                   # API reference
    ├── DATABASE.md              # Database schema
    ├── deepagents官方参考文档/    # deepagents reference (Chinese)
    └── deepseekAPI参考文档/       # DeepSeek API reference (Chinese)
```

</details>

## Tests

```bash
uv run --with pytest python -m pytest tests/ -v
```

> Tests that touch the knowledge base download a ~79MB embedding model on first run; the time depends on your network.
> On Windows, if you hit a temp-directory permission error, append `--basetemp=%TEMP%\pytest-tmp -p no:cacheprovider`.

## Deployment

Production shape: Nginx reverse proxy → FastAPI (the backend also serves the built frontend).

```bash
# 1. Install dependencies
uv sync
cd frontend && npm install && npm run build && cd ..

# 2. Configure environment (change at least JWT_SECRET / ADMIN_PASSWORD)
cp .env.example .env && vi .env

# 3. Start
uv run python main.py backend
```

Full server instructions (prerequisites, systemd, Nginx, upgrades, troubleshooting) are in **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

**Server security notes**

- Start from a fresh database; do not copy your local `chat.db`
- Do not set `DEEPSEEK_API_KEY` in `.env`; let users configure it after signing in
- Do not copy `config/fernet.key` (it decrypts API keys stored in the database)

## Documentation

| Document | Contents |
|---|---|
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Server deployment, Nginx, systemd, upgrades, troubleshooting |
| [docs/API.md](docs/API.md) | All HTTP endpoints and the SSE event protocol |
| [docs/DATABASE.md](docs/DATABASE.md) | SQLite schema and fields |
| [docs/deepagents官方参考文档/](docs/deepagents官方参考文档) | deepagents reference (Chinese) |
| [docs/deepseekAPI参考文档/](docs/deepseekAPI参考文档) | DeepSeek API reference (Chinese) |

## Contributing

Issues and pull requests are welcome. Before submitting:

1. Run `uv run --with pytest python -m pytest tests/ -v` and make sure tests pass
2. Keep code comments and logs in Chinese (tool docstrings stay English, as they are model prompts)

## Acknowledgements

Built on the following open-source projects and platforms:

- [deepagents](https://github.com/langchain-ai/deepagents) / [LangGraph](https://github.com/langchain-ai/langgraph) / [LangChain](https://github.com/langchain-ai/langchain)
- [FastAPI](https://github.com/fastapi/fastapi) / [Vue 3](https://github.com/vuejs/core) / [Vite](https://github.com/vitejs/vite)
- [Chroma](https://github.com/chroma-core/chroma) vector store
- [DeepSeek](https://www.deepseek.com/) model service and [Bocha](https://bochaai.com/) search API

## License

[MIT](LICENSE)
