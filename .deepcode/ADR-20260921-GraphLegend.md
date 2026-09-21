# ADR-20260921：专家团图例颜色与节点不一致

- 状态：已确认（用户选择方案 B），实现中
- 日期：2026-09-21
- 影响面：`frontend/src/components/AgentConfigPage.vue`、`__tests__/material.test.js`

---

## 1. 问题陈述

专家团关系图左下角图例中，「其他专家」的圆点是**灰色**，但环上的内置专家节点实际使用**各自配色**。

## 2. 根因分析

### 2.1 事实证据

| 项 | 图例颜色 | 节点实际颜色 | 证据 |
|---|---|---|---|
| 主代理 | `var(--accent)` #5b57d2 | 中心节点 `--ec: '#5b57d2'` | `AgentConfigPage.vue:385`、`.lg-dot.main` L638 |
| **其他专家** | **`var(--text-muted)`（灰）** | **`expertForAgent(n.agent).color`** → `#0ea5e9` / `#f59e0b` / `#10b981` / `#ec4899` | 图例 L371 vs 节点 L403；颜色定义 `experts.js:16,23,30,37` |
| 自定义专家 | `#8b5cf6` | 外圈节点 `--ec: '#8b5cf6'` | L421、`.lg-dot.custom` L639 |

### 2.2 根因分层表

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | 图例「其他专家」为灰色，与图中彩色节点不符 | 用户反馈 |
| 直接原因 | 图例该行写死为默认灰点（无 `style`） | L371 `<i class="lg-dot"></i>` |
| **根因** | **图例与节点使用两套颜色来源**：节点是**数据驱动**（`experts.js`），图例是**硬编码**。只要专家配色变化或新增专家，图例必然失真 | L403 vs L371 |

### 2.3 泛化判断

| 问题 | 一次性 / 一类 | 代表输入 | 反例 | 非适用场景 |
|---|---|---|---|---|
| 图例与图形颜色不同源 | **一类**：任何"图例硬编码 + 图形数据驱动"的组合 | 专家团图 | 颜色恒定的项（主代理/自定义）不受影响 | 图例本身即由同一数据源渲染时不适用 |

**规则**：图例必须由与图形相同的数据源渲染，不得硬编码颜色。

## 3. 设计方案（用户确认：方案 B 逐色列举）

图例改为**数据驱动**：为环上每个内置专家渲染一个圆点 + 名称，颜色取自 `expertForAgent(agent).color`。

```html
<div class="graph-legend glass-weak">
  <span><i class="lg-dot main"></i>{{ t('mainAgent') }}</span>
  <span v-for="n in ring" :key="'lg' + n.agent.id">
    <i class="lg-dot" :style="{ background: expertForAgent(n.agent).color }"></i>
    {{ expertForAgent(n.agent).displayName }}
  </span>
  <span v-if="outer.length"><i class="lg-dot custom"></i>{{ t('customExperts') }}</span>
</div>
```

配套：`.graph-legend` 允许换行（`flex-wrap: wrap` + `max-width: calc(100% - 24px)` + `row-gap`），
避免逐色列举后在窄屏溢出。

不变量：
- I1：图例中每类节点的颜色必须来自与节点渲染相同的来源（`expertForAgent` / 常量），禁止硬编码。
- I2：图例不得使用默认灰点表示"多色集合"。

**复杂度**：O(k) 渲染，k = 内置专家数（≤5）。

## 4. 防复发机制

`material.test.js` 守卫：
1. 图例块必须包含 `expertForAgent(`（数据驱动）；
2. 图例块不得存在无内联样式的裸 `<i class="lg-dot"></i>`（即旧的灰点写法）。

## 5. 测试计划

| ID | 类型 | 场景 | 期望 |
|---|---|---|---|
| T1 | 守卫 | 图例颜色来源 | 含 `expertForAgent(`，无裸灰点 |
| T2 | 回归 | 现有前端用例 | 全通过 |
| T3 | 构建 | `npm run build` | 成功 |
| T4 | 手工 | 打开专家团页 | 图例列出各内置专家配色与名称，与节点一致 |
| T5 | 手工 | 窄屏 | 图例换行、不溢出 |

---

## 6. 实现结果

| 文件 | 改动 |
|---|---|
| `AgentConfigPage.vue` | 图例第二项由硬编码灰点改为 `v-for="n in ring"` 逐色列举（颜色取 `expertForAgent(n.agent).color`，名称取 `displayName`）；`.graph-legend` 增加 `flex-wrap` / `row-gap` / `max-width` 防窄屏溢出 |
| `__tests__/material.test.js` | 新增 2 个守卫（T1 数据驱动、T2 禁止裸灰点） |

验证：前端 `44 passed`（material 19 + sse 15 + capsule 10）；构建成功。

待实机验证：专家团页图例是否逐色列出内置专家且与节点颜色一致；窄屏下是否正常换行。
