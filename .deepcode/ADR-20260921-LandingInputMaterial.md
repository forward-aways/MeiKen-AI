# ADR-20260921：落地页输入框材质统一（输入框材料抽象）

- 状态：待评审（Phase 2.5 完成，等待 CHECKPOINT）
- 日期：2026-09-21
- 影响面：`frontend/src/assets/main.css`、`frontend/src/components/Dashboard.vue`、`frontend/src/components/MessageInput.vue`（可选：其余 10 个含内联材质的组件）

---

## 1. 背景与问题陈述

用户在验收时发现：**落地页（Dashboard）的输入框仍是旧样式**，与已升级为亚克力/液态玻璃的聊天输入框（MessageInput）不一致。

该问题不是"漏改一个样式"，而是**同一语义的视觉材料在多个组件中被各自实现**，导致升级时必然漂移。

---

## 2. 症状

| 编号 | 症状 | 说明 |
|---|---|---|
| S1 | 落地页输入框视觉与聊天输入框不一致 | 落地页为近不透明白色卡片；聊天页为半透明玻璃 |
| S2 | 落地页内部自相矛盾 | 同页的提示胶囊 `.prompt-chip` 已是新玻璃材质，输入框却是旧材质 |
| S3 | 焦点态、暗色态表现不同 | 两者 focus 光环与暗色底完全不同 |

---

## 3. 证据（代码位置）

**旧材质（落地页输入框）** — `frontend/src/components/Dashboard.vue:151-165`

```css
.landing-input {
  background: linear-gradient(180deg, rgba(255,255,255,.94), rgba(255,255,255,.84));
  backdrop-filter: blur(20px) saturate(160%);
  border: 1.5px solid var(--border-strong);
  box-shadow: var(--shadow-ambient), var(--shadow-key);
}
[data-theme="dark"] .landing-input { background: linear-gradient(180deg, rgba(32,35,52,.94), rgba(27,30,46,.86)); }
.landing-input:focus-within { box-shadow: 0 0 0 4px rgba(91,87,210,.12), ...; }
```

**新材质（聊天输入框）** — `frontend/src/components/MessageInput.vue:196-216`

```css
.input-inner {
  background:
    url("...feTurbulence...opacity='0.04'..."),           /* 噪点 */
    linear-gradient(180deg, rgba(255,255,255,.58), rgba(255,255,255,.32));  /* 半透明染色 */
  backdrop-filter: blur(28px) saturate(185%);
  border: 1.5px solid rgba(255,255,255,.65);              /* 玻璃边缘 */
  box-shadow: inset 0 1px 0 rgba(255,255,255,.75),        /* 高光 */
              0 4px 18px rgba(20,18,60,.07);
}
[data-theme="dark"] .input-inner { background: url("...opacity='0.05'..."), linear-gradient(180deg, rgba(44,48,72,.6), rgba(30,33,52,.45)); ... }
.input-inner.drag-over { ... }
```

**同页胶囊已是新材质** — `Dashboard.vue:188-207`（含噪点 + `blur(24px) saturate(180%)`）

**系统性重复**：噪点材质在 12 个组件中以完整 data-URI 内联，共 **43 处**

| 组件 | 处数 |
|---|---|
| ModelManagerModal.vue | 10 |
| AgentOptions.vue / TopBarOptions.vue | 各 6 |
| AgentConfigPage.vue / SkillsPage.vue | 各 3 |
| ExpertTeamBar.vue / KbPage.vue / LoginPage.vue / Sidebar.vue / Dashboard.vue / MessageInput.vue / ChatMessage.vue | 各 1–4 |

噪点不透明度存在 4 个不同取值：`0.04` / `0.045` / `0.05` / `0.06`。

---

## 4. 根因分析

### 4.1 5 Whys

| 层 | 问题 | 回答 |
|---|---|---|
| 1 | 为什么落地页输入框是旧样式？ | 升级材质时只改了 MessageInput，未改 Dashboard |
| 2 | 为什么只改了一个？ | 两者是**两份独立实现**，样式各自内联在 scoped CSS 中 |
| 3 | 为什么会有两份实现？ | 落地页与聊天页的输入区需求不同（无停止/图片），实现时复制而非抽象 |
| 4 | 为什么复制后没有约束？ | 材料（染色/模糊/噪点/高光/边缘/阴影）**没有共享定义**，也没有任何检查 |
| 5 | 为什么会必然漂移？ | 材料的"单一事实源"不存在 → 任一实例升级都会与其余实例分叉 |

### 4.2 根因分层表

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | 落地页输入框仍是旧样式 | 用户验收发现；`Dashboard.vue:151-165` |
| 直接原因 | 亚克力升级只落在 `MessageInput.vue`，未同步 `Dashboard.vue` | 两处 CSS 对比 |
| **根因** | **"输入框材料"没有单一事实源**：同一视觉语义被内联复制到多个组件，升级无法保证一致 | 噪点 43 处内联；两份输入框样式独立维护 |

### 4.3 泛化判断

