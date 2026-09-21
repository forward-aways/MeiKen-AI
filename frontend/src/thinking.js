/**
 * 思考 / 推理强度的纯逻辑（唯一事实源）。
 *
 * 与 store.js 分离的原因：store 在模块级读取 localStorage / window，
 * 无法在 Node 测试环境直接导入；把映射规则抽成纯函数后可被单元测试覆盖。
 *
 * 不变量（见 ADR-20260921-CapsuleAndContextMeter）：
 * - I1 `thinking` 只由 thinkMode 决定，effortSel 永不改变它；
 * - I2 `effort` 由 effortSel 决定，`default` 时回落到 thinkMode 推导的基础强度；
 * - I3 关闭思考时 effort 为 null（不发送 reasoning_effort）。
 */

export const THINK_MODES = ['fast', 'standard', 'deep']
export const EFFORT_LEVELS = ['default', 'low', 'mid', 'high']

// 思考强度 → 基础推理强度（快速=关闭思考，无强度）
const THINK_EFFORT = { standard: 'high', deep: 'max' }
// 推理强度 → API 取值（中→high，高→max；后端 schema 仅接受 low|high|max）
const EFFORT_OVERRIDE = { low: 'low', mid: 'high', high: 'max' }

export function normalizeThinkMode(v) {
  return THINK_MODES.includes(v) ? v : 'standard'
}

export function normalizeEffort(v) {
  // 兼容旧存储：'off' 已废弃（关闭思考改由「快速」承担）
  return EFFORT_LEVELS.includes(v) ? v : 'default'
}

/**
 * @param {string} thinkMode  思考强度：fast | standard | deep
 * @param {string} effortSel  推理强度：default | low | mid | high
 * @returns {{thinking: boolean, effort: string|null}}
 */
export function effectiveEffortFor(thinkMode, effortSel) {
  if (thinkMode === 'fast') return { thinking: false, effort: null }
  const base = THINK_EFFORT[thinkMode] || 'high'
  if (effortSel === 'default') return { thinking: true, effort: base }
  return { thinking: true, effort: EFFORT_OVERRIDE[effortSel] || base }
}
