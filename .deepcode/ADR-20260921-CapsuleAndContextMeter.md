# ADR-20260921：思考/推理强度语义重构 + 上下文用量修复

- 状态：已确认（用户 Checkpoint 通过），实现中
- 日期：2026-09-21
- 影响面：`frontend/src/store.js`、`i18n.js`、`components/AgentOptions.vue`、`App.vue`、`src/sse.js`、`__tests__/sse.test.js`、`backend/agent/llm.py`
- 关联：弹窗模糊修复见 `ADR-20260921-ModalBackdropFilter.md`（本轮一并实现）

---

## 一、思考 / 推理强度语义重构

### 1.1 症状与证据

| 症状 | 证据 |
|---|---|
| 左胶囊叫「思考模式」而非「思考强度」 | `i18n.js:75` `thinkingMode: '思考模式'`；`AgentOptions.vue:167` |
| 右胶囊叫「思考强度」而非「推理强度」 | `i18n.js:76` `reasoningEffort: '思考强度'` |
| 右胶囊含「关」选项（语义错位） | `i18n.js:24` `effOff: '关'`；`AgentOptions.vue:196` 选项 `['off','low','mid','high']` |
| 两胶囊互相耦合 | `store.js:29-33` `effectiveEffort()` 用 `effortSel==='off'` 关闭 thinking；`AgentOptions.vue:20-23` `thinkLabel` 会拼「关闭思考 · X」；两处 `.active` 交叉引用 |

### 1.2 根因

| 层级 | 内容 |
|---|---|
| 症状 | 命名错位 + "关"位置错误 + 两胶囊耦合 |
| 直接原因 | 右胶囊把「是否思考」和「推理强度」两件事混在一个枚举里（`off/low/mid/high`） |
| **根因** | **未按"控制目标"划分控件**：`thinking`（是否思考）与 `reasoning_effort`（推理强度）是 API 的两个独立旋钮，却被合并成一个枚举并与左胶囊交叉耦合 |

### 1.3 API 约束（不变量）

后端 schema 限定 `reasoning_effort ∈ {low, high, max}`（`schemas.py:70`）；
DeepSeek 额外支持 `thinking: {type: enabled|disabled}`（`llm.py:36-38`）。
→ 四档「默认/低/中/高」必须映射到三值集合，其中 **中→high、高→max**。

### 1.4 设计（用户确认）

| 控件 | 标题 | 选项 | 语义 |
|---|---|---|---|
| 左 | **思考强度** | 快速 / 标准 / 深度 | 快速 = **关闭思考**（`thinking=false`）；标准/深度 = 开启思考 |
| 右 | **推理强度** | **默认** / 低 / 中 / 高 | 默认 = **跟随思考强度**（标准→high，深度→max）；低/中/高 = low/high/max |

状态机（唯一事实源：`store.effectiveEffort()`）：

```
thinkMode = fast     → { thinking: false, effort: null }
thinkMode = standard → base = high
thinkMode = deep     → base = max

effortSel = default  → effort = base
effortSel = low      → effort = low
effortSel = mid      → effort = high
effortSel = high     → effort = max
```

不变量：
- I1：`thinking` 只由左胶囊决定，右胶囊永不改变它。
- I2：`reasoning_effort` 由右侧决定；`default` 时回落到左侧推导的 base。
- I3：UI 上两胶囊不交叉引用（不互相改写文案、不互相决定 active）。
- I4：`fast` 时 `reasoning_effort` 不发送（`llm.py` 已保证仅在 `thinking=True` 时注入）。

### 1.5 迁移

- `thinkMode` 默认值由 `fast` 改为 `standard`（默认开启思考、均衡）。
- `effortSel` 默认值由 `mid` 改为 `default`；旧的 `off` 存储值在读取时回落为 `default`（兼容已持久化的 localStorage）。

---

## 二、上下文用量（ContextMeter）无变化

### 2.1 症状与证据

`ContextMeter`（顶栏右侧）数值恒为 `0`，无任何变化。

