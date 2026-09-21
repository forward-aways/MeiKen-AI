# ADR-20260921：对话渲染与 SSE 状态机修复

- 状态：待评审（Phase 2.5 已完成，等待 CHECKPOINT）
- 日期：2026-09-21
- 影响面：`frontend/src/App.vue`、新增 `frontend/src/sse.js`、`frontend/src/components/ActivityPanel.vue`、`frontend/src/components/ChatMessage.vue`、`backend/agent/bridge.py`、`frontend/src/assets/main.css`

---

## 1. 背景与问题陈述

多智能体版本（commit `361fcf7`）同时做了两件互相耦合的改动：

1. 后端把对话引擎从自研实现替换为 deepagents 桥接（新增 `backend/agent/bridge.py`），**丢弃了旧引擎的部分 SSE 事件**。
2. 前端新增 `AgentRun.vue`（执行时间线）与 `ActivityPanel.vue`（右侧活动面板），并重写 `App.vue`（+263 行）。

前端在此期间**没有同步更新事件消费逻辑**，且新组件以“追加循环”的方式接入消息列表，导致一系列渲染与状态错乱。用户反馈的四个症状都指向这组改动。

---

## 2. 症状

| 编号 | 用户描述 | 观察到的现象 |
|---|---|---|
| S1 | 输入与 AI 回复位置混乱 | 消息气泡顺序正确，但工具时间线被整体挪到列表末尾 |
| S2 | AI 回复没有弹出新卡片，一直在原来的卡片生成 | 新回复的气泡为空，活动出现在页面底部旧时间线之后 |
| S3 | 思考结束还显示“思考中” | 思考折叠条长期显示“思考中”且带高光动画 |
| S4 | 右侧面板一会弹出一会消失，与顶部栏重叠 | 面板按消息流启停，面板顶部 52px 被固定顶栏遮住 |

---

## 3. 证据（代码位置）

| 证据 | 位置 |
|---|---|
| 两段并列 `v-for`：先渲染全部 `ChatMessage`，再渲染全部 `AgentRun` | `frontend/src/App.vue:520-532` |
| 通用 `if (ev.tokens)` 位于 `run_end` 分支之前 | `frontend/src/App.vue:74` vs `:122` |
| 前端消费 `thinking_done` / `searching` / `searched` / `rag_loaded` | `frontend/src/App.vue:73-77` |
| 后端 bridge 事件清单**不含**上述事件 | `backend/agent/bridge.py:6-16`（协议注释）与 `:62-205`（实现） |
| `run_end` 载荷包含 `tokens` 字段 | `backend/agent/bridge.py:203-205` |
| 终止事件 `done` 载荷也包含 `tokens` | `backend/services/chat_stream.py:37` |
| 面板在 `.shell-body` 内无顶部偏移；`.sidebar`/`.main` 均为 `padding-top:52px` | `frontend/src/assets/main.css:135-146` vs `ActivityPanel.vue:88` |
| 面板可见性依赖“最后一条 assistant 消息的 `streaming`” | `frontend/src/components/ActivityPanel.vue:7-15` |
| 审批 UI 在面板与时间线中重复 | `ActivityPanel.vue:65-81` 与 `AgentRun.vue:241-257` |
| 消息以数组下标为 key | `frontend/src/App.vue:522,530` |
| 引入时间点（同一次提交同时引入 bridge 与两个新组件） | `git log -S "run-' + convKey" → 361fcf7` |

---

## 4. 根因分析

### 4.1 因果链（全局）

```
引擎迁移（自研 → deepagents bridge）
   ├── 丢失 thinking_done / searching / searched / rag_loaded 事件
   │        └── RC3：协议漂移（前端消费不存在的事件）
   └── 新增 AgentRun / ActivityPanel
            ├── 以“并列第二个 v-for”接入 → RC1：时间线与消息脱离
            └── 面板无顶部偏移 + 以 streaming 启发式启停 → RC4：重叠 + 抖动

App.vue 事件分发改为重写，引入字段级鸭子类型判断
   └── if (ev.tokens) 先于 run_end 分支 → RC2：run_end 被吞
```

