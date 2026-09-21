# ADR-20260921：弹窗模糊异常（嵌套 backdrop-filter）

- 状态：待实现（Phase 1/2 完成）
- 日期：2026-09-21
- 影响面：`components/SkillsPage.vue`、`components/AgentConfigPage.vue`、`components/ModelManagerModal.vue`、`assets/main.css`、`src/__tests__/material.test.js`

---

## 1. 问题陈述

用户反馈："新建智能体的窗口、新建技能的窗口等，模糊效果很奇怪，特别黑、白、乱。"

现象特征：**只有部分弹窗出问题**（新建技能、新建智能体），而"管理模型"弹窗相对正常。

---

## 2. 根因分析

### 2.1 事实证据

| 弹窗 | 遮罩层（overlay） | 卡片（card） | 视觉结果 |
|---|---|---|---|
| 新建技能 `SkillsPage.vue` | `.sp-modal`：`rgba(10,10,30,.35)` + **`backdrop-filter: blur(6px)`** (`:306`) | `.sp-modal-card glass-pop` (`:70`)——**仅** `border-radius/padding`，材质取自全局 `.glass-pop`（`rgba(255,255,255,.26/.14/.18)` + `blur(60px)`） | **异常**（用户点名） |
| 新建智能体 `AgentConfigPage.vue` | `.form-overlay`：`rgba(15,17,27,.35)` + **`backdrop-filter: blur(6px)`** (`:668`) | `.form-shell glass-pop` (`:463`)——同上，无材质覆盖 | **异常**（用户点名） |
| 管理模型 `ModelManagerModal.vue` | `.pmm-overlay`：`rgba(15,17,27,.35)` + **`backdrop-filter: blur(6px)`** (`:389`) | `.pmm-card` **有**近实心覆盖：`rgba(255,255,255,.99/.975)` + `blur(60px)` (`:397-401`) | 相对正常 |

### 2.2 机制

CSS Filter Effects Level 2 规定：**带有 `backdrop-filter`（非 none）的元素会创建
"backdrop root"**；其后代元素的 `backdrop-filter` 只能采样到该 root **内部**的内容。

于是形成：

```
页面内容（body::before 环境渐变 + 页面元素）
  └─ .sp-modal / .form-overlay   ← backdrop-filter: blur(6px) 创建 backdrop root
        └─ .sp-modal-card / .form-shell  ← backdrop-filter: blur(60px)
              只能"看到"遮罩层自身那层纯色 rgba(10,10,30,.35)
              → 60px 模糊无内容可模糊，等于失效
```

### 2.3 症状对照

| 用户描述 | 成因 |
|---|---|
| **特别黑** | 卡片材质 `.glass-pop` 只有 26% 白（原本靠"模糊页面亮部"提亮）；模糊失效后，遮罩的深色纯色（rgba(10,10,30,.35)）直接透出，卡片发灰发黑 |
| **白** | 卡片内部元素（输入框 `var(--surface-1)`、近实心白控件）在发灰的卡片上对比突兀，形成"死白" |
| **乱** | 噪点纹理叠加在**无模糊的纯色**底上（噪点失去玻璃散射的融合），再叠多层边框与阴影 → 视觉杂乱 |
| 为何"管理模型"较轻 | `.pmm-card` 有近实心白覆盖，遮住了失效的模糊层，所以只是"平"，不明显 |

### 2.4 根因分层表

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | 部分弹窗模糊异常、发黑发灰、杂乱 | 用户反馈 |
| 直接原因 | 卡片的后背模糊实际失效，只剩半透明深色叠加 | 嵌套 backdrop root |
| **根因** | **遮罩层与卡片同时使用 `backdrop-filter`**——遮罩层本不需要模糊（只需压暗），却因创建 backdrop root 而"吃掉"了卡片的后背模糊 | `SkillsPage.vue:306`、`AgentConfigPage.vue:668`、`ModelManagerModal.vue:389` |

### 2.5 泛化判断