### 2.2 根因 A：流式用量从未上报

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | tokens 恒为 0 | 消息入库 `tokens=0`；meter 不动 |
| 直接原因 | `usage_metadata` 始终为 `None`，`tokens_box["tokens"]` 保持 0 | `bridge.py` 仅在 `usage_metadata` 存在时赋值 |
| 根因 | **未开启 `stream_usage`**：langchain-openai 只在 `base_url` 等参数全为 `None` 时才自动开启；本项目始终传 `base_url` → 不发送 `stream_options.include_usage` → DeepSeek 流式响应不含 usage | `langchain_openai/chat_models/base.py:1172-1191`（自动开启条件）；`llm.py:100-108`（始终传 base_url） |

### 2.3 根因 B：语义错误（累加 vs 最近一次）

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | 即使有值也会虚高 | — |
| 直接原因 | 前端对每轮 `total_tokens` **累加**，并在打开会话时对历史消息 `tokens` **求和** | `store.js:81-83` `addContextTokens`；`App.vue` `openConv` 的 `reduce` |
| 根因 | **把"累计消耗"当成"上下文占用"**：每轮请求都会重发全部历史，`total_tokens` 已包含历史；累加会重复计数（近似平方增长） | 概念错误 |

### 2.4 设计

**根因 A 修复**：`build_llm` 在 `deepseek_compat=True` 时显式传 `stream_usage=True`
（DeepSeek 已验证支持 `stream_options.include_usage`）。
非 DeepSeek 兼容端点保持默认（不发送），避免破坏不支持该字段的第三方端点 —— 这是**泛化边界**。

**根因 B 修复**：上下文占用 = **最近一次 LLM 调用的 `total_tokens`**，采用 `set` 语义：
- `run_end.tokens` → `setContextTokens(tokens)`（后端该值取最后一次 usage 覆盖）
- 打开会话 → 取**最后一条有 tokens 的 assistant 消息**的 tokens（而非求和）

不变量：
- I5：`contextTokens` 单调对应当前上下文规模，不由历史累加产生。
- I6：`tokens=0`（未上报）不得覆盖已有值（避免回退为 0）。

### 2.5 复杂度

O(1) 更新；打开会话为 O(n) 单次扫描（n=消息数）。

---

## 三、防复发机制

| 机制 | 位置 |
|---|---|
| 语义不变量断言（左/右解耦、四档映射、默认跟随） | `__tests__/sse.test.js` 或新增 `capsule.test.js` |
| `contextTokens` 使用 set 语义的守卫（禁止 `addContextTokens` 复活） | `__tests__/sse.test.js` |
| `stream_usage` 必须为 deepseek_compat 开启 | `tests/test_bridge_events.py` 或 `tests/test_llm.py` |
| 弹窗遮罩禁止 `backdrop-filter`；三个弹窗引用 `.glass-dialog` | `__tests__/material.test.js`（依 ModalBackdropFilter ADR） |

---

## 四、测试计划

| ID | 类型 | 场景 | 期望 | 覆盖根因 |
|---|---|---|---|---|
| T1 | 单元 | `thinkMode=fast` | `{thinking:false, effort:null}` | 语义 |
| T2 | 单元 | `standard + default` / `deep + default` | effort = high / max | 语义 |
| T3 | 单元 | `standard + 低/中/高` | effort = low/high/max | 映射 |
| T4 | 单元 | `fast + 高` | `thinking:false`（右不改变左） | 解耦 I1 |
| T5 | 单元 | `run_end{tokens:120}` | `setContextTokens(120)` 被调用一次 | 根因 B |
| T6 | 单元 | `run_end{tokens:0}` | 原样上报（由 store 守卫忽略） | I6 |
| T7 | 守卫 | 遮罩类是否含 `backdrop-filter` | 无命中 | 弹窗根因 |
| T8 | 守卫 | 三个弹窗是否引用 `.glass-dialog` | 全部命中 | 弹窗根因 |
| T9 | 后端 | `deepseek_compat` 构建是否带 `stream_usage=True` | 断言为真 | 根因 A |
| T10 | 回归 | 现有用例 | 全通过 | — |

---