| 问题类型 | 一次性 / 一类 | 代表输入 | 反例 | 非适用场景 |
|---|---|---|---|---|
| 材料漂移 | **一类**：任何"同一语义视觉元素在多组件各写一份"的情况 | 两个输入框 | 菜单/弹窗刻意使用更实心的 `.glass-pop`（**有意不同**，不应强行统一） | 语义本就不同的材质（如用户气泡 vs 助手气泡） |

> 结论：规则不是"所有材质必须同一"，而是**"同一语义的材质必须有单一事实源"**。`.glass-pop` 与 `.glass-input` 是不同语义，各自单一即可。

---

## 5. 设计方案

### 5.1 方案 A（最小，推荐先行）：抽取共享输入框材料类

在 `main.css` 的玻璃材质系统中新增 `.glass-input`，封装输入的完整配方：

```css
/* 输入框玻璃材质：半透明染色 + 噪点 + 模糊 + 高光 + 玻璃边缘 + 柔和投影 */
.glass-input {
  background:
    var(--noise-soft),
    linear-gradient(180deg, rgba(255,255,255,.58), rgba(255,255,255,.32));
  backdrop-filter: blur(28px) saturate(185%);
  -webkit-backdrop-filter: blur(28px) saturate(185%);
  border: 1.5px solid rgba(255,255,255,.65);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.75), 0 4px 18px rgba(20,18,60,.07);
  transition: border-color .25s var(--ease), box-shadow .25s var(--ease);
}
[data-theme="dark"] .glass-input {
  background:
    var(--noise-medium),
    linear-gradient(180deg, rgba(44,48,72,.6), rgba(30,33,52,.45));
  border-color: rgba(255,255,255,.12);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 4px 18px rgba(0,0,0,.25);
}
.glass-input:focus-within {
  border-color: var(--accent);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.8), 0 0 0 3px rgba(91,87,210,.12), 0 4px 18px rgba(91,87,210,.12);
}
[data-theme="dark"] .glass-input:focus-within {
  box-shadow: inset 0 1px 0 rgba(255,255,255,.1), 0 0 0 3px rgba(126,121,247,.15), 0 4px 18px rgba(0,0,0,.3);
}
.glass-input.drag-over {
  border-color: var(--accent);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.8), 0 0 0 3px rgba(91,87,210,.18), 0 4px 18px rgba(91,87,210,.15);
}
```

组件侧只保留**布局**（宽度、圆角、内边距、动画），删除材料声明：

- `MessageInput.vue`：`.input-inner` 去掉 background/blur/border/box-shadow/focus/dark/drag，改为模板上 `class="input-inner glass-input"`。
- `Dashboard.vue`：`.landing-input` 同上。

### 5.2 方案 B（推荐叠加）：噪点令牌化 + 架构守卫

1. 在 `:root` 定义 4 个噪点令牌，**逐字保留现有不透明度**（避免任何视觉变化）：

```css
--noise-subtle: url("...opacity='0.04'...");
--noise-soft:   url("...opacity='0.045'...");
--noise-medium: url("...opacity='0.05'...");
--noise-strong: url("...opacity='0.06'...");
```

2. 将 12 个组件中 43 处内联噪点替换为对应令牌（机械替换，不改其它属性）。
3. 新增守卫测试 `frontend/src/__tests__/material.test.js`：**禁止 `main.css` 之外出现 `feTurbulence`**。该测试在当前代码上失败（43 处），在方案 B 完成后通过 → 真正防止内联材质再次扩散。

### 5.3 组件 API 契约

```
MessageInput.vue
  props:  modelValue, disabled, placeholder   （不变）
  emits:  update:modelValue, send, stop, tempFile （不变）
  class:  "input-inner glass-input"（材料来自全局类）

Dashboard.vue
  template: class="landing-input glass-input"（材料来自全局类）
  行为不变：typewriter / 自动聚焦 / textarea 自适应 / tempFile / 提示胶囊
```

### 5.4 复杂度

纯 CSS/模板重构：无运行时复杂度变化；CSS 体积略降（消除重复 data-URI，方案 B 下每处约 300 字节 × 43 ≈ 12KB 源码级去重，构建后 gzip 收益较小但可读性显著提升）。

---

## 6. 备选方案与取舍

| 决策点 | 方案 | 优点 | 缺点 | 取舍 |
|---|---|---|---|---|
| 材料统一 | **A 共享 `.glass-input`** | 改动小、零行为风险 | 两份 markup 仍在，按钮/工具条仍可能漂移 | 推荐先行 |
| 材料统一 | B' 落地页直接复用 `MessageInput.vue`（variant） | 彻底消除第二份实现 | 需为落地页屏蔽图片/停止、迁移本地状态与聚焦逻辑，回归面较大 | 可作为后续独立迭代 |
| 噪点治理 | **B 令牌化 + 守卫测试** | 消除全站同类漂移；可执行防复发 | 触及 12 文件（机械替换） | 推荐叠加 |
| 噪点治理 | 不动 | 无风险 | 同类问题必复发（下次升级材质仍会漏） | 不满足防复发要求 |