### 4.2 根因分层表

**RC1 —— 时间线整体脱离消息列表**

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | 工具时间线全部堆在对话末尾 | 实际渲染顺序 `[u1][a1][u2][a2] … [trace(a1)][trace(a2)]` |
| 直接原因 | 两个独立 `v-for` 都遍历 `msgs`，第二个把全部 `AgentRun` 追加到末尾 | `App.vue:520-532` |
| 根因 | **“一条消息 = 气泡 + 时间线”这一整体被拆成两个并列列表**，破坏消息与其附属信息的从属关系 | `AgentRun` 未被纳入消息循环 |

**RC2 —— `run_end` 事件被通用分支吞掉**

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | 最终答案未被 `final_text` 覆盖；`phase` 不清空；上下文计量不增长 | `addContextTokens` 从不执行 |
| 直接原因 | `run_end` 载荷含 `tokens`，在到达 `:122` 分支前被 `:74` 的 `if (ev.tokens)` 命中并 `return true` | `bridge.py:203-205` + `App.vue:74` |
| 根因 | **事件分发依赖“字段是否存在”的鸭子类型，而非显式判别符**；`tokens` 字段被多个事件类型共用，判别不唯一 | `run_end`/`done` 均含 `tokens` |
| 放大因素 | `tokens_box["tokens"]` 仅在有 `usage_metadata` 时非 0，故 **行为随 token 是否上报而漂移**（有时正常、有时异常） | `bridge.py:78-80` |

**RC3 —— SSE 协议漂移**

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | “思考结束还显示思考中”；搜索状态条永不出现 | `thinkingTime` 恒为 `undefined` |
| 直接原因 | 前端等待 `thinking_done` 来写入 `thinkingTime`，后端从不发送 | `App.vue:73`；后端 grep 无 `thinking_done` |
| 根因 | **引擎迁移时未把 SSE 事件契约作为显式接口维护**：生产者与消费者各自演化，缺少契约文档与契约测试 | `bridge.py:6-16` 仅注释、无校验 |
| 放大因素 | 旧引擎确有事件；迁移后成为死代码，却仍驱动 UI 状态判定 | `git log -S "thinking_done" → e32ee07`（初版） |

**RC4 —— 右侧面板重叠与抖动**

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | 面板顶部被顶栏遮挡；运行期间反复出现/消失 | 面板顶部内容位于顶栏之后 |
| 直接原因 A | `.activity-panel` 无 `padding-top:52px`，在 `.shell-body` 中从 y=0 起排 | `main.css:135-146`、`ActivityPanel.vue:88` |
| 直接原因 B | 可见性 = `最后一条 assistant 消息的 streaming || todos || toolCalls …`；`streaming` 仅在一次请求期间为真 | `ActivityPanel.vue:7-15` |
| 根因 | **把“是否有运行中活动”绑定到可变的“最后一条消息对象”，而非运行生命周期**；且面板增删改变 flex 宽度导致 `.main` 回流 | 无稳定运行态信号 |
| 次要问题 | 审批 UI 在面板与时间线重复渲染，二者状态可能不一致 | 两处独立渲染 approval |

### 4.3 泛化判断

| 问题 | 一次性 / 一类 | 代表输入 | 反例 | 非适用场景 |
|---|---|---|---|---|
| RC1 | 一类：任何“消息 + 附属视图”拆分渲染 | 多轮工具对话 | 单条消息 | 无附属视图的消息 |
| RC2 | 一类：事件载荷字段重叠时按字段分发 | `run_end{tokens>0}` | `token`（无 tokens 字段） | 字段互不重叠的事件 |
| RC3 | 一类：生产者/消费者协议无契约 | 引擎替换、事件增删 | 事件集稳定时 | 单进程内直连调用 |
| RC4 | 一类：浮动/侧栏与固定顶栏的层叠 | 新增右侧栏 | 无固定顶栏布局 | 面板固定定位时 |

### 4.4 快速补丁 vs 结构化修复