| 问题 | 一次性 / 一类 | 代表输入 | 反例 | 非适用场景 |
|---|---|---|---|---|
| 嵌套 backdrop-filter 失效 | **一类**：任何"遮罩 + 玻璃卡片"组合 | 新建技能/智能体弹窗 | 卡片有近实心覆盖时症状被掩盖（仍属同一缺陷） | 遮罩层不透明（无 backdrop-filter）时不受影响；`.img-lightbox`（遮罩内无玻璃子元素）不适用 |

---

## 3. 设计方案

### 3.1 遮罩层：只压暗，不模糊

移除三个遮罩层的 `backdrop-filter`，并适度加深纯色以保证压暗效果：

```css
/* 遮罩层：不使用 backdrop-filter（避免创建 backdrop root 使卡片模糊失效） */
.sp-modal, .form-overlay, .pmm-overlay {
  background: rgba(15,17,27,.46);
}
[data-theme="dark"] ... { background: rgba(0,0,0,.58); }
```

移除后，卡片自己的 `backdrop-filter` 将直接采样**页面内容**，毛玻璃效果真正生效。

### 3.2 弹窗卡片：新增共享类 `.glass-dialog`

`.glass-pop`（26% 白）是给"浮在内容上的小菜单"设计的；弹窗卡片需要**可读性优先**，
故新增近实心毛玻璃类（与 `.ao-menu`/`.to-menu` 已确认的"近实心"配方同族）：

```css
.glass-dialog {
  background: var(--noise-subtle), linear-gradient(180deg, rgba(255,255,255,.99), rgba(246,245,255,.975));
  backdrop-filter: blur(60px) saturate(200%);
  border: 1px solid rgba(255,255,255,.7);
  box-shadow: inset 0 1px 0 rgba(255,255,255,1), inset 0 -1px 0 rgba(20,18,60,.05),
              0 10px 26px rgba(20,18,60,.14), 0 28px 68px rgba(20,18,60,.22);
}
[data-theme="dark"] .glass-dialog { /* 深色近实心 */ }
```

替换：
- `SkillsPage.vue`：`.sp-modal-card glass-pop` → `glass-dialog`
- `AgentConfigPage.vue`：`.form-shell glass-pop` → `glass-dialog`
- `ModelManagerModal.vue`：`.pmm-card`/`.pmm-dlg-card` 的**内联材质**删除 → `glass-dialog`（消除重复）

### 3.3 复杂度

纯 CSS/模板；无运行时复杂度。消除 3 份重复的弹窗材质声明。

---

## 4. 防复发机制

1. **架构守卫**（`material.test.js` 扩展）：
   - 禁止"遮罩类"选择器（含 `overlay` / `modal` 且为 `position: fixed; inset: 0`）声明 `backdrop-filter`；
   - 断言三个弹窗卡片引用 `.glass-dialog`。
2. **文档**：`main.css` 注释写明"遮罩层禁止 backdrop-filter"及其原因（backdrop root 机制）。
3. **ADR 不变量 I3** 记入 `ControlMaterial` ADR，作为全局设计约束。

---

## 5. 测试计划

| ID | 类型 | 场景 | 期望 | 覆盖根因 | 覆盖防复发 |
|---|---|---|---|---|---|
| T1 | 守卫 | 扫描遮罩类规则是否含 `backdrop-filter` | 无命中 | 根因 | 是 |
| T2 | 守卫 | 三个弹窗卡片是否引用 `glass-dialog` | 全部命中 | 根因 | 是 |
| T3 | 回归 | 现有 20 个用例 | 全通过 | — | 是 |
| T4 | 构建 | `npm run build` | 成功 | — | 否 |
| T5 | 手工 | 浅色/暗色打开新建技能、新建智能体、管理模型 | 卡片为均匀毛玻璃、无发黑/发灰、噪点自然 | 症状 | 是 |
| T6 | 手工 | 弹窗内滚动、输入、关闭 | 行为不变 | — | 否 |