---

## 7. 防复发机制

1. **单一事实源**：材料定义只在 `main.css`，组件只引用类名。
2. **架构守卫测试**（方案 B）：`material.test.js` 断言 `main.css` 外无 `feTurbulence`，违规即失败。
3. **契约测试**：断言 `MessageInput.vue` / `Dashboard.vue` 模板包含 `glass-input`，防止未来新输入框绕过共享类。
4. **文档**：在 `main.css` 的材质系统段落补注释，说明"新增输入框必须复用 `.glass-input`"。

---

## 8. 测试计划

| ID | 类型 | 场景 | 期望 | 覆盖根因 | 覆盖防复发 |
|---|---|---|---|---|---|
| T1 | 单元/守卫 | 扫描 `frontend/src/**/*.{vue,css}` 查找 `feTurbulence` | 仅 `main.css` 命中（方案 B） | 根因 | 是 |
| T2 | 单元/契约 | 扫描两个输入组件模板 | 均含 `glass-input` | 根因 | 是 |
| T3 | 构建 | `npm run build` | 成功，无 CSS 报错 | — | 否 |
| T4 | 回归 | 现有 `npm test`（14 用例） | 全通过（不破坏既有逻辑） | — | 是 |
| T5 | 手工 | 浅色/暗色下落地页与聊天页输入框对比 | 材质、焦点态、暗色一致 | 症状 S1/S3 | 是 |
| T6 | 手工 | 落地页：聚焦、打字自适应、上传临时文件、提示胶囊点击 | 行为不变 | — | 否 |
| T7 | 手工 | 聊天页：聚焦、拖拽图片高亮（drag-over） | 行为不变 | — | 是 |

---

## 9. 决策（Checkpoint，2026-09-21 用户确认）

1. **材料统一范围**：**A 共享 `.glass-input` 材质类**（不做 B' 组件复用）。
2. **噪点治理**：**执行方案 B**（令牌化 12 文件 43 处 + 守卫测试）。
3. **行为差异**：**一并补齐落地页图片支持**（粘贴 / 拖拽 / 上传）。

> 用户已确认，进入 Phase 3 实现。

---

## 10. 实现结果（Phase 3/4 完成后回填）

### 落地内容

| 文件 | 改动 |
|---|---|
| `assets/main.css` | 新增 4 个噪点令牌（`--noise-subtle/soft/medium/strong`，逐字保留 0.04/0.045/0.05/0.06）；新增 `.glass-input` 完整材质（含暗色 / `:focus-within` / `.drag-over`）与使用说明注释 |
| 12 个组件 | 43 处内联噪点 data-URI → 对应令牌（脚本精确字符串替换，非正则） |
| `components/MessageInput.vue` | 材质移出，仅留布局；改用 `glass-input` 类与共享组合式函数；预览行改用 `AttachPreview` |
| `components/Dashboard.vue` | 旧实心材质删除，改用 `glass-input`；新增图片粘贴 / 拖拽 / 上传 / 预览；`send` 事件携带 `imageIds` |
| `attachments.js` | **新增**：图片附件行为唯一实现（`useImageAttachments`） |
| `components/AttachPreview.vue` | **新增**：附件预览行唯一实现（结构 + 样式单点维护） |
| `App.vue` | 落地页 `@send` 改为 `(text, ids) => send(text, false, ids)` |
| `src/__tests__/material.test.js` | **新增**：6 个架构守卫用例 |

### 验证证据

| 验证 | 结果 |
|---|---|
| 噪点替换量 | **43 处**，与审计数量完全一致 |
| 残留检查 | `feTurbulence` 仅存在于 `main.css`（4 个令牌 + 1 条注释） |
| 前端测试 | `20 passed`（sse 14 + material 6） |
| 生产构建 | `built in 10.31s`，无错误 |
| **守卫有效性证明** | `Dashboard.vue@HEAD` / `MessageInput.vue@HEAD` 均含 `feTurbulence` 且不含 `glass-input` → T1/T2 在修复前必然失败 |

### 与设计的偏差

1. **新增 `AttachPreview.vue` 与 `attachments.js`**（设计未列）。原因：补齐落地页图片支持时，
   预览结构与上传逻辑会第二次复制，直接违背本次根因（同一语义多处实现），
   故一并抽象为单点实现，并加入守卫 T2c/T2d。
2. **`sendMsg` 不以 `canSend` 为闸门**。自审时发现：提示胶囊传入文本而输入框为空，
   若以 `canSend`（要求输入框非空）把关会导致胶囊失效；改为只校验"有内容且无图片在上传"。

### 待实机验证

1. 浅色 / 暗色下落地页与聊天页输入框材质、焦点态、拖拽高亮一致（S1/S3）。
2. 落地页：粘贴截图、拖拽图片、点图片按钮上传、删除预览、发送后气泡显示图片。
3. 落地页：提示胶囊在输入框为空时仍可点击发送。
4. 聊天页回归：图片上传 / 拖拽高亮 / 停止生成 / 临时文件均正常。