| 方案 | 解决根因 | 防复发 | 泛化性 | 长期成本 |
|---|---|---|---|---|
| 补丁：把 `if (ev.tokens)` 移到 `run_end` 之后 | 仅 RC2 部分 | 无（新增含 `tokens` 的事件会再次踩坑） | 低 | 高（每次加事件都要重审顺序） |
| 补丁：`AgentRun` 前加 `<div>` 手动插入 | 仅 RC1 表象 | 无 | 低 | 中 |
| 结构化：显式判别符分发 + 单一消息循环 + 契约化事件 + 稳定运行态 | RC1–RC4 | 契约测试 / 判别唯一性 / 单元测试 | 高 | 低 |

---

## 5. 泛化边界与反例

- **适用范围**：浏览器端 SSE 消费 + Vue 列表渲染；服务端 bridge 事件生产。
- **不变量（Invariant）**：
  - I1：每个 SSE 事件**恰好**有一个判别符：`status` 或 `type`（终态 `done` / 错误 `error` 除外）。
  - I2：`run_end` 对每个 run **恰好应用一次**，且必须清空 `phase` 并写回 `final_text`。
  - I3：一条消息的附属视图（时间线/审批/过程记录）必须与气泡**同属一个渲染单元**。
  - I4：右侧面板的可见性由**运行生命周期**决定，与“消息列表长度/末条对象身份”无关。
- **反例（当前实现会失败的输入）**：
  - `run_end` 中 `tokens > 0` → RC2 触发（`tokens = 0` 时反而正常）。
  - 连续两条都带工具调用的 assistant 消息 → RC1 呈现为两条时间线堆叠在末尾。
  - 仅思考、无工具、无后续 token 的回复 → RC3 表现为“永久思考中”。
- **非适用场景**：
  - 非流式（一次性返回）对话无需 `thinking_done` 时间线语义。
  - 移动端（≤1024px）面板本就 `display:none`，RC4 不适用。

---

## 6. 设计方案

### 6.1 单一事实源：SSE 事件契约

在 `docs/`（或 `backend/agent/bridge.py` 顶部注释）冻结契约，并作为前后端共同规范：

| 判别符 | 事件 | 载荷 | 前端动作 |
|---|---|---|---|
| `status` | `run_end` | `interrupted, run_id, tokens, final_text` | 写回 `final_text`、清 `phase`、计上下文、结束运行态 |
| `status` | `sub_started` | `subagent, task` | 追加子代理步骤 |
| `status` | `sub_done` | `subagent` | 标记子代理完成 |
| `type` | `token` | `token` | 追加正文 |
| `type` | `reasoning` | `reasoning` | 追加思考 |
| `type` | `thinking_done` | `seconds`（**新增，后端补发**） | 记录思考耗时，结束思考态 |
| `type` | `todo` | `todos` | 覆盖计划清单 |
| `type` | `tool_call` | `id, tool, args` | 追加时间线步骤 |
| `type` | `tool_result` | `id, tool, result, sources?` | 按 `id` 配对并完成 |
| `type` | `approval_request` | `action_id, tool, args, allowed` | 追加审批 |
| （终态） | `done` | `id, tokens` | 标记已入库 |
| （终态） | `error` | `error` | 展示错误 |

**淘汰**：`searching` / `searched` / `rag_loaded`——deepagents 桥接已用 `tool_call`/`tool_result` 统一表达（时间线中的“正在调用 联网搜索”“N 个网页”），继续保留会造成第二套并行真源。

### 6.2 前端事件分发器（提取为纯函数，可单测）

新增 `frontend/src/sse.js`：

```js
// 判别优先级：status 判别符 > type 判别符 > 终态 done > error
export function applyEvent(ast, ev, hooks = {}) {
  // 1) 显式 status 判别符
  if (ev.status) return applyStatus(ast, ev, hooks)
  // 2) 显式 type 判别符
  if (ev.type) return applyType(ast, ev, hooks)
  // 3) 终态
  if (ev.done) return applyDone(ast, ev, hooks)
  if (ev.error) return applyError(ast, ev, hooks)
  hooks.onUnknown?.(ev)   // 未知事件不静默
  return false
}
```

