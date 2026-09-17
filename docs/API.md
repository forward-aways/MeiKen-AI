# API 参考

- 基础地址：`http://<host>:8000`
- 交互文档：`/docs`（Swagger UI）
- 认证：登录后由服务端下发 httpOnly Cookie（JWT），除注册 / 登录 / 健康检查外均需登录态
- 请求体默认 `application/json`；上传接口使用 `multipart/form-data`

## 认证

前缀 `/api/auth`

| Method | Endpoint | 说明 |
|---|---|---|
| POST | `/register` | 注册（邮箱 + 密码 + 昵称） |
| POST | `/login` | 登录（支持邮箱或昵称） |
| GET | `/me` | 当前用户信息 |
| PUT | `/profile` | 更新个人资料（昵称 / 头像 / 签名等） |
| PUT | `/password` | 修改密码 |
| POST | `/forgot-password` | 发送重置邮件（未配置 SMTP 时重置链接打印到日志） |
| POST | `/reset-password` | 使用令牌重置密码 |
| POST | `/logout` | 退出登录（清除 Cookie） |

## 对话

前缀 `/api`

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `/conversations` | 对话列表 |
| POST | `/conversations` | 新建对话 |
| GET | `/conversations/{id}` | 对话详情（含消息列表） |
| PATCH | `/conversations/{id}` | 重命名 / 置顶 |
| DELETE | `/conversations/{id}` | 删除对话 |
| DELETE | `/conversations/{id}/messages/{mid}` | 删除单条消息 |
| GET | `/search?q=keyword` | 全文搜索消息 |

## 聊天与运行

前缀 `/api`

### 发送消息

```
POST /chat/{conversation_id}
```

请求体（字段均有默认值）：

```json
{
  "message": "帮我分析这份数据",
  "image_ids": [],
  "system_prompt": "",
  "enable_search": true,
  "enable_thinking": true,
  "enable_rag": false,
  "rag_files": [],
  "agent_id": 1,
  "model": "deepseek-flash",
  "thinking": true,
  "reasoning_effort": "high",
  "mode": "general"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `message` | string | 用户输入（≤ 8000 字） |
| `image_ids` | string[] | 已上传图片 ID（多模态，最多 4 张） |
| `system_prompt` | string | 本次会话临时系统提示词 |
| `enable_search` | bool | 启用联网搜索工具 |
| `enable_thinking` | bool | 启用思考模式 |
| `enable_rag` | bool | 启用知识库检索 |
| `rag_files` | string[] | 限定检索的知识库文件 ID |
| `agent_id` | int \| null | 使用的代理 |
| `model` | string \| null | 本次会话模型覆盖 |
| `thinking` | bool \| null | 本次会话思考开关覆盖 |
| `reasoning_effort` | string \| null | 推理强度：`low` / `high` / `max` |
| `mode` | string | 人格模式：`code` / `work` / `general` |

响应为 SSE 流（`text/event-stream`），每条事件形如 `data: <json>`，字段如下：

| 事件 | 说明 |
|---|---|
| `{"type":"token","token":"..."}` | 回答内容（流式累加） |
| `{"type":"reasoning","reasoning":"..."}` | 思考链增量 |
| `{"type":"todo","todos":[...]}` | 计划清单快照 |
| `{"type":"tool_call","id":"...","tool":"...","args":{}}` | 工具调用开始 |
| `{"type":"tool_result","id":"...","tool":"...","result":"...","sources":[...]}` | 工具结果（`sources` 为结构化来源） |
| `{"status":"sub_started","subagent":"...","task":"..."}` | 子代理开始 |
| `{"status":"sub_done","subagent":"..."}` | 子代理完成 |
| `{"type":"approval_request","action_id":"...","tool":"...","args":{},"allowed":[...]}` | 等待人工审批 |
| `{"status":"run_end","interrupted":false,"run_id":"...","tokens":123,"final_text":"..."}` | 运行结束（正文以 `final_text` 为准） |
| `{"error":"..."}` | 异常信息 |
| `{"done":true,"id":123,"tokens":123}` | 回答已入库并结束（中断时不下发） |

> 多数事件带 `agent` 字段，标识事件来源是主代理还是子代理。

### 运行控制

| Method | Endpoint | 说明 |
|---|---|---|
| POST | `/approvals/{action_id}` | 审批工具调用：`decision` 取 `approve` / `reject` / `edit`，可附 `edited_args` 与 `message` |
| POST | `/runs/{run_id}/stop` | 停止运行 |

## 智能体

前缀 `/api/agents`

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `` | 代理列表 |
| POST | `` | 创建代理 |
| PATCH | `/{id}` | 更新代理（名称 / 提示词 / 工具 / 模型等） |
| DELETE | `/{id}` | 删除代理（内置不可删） |

## 技能

前缀 `/api/skills`

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `` | 技能列表 |
| GET | `/{id}` | 技能详情 |
| POST | `` | 创建技能 |
| POST | `/upload` | 上传 `SKILL.md` |
| PATCH | `/{id}` | 更新 / 启停技能 |
| DELETE | `/{id}` | 删除技能 |

## 知识库

前缀 `/api/kb`

| Method | Endpoint | 说明 |
|---|---|---|
| POST | `/upload` | 上传文档（自动解析 + 切分 + 向量化） |
| GET | `/files` | 知识库文件列表 |
| DELETE | `/files/{id}` | 删除文件（同时清理向量数据） |

支持的格式：`.pdf` `.docx` `.xlsx` `.xlsm` `.xls` `.pptx` `.csv` `.tsv` `.html` `.htm` `.txt` `.md` 及常见代码 / 配置文件扩展名。

## 用户文件

前缀 `/api/files`

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `?scope=all\|uploads\|generated\|exports` | 工作区文件列表（相对路径 / 大小 / 修改时间） |
| GET | `/read?path=<rel>` | 预览：文本类返回原文，文档类由解析器转为 Markdown |
| GET | `/download?path=<rel>` | 下载文件（保留原文件名） |

`path` 为工作区内相对路径（如 `uploads/ab12cd34ef56.pdf`），服务端会做目录穿越校验。

## 图片

前缀 `/api/images`

| Method | Endpoint | 说明 |
|---|---|---|
| POST | `` | 上传图片（多模态消息使用），返回图片 ID |
| GET | `/{id}` | 获取图片内容（需登录，按用户鉴权） |

## 模型供应商

前缀 `/api/providers`

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `` | 供应商列表（API Key 仅返回是否已配置） |
| POST | `` | 添加供应商（名称 / Base URL / Key / 模型列表） |
| PATCH | `/{id}` | 更新供应商（Key / 模型 / 启停） |
| DELETE | `/{id}` | 删除供应商（内置不可删） |
| POST | `/{id}/test` | 连接测试 |

## 其他

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
