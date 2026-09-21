# ADR-20260921：弹窗错位发黑（transform 包含块）

- 状态：待确认（Phase 1/2 完成）
- 日期：2026-09-21
- 影响面：`frontend/src/components/SkillsPage.vue`、`components/AgentConfigPage.vue`、`assets/main.css`、`__tests__/material.test.js`
- 关联：`ADR-20260921-ModalBackdropFilter.md`（上一个弹窗问题，已修复且已 Teleport 管理模型弹窗）

---

## 1. 问题陈述

用户操作：技能页 → 点击「新建」→ 弹窗**错位 + 发黑**，"都要看不见了"。

## 2. 根因分析

### 2.1 事实证据

| 事实 | 证据 |
|---|---|
| 页面容器有持续生效的 `transform` 动画 | `main.css:373` `.main.view-anim > * { animation: viewIn .35s var(--spring) both }`；`main.css:466` `@keyframes viewIn { from { opacity:0; transform: translateY(14px) } to { opacity:1; transform: translateY(0) } }` |
| `both` 填充模式使动画结束后**保留 `to` 关键帧**，即 `transform: translateY(0)`（**非 `none`**） | 同上；`.main` 的直接子元素 = 各页面组件（SkillsPage / AgentConfigPage / …） |
| SkillsPage 的弹窗渲染在页面容器内部 | `SkillsPage.vue:69` `<div v-if="formOpen" class="sp-modal">`，其模板根为 `.skills-page`（`.main` 的直接子元素） |
| AgentConfigPage 同理 | `AgentConfigPage.vue:462` `<div v-if="showForm" class="form-overlay">` |
| 弹窗使用 `position: fixed; inset: 0` | `.sp-modal { position: fixed; inset: 0; ... }`；`.form-overlay` 同 |
| 管理模型弹窗**已** Teleport 到 body，故相对正常 | `ModelManagerModal.vue:225` `<Teleport to="body">` |

### 2.2 机制

CSS 规范：**非 `none` 的 `transform` 会成为其后代 `position: fixed` 元素的包含块**。

```
.main.view-anim > *   ← 动画结束后仍保留 transform: translateY(0)
  └─ SkillsPage（被包含块约束）
       └─ .sp-modal { position: fixed; inset: 0 }
            → 不再相对视口，而是相对 SkillsPage 的盒子
            → 遮罩只覆盖页面局部、卡片在局部内居中
            → 视觉结果：错位 + 大片深色遮罩 =「发黑、几乎看不见」
```

### 2.3 根因分层表

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | 新建技能弹窗错位、发黑、几乎不可见 | 用户反馈 |
| 直接原因 | 弹窗的 `position: fixed` 被祖先的 `transform` 改变了包含块，遮罩不再覆盖视口 | 上述机制 |
| **根因** | **弹窗渲染在会建立包含块的页面容器内部**：`position: fixed` 依赖视口，但祖先的 transform（来自入场动画的 `both` 填充）把它劫持了 | `main.css:373` + 两个页面模板 |

### 2.4 泛化判断

| 问题 | 一次性 / 一类 | 代表输入 | 反例 | 非适用场景 |
|---|---|---|---|---|
| 祖先 transform 劫持 fixed 定位 | **一类**：任何"在会被动画/变换的容器内渲染 fixed 浮层" | 新建技能/新建智能体弹窗 | 管理模型弹窗（已 Teleport，免疫） | 祖先无 transform/filter/contain 时不触发 |

**规则**：模态浮层不得依赖渲染位置——必须 Teleport 到 `body`；容器入场动画不得残留 `transform`。

## 3. 设计方案

### 3.1 弹窗 Teleport 到 body（根治定位）