- **不变量 I1** 在此强制：判别符唯一，禁止任何 `ev.tokens` 之类的字段级判断。
- `run_end` 的处理**只**存在于 `applyStatus`，`tokens` 仅在此处与 `applyDone` 读取。
- 未知事件通过 `onUnknown` 记录（可接 `logger.js`），作为协议漂移的早期告警。

### 6.3 后端补发 `thinking_done`（修复 S3 的根因，而非前端猜测）

在 `bridge.py` 内新增思考计时状态（随 `tokens_box` 传递，避免新增并行状态对象）：

```
tokens_box = { tokens: 0, think_t0: null, think_closed: true }
```

- 收到首个 `reasoning` 且 `think_t0 == null` → `think_t0 = perf_counter()`，`think_closed = false`
- 收到首个正文 `token`、或发出 `tool_call`/`sub_started`、或即将发出 `run_end` 时：
  - 若 `!think_closed` → 先产出 `{"type":"thinking_done","seconds": round(perf_counter()-think_t0, 1)}`，置 `think_closed = true`
- 无思考的 run 不发该事件（前端 `thinkingTime` 保持空，思考条不出现）

**契约**：`thinking_done` 先于触发它的 `token`/`tool_call` 产出，保证前端先结束思考态再进入生成态。

### 6.4 消息与时间线合并渲染（修复 S1/S2）

`App.vue` 模板改为单一循环，把气泡与附属视图绑定为同一渲染单元：

```html
<template v-for="(m, i) in msgs" :key="msgKey(m, i)">
  <ChatMessage :message="m" :index="i" ... />
  <AgentRun v-if="m.role === 'assistant'" :msg="m" @approve="handleApproval" />
</template>
```

- 渲染顺序变为 `[u1][a1+trace(a1)][u2][a2+trace(a2)]`。
- `msgKey(m, i)`：持久化消息用 `'m' + m.id`，流式临时消息用 `'n' + convKey + '-' + i`——避免下标 key 在 `retry/regenerate` splice 后复用组件实例（修正编辑态/折叠态串到别的消息）。

### 6.5 右侧活动面板（RC4）

采用**生命周期驱动**的可见性，替代“末条消息启发式”：

```
visible = busy (存在进行中的 run)  ||  lastAssistant.pendingApprovalPending
```

- 运行期间稳定可见（不随消息对象变化抖动）；审批等待期间保持；结束后隐藏。
- 布局：`.activity-panel { padding-top: 52px }`（移动端 `display:none` 不变），消除与固定顶栏重叠；并加 `z-index` 明确层叠。
- **去重**：审批 UI 只保留在消息时间线（上下文就近），面板改为只读进度展示——消除两套审批状态不一致的风险。
- 由于 `busy` 在整轮 run 内恒为真，面板不再“一会弹出一会消失”。

### 6.6 淘汰死代码

`App.vue` 移除 `searchingQuery` / `searching-bar` / `searchResults` / `ragSources` 等无生产者字段与对应模板，避免“第二真源”。

---

## 7. 数据结构与 API 契约

```python
# backend/agent/bridge.py —— 思考计时状态（随 tokens_box 复用）
tokens_box: dict = {
    "tokens": int,          # token 累计
    "turn_text": str,       # 本回合正文（既有）
    "think_t0": float|None, # 首次 reasoning 的时间戳（新增）
    "think_closed": bool,   # 是否已发出 thinking_done（新增）
}
```

```js
// frontend/src/sse.js
/**
 * @param {object} ast    流式 assistant 消息（reactive）
 * @param {object} ev     SSE 事件 JSON
 * @param {object} hooks  { onUnknown?, addContextTokens? }
 * @returns {boolean}     是否产生了状态变更（用于触发滚动）
 */
export function applyEvent(ast, ev, hooks)
```

- 异常：`applyEvent` 不抛异常；未知事件交 `hooks.onUnknown`。
- `run_end` 后置条件：`ast.content === ev.final_text`（当 `final_text` 为字符串）、`ast.phase === ''`、`ast.interrupted === ev.interrupted`、上下文计量 +`ev.tokens`（且仅此处累加，`done` 不重复累加）。