## 五、实现结果（Phase 3/4 完成后回填）

### 5.1 落地内容

| 文件 | 改动 |
|---|---|
| `frontend/src/thinking.js` | **新增**：思考/推理强度纯映射（`effectiveEffortFor` / `normalizeThinkMode` / `normalizeEffort`）——与 store 分离以便在 Node 测试环境覆盖 |
| `store.js` | `effectiveEffort()` 委托纯函数；`thinkMode` 默认 `standard`、`effortSel` 默认 `default`（旧 `off` 归一为 `default`）；`addContextTokens` 删除 → `setContextTokens`（忽略 ≤0，I6）+ `resetContextTokens` |
| `i18n.js` | 新增 `thinkingIntensity: 思考强度`、`reasoningIntensity: 推理强度`、`effDefault/effDefaultDesc`；删除 `effOff/effOffDesc`；`thinkFastDesc` 改为"关闭思考，响应最快"；保留 `thinkingMode`（供智能体配置表单使用，语义不同） |
| `AgentOptions.vue` | 左胶囊标题改「思考强度」、右胶囊改「推理强度」；右胶囊选项 `default/low/mid/high`；**移除两胶囊间的全部交叉耦合**（文案与 active 判定） |
| `TopBarOptions.vue` | 同步新选项模型与标题键；移除 `effortSel !== 'off'` 耦合 |
| `App.vue` | `run_end` 走 `setContextTokens`；`openConv` 取**最后一条有 tokens 的 assistant 消息**（不再求和）；`newChat`/`delConv` 走 `resetContextTokens` |
| `sse.js` | hook 更名 `addContextTokens` → `setContextTokens` |
| `backend/agent/llm.py` | `deepseek_compat` 显式 `stream_usage=True`；标准端点不开启（泛化边界） |
| `frontend/src/__tests__/capsule.test.js` | **新增** 10 个用例（T1–T4 + 归一化 + 选项模型守卫） |
| `tests/test_llm.py` | **新增** 5 个用例（T9 + thinking 参数注入 + 泛化边界） |

### 5.2 验证证据

| 验证 | 结果 |
|---|---|
| 前端测试 | `39 passed`（capsule 10 + sse 15 + material 14） |
| 后端测试 | `29 passed`（llm 5 + bridge 6 + documents 8 + smoke 10） |
| 生产构建 | `built in 5.95s`，无错误 |
| 弹窗修复 | 三个遮罩层已无 `backdrop-filter`（守卫 T1），三张卡片均引用 `.glass-dialog`（守卫 T2）——**该项在实现前已由并行工作流完成**，本轮补齐守卫 |

### 5.3 自审发现并修复的问题

**回归（已修复）**：删除 `effOff/effOffDesc` 后，`TopBarOptions.vue` 仍在用 `off/low/mid/high` 与 `effOff` 文案，
会导致顶栏胶囊显示原始 key；`AgentConfigPage.vue` / `AgentForm.vue` 仍在用 `t('thinkingMode')`。
处置：同步顶栏选项模型 + 保留 `thinkingMode` 键（智能体配置表单语义不同，不属本次重构范围），
并新增守卫（禁止 `'off', 'low', 'mid', 'high'` 与 `effOff` 复活）。

**测试修正**：弹窗守卫 T1 最初把注释中提到的 `backdrop-filter` 误判为违规 → 断言前剥离 CSS 注释。

### 5.4 待实机验证

1. 左胶囊显示「思考强度」、右胶囊显示「推理强度」，右胶囊无"关"档。
2. 快速 → 无思考过程（reasoning 不出现）；标准/深度 → 有思考，且深度更长。
3. 推理强度选「默认」时跟随思考强度；选低/中/高时覆盖强度但不改变思考开关。
4. 顶栏胶囊与输入框胶囊表现一致。
5. **上下文用量**：发送一条消息后顶栏环形表数值应变化；打开历史会话应显示该会话最近一次的上下文规模。
6. 弹窗（新建技能 / 新建智能体 / 管理模型）在浅色与暗色下均为均匀毛玻璃，无发黑/发灰。
