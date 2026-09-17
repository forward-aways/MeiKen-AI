# 数据库结构

业务数据使用 SQLite（WAL 模式），文件为项目根目录下的 `chat.db`，首次启动自动创建。

除 `chat.db` 外，运行时还会生成两个由 LangGraph 管理的数据库（不在此文档描述）：

| 文件 | 用途 |
|---|---|
| `checkpoints.db` | 对话检查点（中断恢复、审批续跑） |
| `skills_store.db` | 技能与技能文件存储（LangGraph Store） |

表结构与列迁移集中定义在 `backend/db/_core.py`，通过 `CREATE TABLE IF NOT EXISTS` 与 `ALTER TABLE` 保证幂等，可安全重复启动。

## 表一览

| 表名 | 说明 |
|---|---|
| `users` | 用户账户（资料 / 头像 / 角色） |
| `conversations` | 对话 |
| `messages` | 消息 |
| `knowledge_files` | 知识库文件 |
| `agents` | 智能体配置（含内置） |
| `agent_runs` | 代理运行记录 |
| `approvals` | 人工审批请求与决策 |
| `skills` | 技能（`SKILL.md` 元数据与内容） |
| `skill_overrides` | 用户级技能启停覆盖 |
| `providers` | 模型供应商（API Key 加密存储） |
| `images` | 上传图片（多模态） |

## users

| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| email | TEXT UNIQUE | 登录邮箱 |
| nickname | TEXT | 昵称（可用于登录） |
| password_hash | TEXT | bcrypt 哈希 |
| role | TEXT | `user` / `admin` |
| created_at | TEXT | UTC ISO 时间 |
| real_name / gender / birthday / bio / ai_address | TEXT | 个人资料 |
| avatar / avatar_color | TEXT | 头像（图片或 emoji）与兜底颜色 |

## conversations

| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| user_id | INTEGER FK | 所属用户（`ON DELETE CASCADE`） |
| title | TEXT | 标题 |
| created_at / updated_at | TEXT | UTC ISO 时间 |

## messages

| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| conversation_id | INTEGER FK | 所属对话（`ON DELETE CASCADE`） |
| role | TEXT | `user` / `assistant`（CHECK 约束） |
| content | TEXT | 消息正文（仅最终回答，不含过程文本） |
| created_at | TEXT | UTC ISO 时间 |
| tokens | INTEGER | token 用量 |
| images | TEXT | JSON 数组，图片 ID 列表（旧库自动补列） |

## knowledge_files

| 列 | 类型 | 说明 |
|---|---|---|
| id | TEXT PK | 文件 ID（随机 hex） |
| user_id | INTEGER FK | 所属用户 |
| filename | TEXT | 原始文件名 |
| filepath | TEXT | 磁盘路径（位于 `workspace/{user_id}/uploads/`） |
| chunks | INTEGER | 切分片段数 |
| scope | TEXT | `kb`（知识库）/ `temp`（单次对话附加） |
| created_at | TEXT | UTC ISO 时间 |

## agents

| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| user_id | INTEGER | 归属；`0` 表示内置代理 |
| name / display_name / description | TEXT | 标识与展示信息 |
| system_prompt | TEXT | 系统提示词（英文） |
| tools | TEXT | JSON 数组，工具名列表 |
| model | TEXT | 默认模型名 |
| thinking / reasoning_effort / temperature | INTEGER / TEXT / REAL | 推理配置 |
| is_builtin | INTEGER | `1` 为内置（不可删除） |
| created_at | TEXT | UTC ISO 时间 |

## agent_runs

| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| conv_id / agent_id | INTEGER | 对话与代理 |
| thread_id | TEXT | LangGraph 线程 ID |
| status | TEXT | `running` / `done` / `interrupted` 等 |
| created_at / updated_at | TEXT | UTC ISO 时间 |

## approvals

| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| run_id | INTEGER | 所属运行 |
| action_id | TEXT | 工具调用动作 ID |
| tool | TEXT | 工具名 |
| args | TEXT | JSON 参数 |
| status | TEXT | `pending` / `approved` / `rejected` 等 |
| created_at | TEXT | UTC ISO 时间 |

## skills

| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| user_id | INTEGER | 归属；`0` 表示内置 |
| name / description | TEXT | 技能名与说明（`UNIQUE(user_id, name)`） |
| content | TEXT | `SKILL.md` 正文 |
| meta | TEXT | JSON 元数据（含 `allowed-tools`） |
| enabled | INTEGER | 默认启用状态 |
| source | TEXT | `manual` / `upload` 等 |
| created_at / updated_at | TEXT | UTC ISO 时间 |

## skill_overrides

| 列 | 类型 | 说明 |
|---|---|---|
| user_id | INTEGER | 用户 |
| skill_id | INTEGER | 技能 |
| enabled | INTEGER | 该用户的启用状态（复合主键） |

## providers

| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| user_id | INTEGER | 归属；`0` 表示内置供应商 |
| name | TEXT | 供应商名（`UNIQUE(user_id, name)`） |
| base_url | TEXT | OpenAI 兼容 Base URL |
| api_key_enc | TEXT | Fernet 加密后的 API Key（明文不落库） |
| deepseek_compat | INTEGER | 是否启用 DeepSeek 专有参数 |
| models | TEXT | JSON 数组，模型定义（名称 / 上下文窗口） |
| is_builtin / enabled | INTEGER | 内置标记 / 启用状态 |
| created_at / updated_at | TEXT | UTC ISO 时间 |

> 解密依赖 `config/fernet.key`，该文件丢失将导致库中 Key 无法解密。

## images

| 列 | 类型 | 说明 |
|---|---|---|
| id | TEXT PK | 图片 ID |
| user_id | INTEGER FK | 所属用户 |
| filename | TEXT | 原始文件名 |
| filepath | TEXT | 磁盘路径（`workspace/{user_id}/uploads/`） |
| mime | TEXT | MIME 类型 |
| size | INTEGER | 字节数 |
| created_at | TEXT | UTC ISO 时间 |

## 索引

| 索引 | 目标 |
|---|---|
| `idx_provider_user` | `providers(user_id, enabled)` |
| `idx_image_user` | `images(user_id, created_at)` |
| `idx_msg` | `messages(conversation_id, created_at)` |
| `idx_conv_user` | `conversations(user_id, updated_at)` |
| `idx_kb_user` | `knowledge_files(user_id, scope)` |
| `idx_agent_user` | `agents(user_id)` |
| `idx_run_conv` | `agent_runs(conv_id)` |
| `idx_approval_run` | `approvals(run_id, status)` |
| `idx_skill_user` | `skills(user_id, enabled)` |

## 备份与迁移

需要同时备份以下内容，缺一不可：

| 路径 | 用途 |
|---|---|
| `chat.db`（含 `-wal` / `-shm`） | 业务数据 |
| `checkpoints.db` | 对话检查点 |
| `skills_store.db` | 技能存储 |
| `config/fernet.key` | 解密数据库中的 API Key |
| `workspace/` | 用户上传与 AI 生成文件 |

知识库可重建：还原 `chat.db` 与 `workspace/` 后重新上传文件即可。若一并迁移 `chroma_db/`，需保证目录结构一致。