---

## 8. 复杂度

| 操作 | 时间 | 空间 |
|---|---|---|
| `applyEvent` 单次分发 | O(1)（事件数固定） | O(1) |
| 每条消息渲染 | O(1)，合计 O(n)，n = 消息数 | O(n) |
| AgentRun `steps` 归并（既有） | O(k)，k = 该消息步骤数 | O(k) |
| 思考计时 | O(1) | O(1) |

无嵌套规模增长；不引入额外后端状态。

---

## 9. 备选方案与取舍

| 决策点 | 方案 A（推荐） | 方案 B | 取舍 |
|---|---|---|---|
| 思考结束信号 | 后端补发 `thinking_done`（含秒数） | 前端在首个 token 时自行结算 | A 保持既有 UI 契约与“思考了 N 秒”语义；B 使 producer/consumer 职责错位 |
| 活动面板 | 保留，改为 `busy` 驱动 + 去重 | 直接删除，统一用消息内时间线 | A 保留快速总览；B 更简但损失功能。**交用户决定** |
| 分发方式 | 显式判别符表 | 逐字段 `if` 并调整顺序 | 表结构消除字段碰撞类问题；逐字段仍会在新增事件时复发 |
| 前端回归测试 | 引入 Vitest 单测 `sse.js` | 仅手工验证 | Vitest 是防复发的关键；**需用户同意新增 devDependency** |

---

## 10. 防复发机制

1. **契约测试（前端）**：`sse.test.js` 断言 `run_end`（含 `tokens>0`）必须写回 `final_text`、清 `phase`——该用例在修复前失败。
2. **契约测试（后端）**：`tests/test_bridge_events.py` 用假 chunk 调用 `_handle_message_chunk`，断言 `reasoning → token` 序列产出 `thinking_done`；断言 `run_end` 载荷字段稳定。
3. **判别唯一性**：`applyEvent` 对未知事件记录告警，协议漂移立即暴露。
4. **渲染不变量**：消息循环内气泡与时间线同单元，模板层直接体现 I3。
5. **文档**：将 SSE 契约表写入 `docs/API.md` 并链接至 ADR。
6. **单元测试约束**：`thinking_done` 只在确有思考时产出（避免空事件）。

---

## 11. 测试计划

| ID | 类型 | 输入 / 场景 | 期望 | 覆盖根因 | 覆盖防复发 |
|---|---|---|---|---|---|
| T1 | Happy | `reasoning` → `token` → `run_end{tokens:120,final_text:"A"}` | `content==="A"`、`phase===""`、上下文 +120、`thinkingTime` 有值 | RC2/RC3 | 是 |
| T2 | 边界 | `run_end{tokens:0,final_text:"B"}` | 仍写回 `"B"`、清 `phase`（tokens=0 也必须处理） | RC2 | 是 |
| T3 | 回归 | 仅 `run_end{"tokens":120}` 无 `final_text` | 不崩溃、不改 `content` | RC2 | 是 |
| T4 | 错误 | `{"error":"boom"}` | `ast.error=true`、`phase=""` | RC2 | 否 |
| T5 | 配对 | 两次同名 `tool_call`（不同 id）+ 乱序 `tool_result` | 按 `id` 正确配对 | RC1 | 是 |
| T6 | 泛化 | 3 条消息（2 条含工具） | 渲染顺序 `a1+trace1, a2+trace2, a3+trace3`，无末尾堆叠 | RC1 | 是 |
| T7 | 边界 | 无思考的 run | 不产出 `thinking_done`，思考条不出现 | RC3 | 是 |
| T8 | 手工/集成 | 运行中观察面板；审批等待 | 面板稳定可见、无重叠、审批仅一处 | RC4 | 是 |

---

## 12. 决策（Checkpoint，2026-09-21 用户确认）

