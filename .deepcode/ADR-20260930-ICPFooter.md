# ADR-20260930：网站底部添加 ICP 备案号

- 状态：待确认（Phase 1/2 完成）
- 日期：2026-09-30
- 影响面：新增 `frontend/src/components/SiteFooter.vue`；`LoginPage.vue`、`Dashboard.vue`、`App.vue`；`__tests__/material.test.js`

---

## 1. 需求

通信管理局要求：在网站**首页底部**展示备案号 **辽ICP备2026015937号-1**，并**链接到工信部备案官网首页**（`https://beian.miit.gov.cn/`），否则驳回。

## 2. 现状评估

| 事实 | 证据 |
|---|---|
| 项目是 SPA，访问者首屏是登录页；登录后是落地页/聊天页 | `App.vue`：`<LoginPage v-if="!authed" />`；`Dashboard v-if="!msgs.length && welcomeShow"` |
| 聊天页底部已有免责声明行 | `App.vue:496` `.ai-disclaimer`（"内容由 AI 生成，仅供参考"） |
| 目前**没有任何**备案号展示 | 全仓无 `ICP` / `beian` 相关内容 |

## 3. 约束分析

这是**合规要求**而非缺陷修复，但同样存在"单一事实源"问题：备案号与链接若在多个页面各写一份，未来**变更备案号或链接时必然漏改**（与既有 ADR 的材质漂移同类）。

不变量：
- I1：备案号与工信部链接**只有一个定义处**（组件内），各页面只引用组件。
- I2：链接必须是 `https://beian.miit.gov.cn/`（工信部备案官网首页），新窗口打开且带 `rel="noopener"`。
- I3：备案号文本必须与备案系统一致：`辽ICP备2026015937号-1`（不得改写、不得截断）。

## 4. 设计方案

### 4.1 新增 `SiteFooter.vue`（唯一事实源）

```vue
<template>
  <div class="site-footer">
    <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">
      辽ICP备2026015937号-1
    </a>
  </div>
</template>
```

样式：小字号、`--text-muted`、居中、不抢视觉；hover 变 accent。

### 4.2 插入位置

| 位置 | 理由 |
|---|---|
| `LoginPage.vue` 底部 | 未登录访客的**首屏**（合规意义上的"首页"） |
| `Dashboard.vue` 底部（提示词胶囊下方） | 登录后的落地页 |
| `App.vue` 聊天页 `.ai-disclaimer` 附近 | 应用内常驻可见 |

不引入全站固定页脚：聊天页为滚动布局 + 底部输入框，固定页脚会遮挡输入区。

**复杂度**：O(1)；无运行时逻辑。

## 5. 防复发机制

`material.test.js` 守卫：
1. 断言 `SiteFooter.vue` 含备案号原文 `辽ICP备2026015937号-1`；
2. 断言链接为 `https://beian.miit.gov.cn/`；
3. 断言三个页面均引用了 `SiteFooter`（防止页面改版时被删掉 → 备案被驳回）。

## 6. 测试计划

| ID | 类型 | 场景 | 期望 |
|---|---|---|---|
| T1 | 守卫 | 备案号原文 | 与备案一致 |
| T2 | 守卫 | 链接地址 | `https://beian.miit.gov.cn/` |
| T3 | 守卫 | 三处引用 | 全部命中 |
| T4 | 回归 | 现有前端用例 | 全通过 |
| T5 | 构建 | `npm run build` | 成功 |
| T6 | 手工 | 未登录首页 / 落地页 / 聊天页 | 底部可见备案号，点击新窗口打开工信部备案官网 |

---

## 7. 实现结果

| 文件 | 改动 |
|---|---|
| `components/SiteFooter.vue` | **新增**：备案号 + 工信部链接的唯一事实源（小字、muted、hover 变 accent） |
| `components/LoginPage.vue` | 引入并在页面底部渲染；`.login-page` 加 `position: relative`，页脚用 `.login-footer` 绝对定位钉底（登录页是 flex 居中布局，页脚若作为普通子元素会被排到卡片旁边） |
| `components/Dashboard.vue` | 引入并在提示词胶囊下方渲染 |
| `App.vue` | 引入并在聊天页免责声明下方渲染（`v-if="msgs.length"`，与落地页互斥，避免重复） |
| `__tests__/material.test.js` | 新增 4 个守卫（T1 备案号原文、T2 链接与 `_blank`/`noopener`、T3 三处引用、T4 备案号单点维护） |

验证：前端 `48 passed`；构建成功。

**自审发现并修复**：`.login-page` 是 `display:flex; align-items:center` 布局，页脚作为普通子元素会被排到登录卡片**旁边**而非页面底部 → 改为 `position: relative` + 页脚绝对定位钉底。

待实机验证：未登录首屏、落地页、聊天页底部均可见备案号；点击新窗口打开 `beian.miit.gov.cn`。

---

## 8. 布局修正（用户验收反馈）

首次实现的布局不符合预期：落地页备案号跟在提示词胶囊后面（不在页面底部）、聊天页备案号另起一行（应与免责声明同行）。

### 8.1 根因

| 症状 | 直接原因 | 根因 |
|---|---|---|
| 落地页备案号不在底部 | 它作为 `.dashboard`（居中 flex 列）的最后一个子元素，只排在内容之后 | 组件**自带布局**（居中 + 内边距），与宿主页面的布局需求互相打架 |
| 聊天页备案号另起一行 | 它是 `.ai-disclaimer` 的**兄弟块级元素** | 同上：没有"同行"的表达能力 |

### 8.2 修正方案

1. **`SiteFooter` 改为布局中立**：根节点直接是内联 `<a>`（去掉自带的外层 div、居中与内边距），位置完全由宿主决定。
2. **聊天页**：免责声明与备案号放进同一个 `.chat-foot` flex 行（`[— 内容由 AI 生成，仅供参考 —] · [辽ICP备…]`）。
3. **落地页**：由 `App.vue` 的底部行统一渲染——落地页时输入框隐藏，该行即**页面最底部**；`Dashboard.vue` 不再单独渲染（避免重复）。
4. **登录页**：`.login-footer` 保持绝对定位钉底，并补 `text-align: center`（根节点变为内联元素后需要）。
5. 守卫 T3 同步更新：断言 `LoginPage` 与 `App.vue` 引用页脚，且 `Dashboard` **不再**单独渲染。

### 8.3 验证

前端 `48 passed`；构建成功。待实机验证：落地页底部、聊天页与免责声明同行、登录页底部。
