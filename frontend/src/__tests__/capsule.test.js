/**
 * 思考/推理强度语义测试（对应 ADR-20260921-CapsuleAndContextMeter 的 T1–T4）。
 *
 * 回归目标：旧实现把"是否思考"（off）与"推理强度"混在右胶囊里，
 * 并与左胶囊交叉耦合；本测试固化解耦后的映射规则。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { effectiveEffortFor, normalizeEffort, normalizeThinkMode } from '../thinking.js'

const SRC = join(fileURLToPath(new URL('.', import.meta.url)), '..')

function vueFiles(dir) {
  const out = []
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) {
      if (name === '__tests__') continue
      out.push(...vueFiles(full))
    } else if (name.endsWith('.vue')) {
      out.push(full)
    }
  }
  return out
}

const rel = (p) => relative(SRC, p).split(sep).join('/')

describe('effectiveEffortFor / 思考强度（左胶囊）', () => {
  it('T1 fast 关闭思考且不下发推理强度', () => {
    expect(effectiveEffortFor('fast', 'default')).toEqual({ thinking: false, effort: null })
    // I1：右胶囊不改变"是否思考"
    expect(effectiveEffortFor('fast', 'high')).toEqual({ thinking: false, effort: null })
  })

  it('T2 default 时推理强度跟随思考强度', () => {
    expect(effectiveEffortFor('standard', 'default')).toEqual({ thinking: true, effort: 'high' })
    expect(effectiveEffortFor('deep', 'default')).toEqual({ thinking: true, effort: 'max' })
  })
})

describe('effectiveEffortFor / 推理强度（右胶囊）', () => {
  it('T3 低/中/高 映射到 low/high/max（后端仅接受三值）', () => {
    expect(effectiveEffortFor('standard', 'low').effort).toBe('low')
    expect(effectiveEffortFor('standard', 'mid').effort).toBe('high')
    expect(effectiveEffortFor('standard', 'high').effort).toBe('max')
  })

  it('T4 右胶囊覆盖强度但不改变思考开关', () => {
    const r = effectiveEffortFor('deep', 'low')
    expect(r).toEqual({ thinking: true, effort: 'low' })
  })

  it('未知取值回落到默认（防御）', () => {
    expect(effectiveEffortFor('unknown', 'default')).toEqual({ thinking: true, effort: 'high' })
    expect(effectiveEffortFor('standard', 'unknown')).toEqual({ thinking: true, effort: 'high' })
  })
})

describe('normalize / 兼容旧存储', () => {
  it('旧的 off / mid 存储值不再被当作关闭思考', () => {
    expect(normalizeEffort('off')).toBe('default')
    expect(normalizeEffort('mid')).toBe('mid')
  })

  it('思考强度默认 standard（旧默认 fast 不再静默关闭思考）', () => {
    expect(normalizeThinkMode(null)).toBe('standard')
    expect(normalizeThinkMode('deep')).toBe('deep')
  })
})

describe('守卫：控件选项模型与文案一致', () => {
  it('不再出现已废弃的 off 档（关闭思考改由「快速」承担）', () => {
    const offenders = vueFiles(join(SRC, 'components'))
      .filter((f) => /'off',\s*'low',\s*'mid',\s*'high'/.test(readFileSync(f, 'utf-8')))
      .map(rel)
    expect(offenders, `以下组件仍在使用废弃的 off 档：${offenders.join(', ')}`).toEqual([])
  })

  it('不再引用已删除的 effOff / effOffDesc 文案', () => {
    const offenders = vueFiles(join(SRC, 'components'))
      .filter((f) => /effOff\b|effOffDesc\b/.test(readFileSync(f, 'utf-8')))
      .map(rel)
    expect(offenders, `以下组件引用了已删除的文案键：${offenders.join(', ')}`).toEqual([])
  })

  it('两处胶囊入口（输入框 + 顶栏）都使用新的标题键', () => {
    for (const name of ['AgentOptions.vue', 'TopBarOptions.vue']) {
      const src = readFileSync(join(SRC, 'components', name), 'utf-8')
      expect(src, `${name} 缺少思考强度标题`).toContain("t('thinkingIntensity')")
      expect(src, `${name} 缺少推理强度标题`).toContain("t('reasoningIntensity')")
    }
  })
})