- `SkillsPage.vue`：`<div v-if="formOpen" class="sp-modal">…</div>` → 包裹 `<Teleport to="body">…</Teleport>`
- `AgentConfigPage.vue`：`<div v-if="showForm" class="form-overlay">…</div>` → 同上
- 样式无需改动：Vue 的 scoped 属性随节点一起移动，`.sp-modal` / `.form-overlay` 规则仍生效
- 项目已有先例：`ChatMessage.vue` 的图片灯箱、`ModelManagerModal.vue`

### 3.2 入场动画不残留 transform（消除包含块）

`main.css`：`.main.view-anim > * { animation: viewIn .35s var(--spring) both }`
→ 填充模式由 `both` 改为 `backwards`。

理由：元素动画结束后的自然状态本就是 `opacity:1; transform:none`，无需 `forwards` 保留终态；
`backwards` 在无延迟时等价于不填充，动画结束后 `transform` 恢复 `none` → 不再建立包含块。

不变量：
- I1：模态浮层必须渲染在 `body` 下（Teleport），不得依赖祖先布局上下文。
- I2：容器级入场动画不得以 `forwards`/`both` 残留 `transform`。

**复杂度**：O(1)。

## 4. 防复发机制

`material.test.js` 新增守卫：
1. 断言 `SkillsPage.vue` / `AgentConfigPage.vue` / `ModelManagerModal.vue` 的模态根节点位于 `<Teleport to="body">` 内；
2. 断言 `.main.view-anim > *` 的动画填充模式不含 `both`/`forwards`（防止 transform 残留复活）。

## 5. 测试计划

| ID | 类型 | 场景 | 期望 |
|---|---|---|---|
| T1 | 守卫 | 三个弹窗组件是否 Teleport 到 body | 全部命中 |
| T2 | 守卫 | `.main.view-anim > *` 的 fill-mode | 不含 `both` / `forwards` |
| T3 | 回归 | 现有前端用例 | 全通过 |
| T4 | 构建 | `npm run build` | 成功 |
| T5 | 手工 | 技能页新建/编辑弹窗 | 居中覆盖全屏、遮罩均匀、无错位发黑 |
| T6 | 手工 | 智能体页新建/编辑弹窗 | 同上 |
| T7 | 手工 | 切换页面（触发入场动画）后立刻打开弹窗 | 仍居中正常 |

---

## 6. 实现结果

| 文件 | 改动 |
|---|---|
| `SkillsPage.vue` | `.sp-modal` 包裹 `<Teleport to="body">`（附原因注释） |
| `AgentConfigPage.vue` | `.form-overlay` 包裹 `<Teleport to="body">` |
| `assets/main.css` | `.main.view-anim > *` 填充模式 `both` → `backwards`（动画结束不残留 transform） |
| `__tests__/material.test.js` | 新增 2 个守卫（T1 三弹窗 Teleport、T2 入场动画 fill-mode） |

### 验证证据

| 验证 | 结果 |
|---|---|
| 前端测试 | `42 passed`（material 17 + sse 15 + capsule 10） |
| 生产构建 | `built in 10.85s`，无错误 |
| 全站 fixed 浮层审计 | 7 处 `position: fixed` 全部为 Teleport 或在顶层（TopBar）：AgentOptions 二级菜单、TopBarOptions 二级菜单、ChatMessage 灯箱、ModelManagerModal、以及本次修复的两个弹窗 |

### 已知同类隐患（未改，记录备查）

`.graph-wrap`（AgentConfigPage）、`ProfilePage` 页面级容器等仍有 `animation: ... both`。
当前它们**不含** `position: fixed` 后代，故无可见故障；但属同一反模式，
后续若在其中新增浮层会复发。已由 T2 的规则约束 `.main.view-anim`，
其余容器可在后续迭代统一清理。

### 待实机验证

1. 技能页「新建 / 编辑」弹窗：居中、遮罩覆盖全屏、无发黑。
2. 智能体页「新建 / 编辑」弹窗：同上。
3. 切换页面后立刻打开弹窗：定位仍正确（验证动画残留已消除）。
4. 管理模型弹窗：行为不变。
