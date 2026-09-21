/**
 * 材质架构守卫（对应 ADR-20260921-LandingInputMaterial 的防复发机制）。
 *
 * 背景：材质曾以完整 data-URI 内联在 12 个组件共 43 处，导致升级时只改了
 * 聊天输入框、漏掉落地页输入框。守卫把"同一语义材质必须有单一事实源"
 * 变成可执行约束，而不是口头约定。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = join(fileURLToPath(new URL('.', import.meta.url)), '..')
const MAIN_CSS = join(SRC, 'assets', 'main.css')

function walk(dir) {
  const out = []
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) {
      if (name === '__tests__') continue
      out.push(...walk(full))
    } else if (/\.(vue|css)$/.test(name)) {
      out.push(full)
    }
  }
  return out
}

const files = walk(SRC)
const rel = (p) => relative(SRC, p).split(sep).join('/')

describe('material single source of truth', () => {
  it('T1 keeps every noise texture inside main.css', () => {
    const offenders = files
      .filter((f) => rel(f) !== 'assets/main.css')
      .filter((f) => readFileSync(f, 'utf-8').includes('feTurbulence'))
      .map(rel)

    expect(offenders, `噪点材质必须使用 var(--noise-*)，禁止内联：${offenders.join(', ')}`).toEqual([])
  })

  it('T1b declares the four noise tokens in main.css', () => {
    const css = readFileSync(MAIN_CSS, 'utf-8')
    for (const token of ['--noise-subtle', '--noise-soft', '--noise-medium', '--noise-strong']) {
      expect(css, `缺少噪点令牌 ${token}`).toContain(`${token}:`)
    }
  })

  it('T2 makes both input surfaces reference the shared .glass-input class', () => {
    const chat = readFileSync(join(SRC, 'components', 'MessageInput.vue'), 'utf-8')
    const landing = readFileSync(join(SRC, 'components', 'Dashboard.vue'), 'utf-8')
    expect(chat).toMatch(/class="[^"]*glass-input/)
    expect(landing).toMatch(/class="[^"]*glass-input/)
  })

  it('T2b defines the input material once, in main.css only', () => {
    const css = readFileSync(MAIN_CSS, 'utf-8')
    expect(css).toContain('.glass-input {')

    // 组件不得重新声明输入框的玻璃边缘/模糊，否则又会分叉
    const offenders = files
      .filter((f) => rel(f) !== 'assets/main.css')
      .filter((f) => /blur\(28px\) saturate\(185%\)/.test(readFileSync(f, 'utf-8')))
      .map(rel)
    expect(offenders, `输入框模糊参数必须来自 .glass-input：${offenders.join(', ')}`).toEqual([])
  })

  it('T2c shares one image-attachment implementation', () => {
    const chat = readFileSync(join(SRC, 'components', 'MessageInput.vue'), 'utf-8')
    const landing = readFileSync(join(SRC, 'components', 'Dashboard.vue'), 'utf-8')
    expect(chat).toContain('useImageAttachments')
    expect(landing).toContain('useImageAttachments')
    // 上传逻辑不得在组件内复制
    expect(chat).not.toContain('uploadImage(')
    expect(landing).not.toContain('uploadImage(')
  })

  it('T2d shares one attachment preview implementation', () => {
    const chat = readFileSync(join(SRC, 'components', 'MessageInput.vue'), 'utf-8')
    const landing = readFileSync(join(SRC, 'components', 'Dashboard.vue'), 'utf-8')
    expect(chat).toContain('AttachPreview')
    expect(landing).toContain('AttachPreview')
    // 预览行结构只允许存在于 AttachPreview.vue
    expect(chat).not.toContain('class="image-preview-row"')
    expect(landing).not.toContain('class="image-preview-row"')
  })
})

describe('control surfaces share one material (elevation system)', () => {
  const read = (name) => readFileSync(join(SRC, 'components', name), 'utf-8')

  it('T3 keeps capsule material out of components', () => {
    const offenders = files
      .filter((f) => rel(f) !== 'assets/main.css')
      .filter((f) => readFileSync(f, 'utf-8').includes('blur(22px) saturate(180%)'))
      .map(rel)
    expect(offenders, `胶囊材质必须来自 .glass-pill：${offenders.join(', ')}`).toEqual([])
  })

  it('T4 removes the old flat control border from the migrated controls', () => {
    for (const name of ['KBPill.vue', 'MessageInput.vue', 'Dashboard.vue']) {
      expect(read(name), `${name} 仍在声明旧平面控件边框`).not.toContain('border: 1.5px solid var(--border-strong)')
    }
  })

  it('T5 references the shared class in every migrated control', () => {
    expect(read('AgentOptions.vue')).toContain('ao-btn glass-pill')
    expect(read('TopBarOptions.vue')).toContain('to-btn glass-pill')
    expect(read('KBPill.vue')).toContain('search-capsule glass-pill')
    expect(read('MessageInput.vue')).toContain('icon-btn glass-icon-btn')
    expect(read('Dashboard.vue')).toContain('attach-btn glass-icon-btn')
    expect(read('Dashboard.vue')).toContain('prompt-chip glass-chip')
  })

  it('T6 keeps the three option capsules icon-free', () => {
    const matches = read('AgentOptions.vue').match(/<button class="ao-btn glass-pill"[^>]*>\s*<span class="ao-label"/g) || []
    expect(matches, '三个胶囊应直接以文字标签开头（前置装饰图标已移除）').toHaveLength(3)
  })

  it('T7 encodes the elevation invariant: all-raised frosted glass with an intensity gradient', () => {
    const css = readFileSync(MAIN_CSS, 'utf-8')
    const start = css.indexOf('/* ===== Control surfaces')
    const end = css.indexOf('/* =====', start + 10)
    expect(start, '未找到控件材质段').toBeGreaterThan(-1)
    const section = css.slice(start, end)

    // 方向一致：全部为凸起（顶部内高光 + 外投影），不采用凹槽（inset 0 2px）
    expect(section, '控件材质不应使用凹槽方向').not.toContain('inset 0 2px')
    for (const cls of ['.glass-input {', '.glass-pill {', '.glass-icon-btn {', '.glass-chip {']) {
      const i = section.indexOf(cls)
      expect(i, `缺少 ${cls}`).toBeGreaterThan(-1)
      const block = section.slice(i, section.indexOf('}', i))
      expect(block, `${cls} 缺少凸起顶部内高光`).toMatch(/inset 0 1px 0 rgba\(255,255,255/)
      expect(block, `${cls} 缺少外投影`).toMatch(/0 \d+px \d+px rgba\(20,18,60/)
    }

    // 强度梯度（区分度来源）：模糊半径 input > pill > chip > icon
    const blurOf = (cls) => {
      const i = section.indexOf(cls)
      const m = section.slice(i, section.indexOf('}', i)).match(/blur\((\d+)px\)/)
      expect(m, `${cls} 未声明模糊半径`).not.toBeNull()
      return Number(m[1])
    }
    const blurInput = blurOf('.glass-input {')
    const blurPill = blurOf('.glass-pill {')
    const blurChip = blurOf('.glass-chip {')
    const blurIcon = blurOf('.glass-icon-btn {')
    expect(blurInput).toBeGreaterThan(blurPill)
    expect(blurPill).toBeGreaterThan(blurChip)
    expect(blurChip).toBeGreaterThan(blurIcon)
  })

  it('T8 keeps the primary send button solid (excluded from the elevation system)', () => {
    expect(read('MessageInput.vue')).toContain('background: var(--accent)')
    expect(read('Dashboard.vue')).toContain('background: var(--accent)')
  })
})

describe('typography guard（对应 ADR-20260921-WelcomeDescOrphan）', () => {
  it('T1 keeps the landing subtitle orphan-safe', () => {
    const src = readFileSync(join(SRC, 'components', 'Dashboard.vue'), 'utf-8')
    const rule = (src.match(/\.dashboard p \{[^}]*\}/) || [])[0] || ''
    expect(rule, '未找到 .dashboard p 规则').not.toBe('')
    // 防复发核心：断行策略不得依赖具体文案长度
    expect(rule, '副标题必须声明 text-wrap: pretty 以避免孤字').toContain('text-wrap: pretty')
    const width = Number((rule.match(/max-width:\s*(\d+)px/) || [])[1])
    expect(width, '副标题宽度需留有余量（≥500px）').toBeGreaterThanOrEqual(500)
  })
})

describe('graph legend（对应 ADR-20260921-GraphLegend）', () => {
  const src = readFileSync(join(SRC, 'components', 'AgentConfigPage.vue'), 'utf-8')
  const legend = (src.match(/<div class="graph-legend[\s\S]*?<\/div>/) || [])[0] || ''

  it('T1 renders legend colors from the same source as the nodes', () => {
    expect(legend, '未找到图例块').not.toBe('')
    expect(legend, '图例颜色必须数据驱动（expertForAgent）').toContain('expertForAgent(')
  })

  it('T2 keeps the hardcoded grey dot out of the legend', () => {
    // 旧的写法：无内联样式的裸灰点表示"多色集合"，与节点配色不符
    expect(legend, '图例不得使用无样式的裸灰点').not.toMatch(/<i class="lg-dot"><\/i>/)
  })
})

describe('modal containing block（对应 ADR-20260921-ModalFixedOffset）', () => {
  const MODALS = [
    ['SkillsPage.vue', 'sp-modal'],
    ['AgentConfigPage.vue', 'form-overlay'],
    ['ModelManagerModal.vue', 'pmm-overlay'],
  ]

  it('T1 teleports every modal overlay to body', () => {
    for (const [file, cls] of MODALS) {
      const src = readFileSync(join(SRC, 'components', file), 'utf-8')
      const m = src.match(new RegExp(`<Teleport to="body">[\\s\\S]*?class="${cls}"`))
      expect(m, `${file} 的 .${cls} 必须 Teleport 到 body，否则会被页面容器的 transform 劫持定位`).not.toBeNull()
    }
  })

  it('T2 does not let the view transition leave a transform behind', () => {
    const css = readFileSync(MAIN_CSS, 'utf-8')
    const rule = (css.match(/\.main\.view-anim > \* \{[^}]*\}/) || [])[0] || ''
    expect(rule, '未找到 .main.view-anim > * 规则').not.toBe('')
    // 残留 transform 会成为 position:fixed 后代的包含块
    expect(rule, '入场动画不得使用 both/forwards 填充（会残留 transform）').not.toMatch(/\b(both|forwards)\b/)
  })
})

describe('modal backdrop-filter（对应 ADR-20260921-ModalBackdropFilter）', () => {
  const DIALOGS = ['SkillsPage.vue', 'AgentConfigPage.vue', 'ModelManagerModal.vue']

  it('T1 keeps backdrop-filter off the modal overlays', () => {
    // 遮罩层若使用 backdrop-filter 会创建 backdrop root，
    // 使卡片的后背模糊失效（弹窗发黑/发灰/杂乱）
    const stripComments = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '')
    for (const name of DIALOGS) {
      const src = stripComments(readFileSync(join(SRC, 'components', name), 'utf-8'))
      const overlays = src.match(/\.(sp-modal|form-overlay|pmm-overlay)\s*\{[^}]*\}/g) || []
      expect(overlays.length, `${name} 未找到遮罩层规则`).toBeGreaterThan(0)
      for (const block of overlays) {
        expect(block, `${name} 的遮罩层不得使用 backdrop-filter`).not.toContain('backdrop-filter')
      }
    }
  })

  it('T2 makes every modal card reference the shared .glass-dialog class', () => {
    for (const name of DIALOGS) {
      const src = readFileSync(join(SRC, 'components', name), 'utf-8')
      expect(src, `${name} 的弹窗卡片应引用 .glass-dialog`).toContain('glass-dialog')
    }
    const css = readFileSync(MAIN_CSS, 'utf-8')
    expect(css, '缺少 .glass-dialog 定义').toContain('.glass-dialog {')
  })
})