1. **活动面板**：**A 保留并修复**——`busy`/运行生命周期驱动 + 顶部偏移 + 审批去重（审批只留消息时间线）。
2. **前端测试依赖**：**同意新增 `vitest`**（devDependency），落地 T1–T7 自动化回归。
3. **淘汰死事件**：**确认移除** `searching/searched/rag_loaded` 及其 UI，搜索状态由 `AgentRun` 时间线承载。
4. **思考耗时**：**保留**“思考了 N 秒”，由后端 `thinking_done.seconds` 提供。

> 用户已确认，进入 Phase 3 实现。

## 13. 实现结果（Phase 3/4 完成后回填）

### 落地内容

| 文件 | 改动 |
|---|---|
| `backend/agent/bridge.py` | 新增 `_thinking_done_event()` 与思考计时状态（`think_t0` / `think_closed`）；在首个正文、首个 `tool_call`/`sub_started`、`run_end` 前结算 `thinking_done{seconds}`；协议注释补充契约不变量 |
| `frontend/src/sse.js` | **新增**：纯函数事件分发器（`applyEvent` / `splitInterim`），按判别符分派，未知事件走 `onUnknown` |
| `frontend/src/App.vue` | 删除本地 `applyEvent` 与死事件消费；改为导入共享分发器并传 `hooks`；消息与时间线合并为单一 `v-for`；新增稳定 `msgKey()`；移除 `searching-bar`；审批流程补 `busy` 闸门与 `AbortController` |
| `frontend/src/components/ActivityPanel.vue` | 可见性改为生命周期驱动（`busy`/`streaming`/`pendingApproval`/`hasActivity`）；`padding-top:52px` 消除顶栏重叠；常驻挂载 + 宽度过渡消除回流抖动；审批改为只读提示（去重） |
| `frontend/src/components/ChatMessage.vue` | 未改动（`isThinking` 判定因 `thinking_done` 恢复产出而自然正确） |
| `frontend/src/i18n.js` | 新增 `approvalInTimeline`；移除无生产者的 `searching` |
| `frontend/src/__tests__/sse.test.js` | **新增**：14 个契约/回归/边界用例 |
| `tests/test_bridge_events.py` | **新增**：6 个后端事件契约用例 |
| `frontend/package.json` | 新增 `vitest` devDependency 与 `npm test` |
| `docs/API.md` | 追加「事件契约（不变量）」小节 |

### 验证证据

| 验证 | 结果 |
|---|---|
| 前端契约测试 | `14 passed`（含 T1–T7） |
| 后端契约测试 | `6 passed` |
| 后端全量（bridge + documents + smoke） | `24 passed` |
| 前端生产构建 | `built in 5.30s`，无错误 |
| **回归有效性证明** | 以旧实现执行 `run_end{tokens:120}` → `content` 保持 `""`、`final_text` **未被写回**；新实现断言通过 → 回归测试确实捕获 RC2 |
| 死代码检查 | `App.vue` 无 `searchingQuery` / `searching-bar` / 本地 `applyEvent` 残留 |

### 与设计的偏差

1. **`thinking_done` 语义收紧为「每个 run 至多一次」**（非「每个思考回合」）。
   原因：`ChatMessage` 的 `isThinking` 在 `thinkingTime` 一旦有值即为 `false`，
   若多次产出会让后续思考回合不再进入思考态，反而削弱 UX。已在实现与测试中固化。
2. **`ActivityPanel` 由条件渲染改为常驻挂载 + 宽度过渡**。原设计只要求
   `busy` 驱动与顶部偏移；实现时发现条件增删 DOM 本身引起 flex 宽度突变
   （属 RC4「抖动」的另一来源），故一并修复。
3. **移动端/窄屏 `min-height:100dvh` 未改动**：需实机验证，未纳入本次范围。

### 待实机验证（无法在此环境自动化的部分）

1. 运行期间右侧面板稳定可见、顶部不被顶栏遮挡、无左右抖动。
2. 多轮工具调用时，时间线始终紧跟各自消息（S1/S2）。
3. 思考模式下「思考中」在正文开始前切换为「思考了 N 秒」（S3）。
4. 审批只出现在消息时间线内（面板显示提示文案），且审批后能继续运行。
