<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { t, agents, loadAgents, setCurrentAgent, currentAgentId, graphPos, saveGraphPos } from '../store.js'
import { del } from '../api.js'
import { expertForAgent } from '../experts.js'
import AgentForm from './AgentForm.vue'

const emit = defineEmits(['close'])

const showForm = ref(false)
const formAgent = ref(null)
const hovered = ref(null)
const selected = ref(null)

const graphRef = ref(null)
const dragState = ref(null)           // { id, dx, dy, moved }
const justDragged = ref(false)

function agentSize(id) {
  if (center.value && id === center.value.id) return 88
  return ring.value.some((n) => n.agent.id === id) ? 62 : 52
}

function layoutFor(id) {
  if (center.value && id === center.value.id) return { x: CX, y: CY }
  const n = [...ring.value, ...outer.value].find((x) => x.agent.id === id)
  return n ? { x: n.x, y: n.y } : { x: CX, y: CY }
}

// Push every other node out of the way of the dragged node (dragged node never moves).
// Displaced nodes stay where they are pushed — position is user-driven.
// Threshold keeps a comfortable gap BEFORE nodes touch (Neo4j-style).
const COLLIDE_MARGIN = 40
const WOBBLE_RADIUS = 240
const WOBBLE_STRENGTH = 0.12
const WOBBLE_MAX_VEL = 0.6

function allNodeIds() {
  return [
    center.value ? center.value.id : null,
    ...ring.value.map((n) => n.agent.id),
    ...outer.value.map((n) => n.agent.id)
  ].filter(Boolean)
}

function resolveCollisions(pinnedId) {
  const me = graphPos[pinnedId]
  if (!me) return
  for (const oid of allNodeIds()) {
    if (oid === pinnedId) continue
    const p = graphPos[oid]
    if (!p) continue
    const dx = p.x - me.x
    const dy = p.y - me.y
    const d = Math.hypot(dx, dy) || 1
    const minD = (agentSize(pinnedId) + agentSize(oid)) / 2 + COLLIDE_MARGIN
    if (d < minD) {
      const nx = dx / d, ny = dy / d
      graphPos[oid] = { x: me.x + nx * minD, y: me.y + ny * minD }
    }
  }
}

// Micro-motion layer (Neo4j liveliness): dragging injects a decaying wobble
// into nearby nodes; on release the ripple settles and positions are saved.
const wob = { running: false, raf: 0, vel: {}, lastInject: null }

function injectWobble(id, gx, gy) {
  // throttle: only inject after the cursor moved enough, so micro-jiggles don't accumulate
  if (wob.lastInject) {
    const dx = gx - wob.lastInject.x
    const dy = gy - wob.lastInject.y
    if (Math.hypot(dx, dy) < 6) return
  }
  wob.lastInject = { x: gx, y: gy }
  for (const oid of allNodeIds()) {
    if (oid === id) continue
    const p = graphPos[oid]
    if (!p) continue
    const dx = gx - p.x
    const dy = gy - p.y
    const d = Math.hypot(dx, dy) || 1
    if (d < WOBBLE_RADIUS) {
      const s = (1 - d / WOBBLE_RADIUS) * WOBBLE_STRENGTH
      const v = wob.vel[oid] || (wob.vel[oid] = { x: 0, y: 0 })
      v.x = Math.max(-WOBBLE_MAX_VEL, Math.min(WOBBLE_MAX_VEL, v.x + (dx / d) * s))
      v.y = Math.max(-WOBBLE_MAX_VEL, Math.min(WOBBLE_MAX_VEL, v.y + (dy / d) * s))
    }
  }
  if (!wob.running) {
    wob.running = true
    wob.raf = requestAnimationFrame(wobbleLoop)
  }
}

function wobbleLoop() {
  let maxV = 0
  for (const id of allNodeIds()) {
    if (dragState.value && dragState.value.id === id) continue
    const v = wob.vel[id]
    if (!v) continue
    v.x *= 0.87
    v.y *= 0.87
    const p = graphPos[id]
    if (p) graphPos[id] = { x: p.x + v.x, y: p.y + v.y }
    maxV = Math.max(maxV, Math.abs(v.x), Math.abs(v.y))
  }
  if (!dragState.value && maxV < 0.02) {
    wob.running = false
    cancelAnimationFrame(wob.raf)
    saveGraphPos()
    return
  }
  wob.raf = requestAnimationFrame(wobbleLoop)
}

function posOf(n) {
  const isWrap = !!n.agent
  const id = isWrap ? n.agent.id : n.id
  const cached = graphPos[id]
  if (cached) return cached
  return isWrap ? { x: n.x, y: n.y } : { x: CX, y: CY }
}
function nodeXY(n) {
  const p = posOf(n)
  return { left: p.x / W * 100 + '%', top: p.y / H * 100 + '%' }
}

function onNodeDown(e, n) {
  if (e.button !== 0) return
  e.preventDefault()
  const id = n.agent ? n.agent.id : n.id
  dragState.value = { id, dx: 0, dy: 0, moved: false }
  const onMove = (ev) => {
    const st = dragState.value
    if (!st || st.id !== id) return
    const rect = graphRef.value ? graphRef.value.getBoundingClientRect() : null
    if (!rect) return
    const gx = (ev.clientX - rect.left) * (W / rect.width)
    const gy = (ev.clientY - rect.top) * (H / rect.height)
    st.dx += Math.abs(ev.movementX)
    st.dy += Math.abs(ev.movementY)
    if (st.dx > 3 || st.dy > 3) st.moved = true
    graphPos[id] = {
      x: Math.min(Math.max(gx, 50), W - 50),
      y: Math.min(Math.max(gy, 50), H - 50)
    }
    resolveCollisions(id)
    injectWobble(id, gx, gy)
  }
  const onUp = () => {
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
    if (dragState.value && dragState.value.moved) justDragged.value = true
    dragState.value = null
    setTimeout(() => { justDragged.value = false }, 0)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

onUnmounted(() => {
  dragState.value = null
  if (wob.running) {
    wob.running = false
    cancelAnimationFrame(wob.raf)
  }
})

const W = 900
const H = 560
const CX = W / 2
const CY = H / 2

const builtins = computed(() => agents.value.filter((a) => a.is_builtin))
const customs = computed(() => agents.value.filter((a) => !a.is_builtin))
const center = computed(() => builtins.value.find((a) => a.name === 'general') || builtins.value[0] || null)
const ringNodes = computed(() => builtins.value.filter((a) => a.id !== (center.value && center.value.id)))
const isCenterActive = computed(() => center.value && currentAgentId.value === center.value.id)

function posFor(i, n, r) {
  const angle = -Math.PI / 2 + (i * 2 * Math.PI) / Math.max(n, 1)
  return { x: CX + r * Math.cos(angle), y: CY + r * Math.sin(angle) }
}

const ring = computed(() =>
  ringNodes.value.map((a, i) => ({ agent: a, ...posFor(i, ringNodes.value.length, 168), size: 84 }))
)
const outer = computed(() =>
  customs.value.map((a, i) => ({ agent: a, ...posFor(i, customs.value.length, 252), size: 68 }))
)
const edges = computed(() => {
  const from = center.value ? posOf(center.value) : { x: CX, y: CY }
  return [...ring.value, ...outer.value].map((n) => {
    const to = posOf(n)
    return {
      agent: n.agent,
      x1: from.x, y1: from.y, x2: to.x, y2: to.y,
      color: expertForAgent(n.agent).color
    }
  })
})

const centerExpert = computed(() => (center.value ? expertForAgent(center.value) : null))
const builtinCount = computed(() => builtins.value.length)
const customCount = computed(() => customs.value.length)

const tipStyle = computed(() => {
  const h = hovered.value
  if (!h) return {}
  if (center.value && h.id === center.value.id) {
    const p = posOf(center.value)
    return { left: p.x / W * 100 + '%', top: (p.y - 70) / H * 100 + '%' }
  }
  const n = [...ring.value, ...outer.value].find((x) => x.agent.id === h.id)
  const p = n ? posOf(n) : { x: CX, y: CY }
  const y = p.y - 70 < 0 ? p.y + 70 : p.y - 70
  return { left: p.x / W * 100 + '%', top: y / H * 100 + '%' }
})

// Detail panel: anchored to the node's top-right by default; free-draggable once moved.
// Dragged positions are remembered per agent (stored as % of the canvas).
const PANEL_W = 320
const savedPanelPos = reactive(JSON.parse(localStorage.getItem('mk-detailpos') || '{}'))
const panelDrag = ref(null)        // { startX, startY, origX, origY } while dragging
const panelMoved = ref(false)

function savePanelPos() {
  localStorage.setItem('mk-detailpos', JSON.stringify(savedPanelPos))
}

const detailStyle = computed(() => {
  if (!selected.value) return {}
  const saved = savedPanelPos[selected.value.id]
  if (saved) {
    return {
      left: saved.x * 100 + '%',
      top: saved.y * 100 + '%',
      transform: 'none'
    }
  }
  const p = posOf(selected.value)
  const size = agentSize(selected.value.id)
  const gap = 14
  let left = p.x + size / 2 + gap
  let top = p.y - size / 2 - gap
  const flipX = left + PANEL_W > W - 10
  if (flipX) left = p.x - size / 2 - gap - PANEL_W
  if (top - 30 < 0) top = p.y + size / 2 + gap + 30
  return {
    left: left / W * 100 + '%',
    top: top / H * 100 + '%',
    transform: 'translateY(-100%)' + (flipX ? ' translateX(-100%)' : '')
  }
})

function onPanelDown(e) {
  if (e.button !== 0) return
  panelMoved.value = false
  panelDrag.value = {
    startX: e.clientX,
    startY: e.clientY,
    origX: e.clientX,
    origY: e.clientY,
  }
  window.addEventListener('pointermove', onPanelMove)
  window.addEventListener('pointerup', onPanelUp)
}

function onPanelMove(e) {
  const d = panelDrag.value
  if (!d) return
  if (Math.abs(e.clientX - d.origX) + Math.abs(e.clientY - d.origY) > 4) {
    panelMoved.value = true
  }
  const rect = graphRef.value.getBoundingClientRect()
  if (!rect.width || !rect.height) return
  let x = (d.origX + (e.clientX - d.startX) - rect.left) / rect.width
  let y = (d.origY + (e.clientY - d.startY) - rect.top) / rect.height
  const minX = 40 / rect.width
  const minY = 0
  const maxX = 1 - 40 / rect.width
  const maxY = 1 - 40 / rect.height
  x = Math.min(Math.max(x, minX), maxX)
  y = Math.min(Math.max(y, minY), maxY)
  savedPanelPos[selected.value.id] = { x, y }
  savePanelPos()
}

function onPanelUp() {
  panelDrag.value = null
  window.removeEventListener('pointermove', onPanelMove)
  window.removeEventListener('pointerup', onPanelUp)
}

function onPanelClose() {
  if (panelMoved.value) return
  selected.value = null
}

function select(a) {
  selected.value = a
  setCurrentAgent(a.id)
}

function isHover(a) {
  return a && hovered.value && hovered.value.id === a.id
}

function startCreate() {
  formAgent.value = null
  showForm.value = true
}

function startEdit(a) {
  formAgent.value = a
  showForm.value = true
}

async function remove(a) {
  if (!confirm(t('confirmDelAgent'))) return
  await del('/agents/' + a.id)
  await loadAgents()
  if (selected.value && selected.value.id === a.id) selected.value = null
}

function onSaved() {
  showForm.value = false
  formAgent.value = null
}

onMounted(loadAgents)
</script>

<template>
  <div class="agents-page">
    <div class="agents-head">
      <div class="agents-title">
        <h2>{{ t('expertTeam') }}</h2>
        <div class="agents-stats">
          <span>{{ t('builtin') }} <b>{{ builtinCount }}</b></span>
          <span>{{ t('custom') }} <b>{{ customCount }}</b></span>
        </div>
      </div>
      <div class="agents-actions">
        <button class="btn primary" @click="startCreate" :disabled="showForm">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          {{ t('createAgent') }}
        </button>
        <button class="btn" @click="emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          {{ t('back') }}
        </button>
      </div>
    </div>

    <div class="graph-wrap" ref="graphRef">
      <svg class="graph-edges" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none">
        <line
          v-for="(e, i) in edges"
          :key="'e' + i"
          class="graph-edge"
          :class="{ hot: isHover(e.agent) }"
          :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2"
          :stroke="e.color"
        />
      </svg>

      <!-- 图例与节点同源：颜色一律取自 expertForAgent(...)，禁止硬编码 -->
      <div class="graph-legend glass-weak">
        <span><i class="lg-dot main"></i>{{ t('mainAgent') }}</span>
        <span v-for="n in ring" :key="'lg' + n.agent.id">
          <i class="lg-dot" :style="{ background: expertForAgent(n.agent).color }"></i>{{ expertForAgent(n.agent).displayName }}
        </span>
        <span v-if="outer.length"><i class="lg-dot custom"></i>{{ t('customExperts') }}</span>
      </div>

      <div
        class="g-node g-center"
        :class="{ active: isCenterActive, hover: isHover(center), dragging: dragState && dragState.id === (center && center.id) }"
        :style="center ? nodeXY(center) : {}"
        @mousedown="center && onNodeDown($event, center)"
        @mouseenter="hovered = center"
        @mouseleave="hovered = null"
        @click="center && !justDragged && select(center)"
        :title="centerExpert && centerExpert.displayName"
      >
        <span class="g-node-icon" :style="{ '--ec': '#5b57d2' }">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22" stroke-linecap="round" stroke-linejoin="round" v-html="centerExpert ? centerExpert.icon : ''"></svg>
        </span>
        <span class="g-node-name">{{ centerExpert ? centerExpert.displayName : '' }}</span>
        <span class="g-node-role main">{{ t('mainAgent') }}</span>
      </div>

      <div
        v-for="n in ring"
        :key="'r' + n.agent.id"
        class="g-node"
        :class="{ hover: isHover(n.agent), dragging: dragState && dragState.id === n.agent.id }"
        :style="nodeXY(n)"
        @mousedown="onNodeDown($event, n)"
        @mouseenter="hovered = n.agent"
        @mouseleave="hovered = null"
        @click="!justDragged && select(n.agent)"
      >
        <span class="g-node-icon" :style="{ '--ec': expertForAgent(n.agent).color }">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round" v-html="expertForAgent(n.agent).icon"></svg>
        </span>
        <span class="g-node-name">{{ expertForAgent(n.agent).displayName }}</span>
        <span class="g-node-role">{{ t('otherExperts') }}</span>
      </div>

      <div
        v-for="n in outer"
        :key="'o' + n.agent.id"
        class="g-node g-outer"
        :class="{ hover: isHover(n.agent), dragging: dragState && dragState.id === n.agent.id }"
        :style="nodeXY(n)"
        @mousedown="onNodeDown($event, n)"
        @mouseenter="hovered = n.agent"
        @mouseleave="hovered = null"
        @click="!justDragged && select(n.agent)"
      >
        <span class="g-node-icon" :style="{ '--ec': '#8b5cf6' }">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round"><rect x="4" y="4" width="16" height="16" rx="4"/><circle cx="9" cy="10" r="1.6"/><path d="M7 16c.8-1.4 2.4-2 4-2s3.2.6 4 2"/></svg>
        </span>
        <span class="g-node-name">{{ n.agent.display_name || n.agent.name }}</span>
        <span class="g-node-role custom">{{ t('customExperts') }}</span>
      </div>

      <div v-if="hovered" class="g-tooltip glass-pop" :style="tipStyle">
        <b>{{ hovered.display_name }}</b>
        <span>{{ hovered.description || (hovered.is_builtin ? expertForAgent(hovered).tagKey ? t(expertForAgent(hovered).tagKey) : '' : 'Custom') }}</span>
      </div>

      <div v-if="selected" class="detail-panel glass-pop" :class="{ dragging: !!panelDrag }" :style="detailStyle">
        <div class="detail-head" @mousedown="onPanelDown">
          <span class="detail-icon" :style="{ '--ec': expertForAgent(selected).color }">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" stroke-linecap="round" stroke-linejoin="round" v-html="expertForAgent(selected).icon"></svg>
          </span>
          <div class="detail-title">
            <div class="detail-name">{{ selected.display_name }} <span v-if="selected.is_builtin" class="badge">{{ t('builtin') }}</span></div>
            <div class="detail-id">{{ selected.name }}</div>
          </div>
          <button class="detail-close" @mousedown.stop @click="onPanelClose">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <p class="detail-desc">{{ selected.description || '—' }}</p>
        <div class="detail-meta">
          <div><span>{{ t('model') }}</span>{{ selected.model }}</div>
          <div><span>{{ t('thinkingMode') }}</span>{{ selected.thinking ? t('thinkOn') : t('thinkOff') }}</div>
          <div><span>{{ t('reasoningEffort') }}</span>{{ selected.reasoning_effort }}</div>
          <div><span>{{ t('temperature') }}</span>{{ selected.temperature }}</div>
          <div class="span2"><span>{{ t('tools') }}</span>{{ Array.isArray(selected.tools) ? selected.tools.join(', ') : selected.tools }}</div>
        </div>
        <div class="detail-actions" v-if="!selected.is_builtin">
          <button class="btn primary" @click="startEdit(selected)">{{ t('edit') }}</button>
          <button class="btn danger-ghost" @click="remove(selected)">{{ t('del') }}</button>
        </div>
        <div v-else class="detail-readonly">{{ t('builtinReadonly') }}</div>
      </div>
    </div>

    <!-- Teleport 到 body：模态浮层不得渲染在页面容器内（容器残留的 transform
         会成为 position:fixed 的包含块，导致错位与遮罩不覆盖视口） -->
    <Teleport to="body">
    <div v-if="showForm" class="form-overlay">
      <div class="form-shell glass-dialog">
        <div class="form-title">{{ formAgent ? t('edit') : t('createAgent') }}</div>
        <AgentForm :agent="formAgent" @saved="onSaved" @cancel="showForm = false" />
      </div>
    </div>
    </Teleport>

    <div class="mobile-list">
      <div v-for="a in agents" :key="'m' + a.id" class="agent-card">
        <div class="agent-card-head">
          <div class="agent-card-title">
            <span class="agent-card-name">{{ a.display_name }}</span>
            <span v-if="a.is_builtin" class="badge">{{ t('builtin') }}</span>
          </div>
          <div class="agent-card-actions" v-if="!a.is_builtin">
            <button @click="startEdit(a)">{{ t('edit') }}</button>
            <button class="del" @click="remove(a)">{{ t('del') }}</button>
          </div>
        </div>
        <div class="agent-card-desc">{{ a.description }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agents-page { max-width: 1080px; margin: 0 auto; padding: 40px 28px 60px; width: 100%; box-sizing: border-box; }
.agents-head { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 28px; flex-wrap: wrap; gap: 16px; }
.agents-title { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; }
.agents-head h2 { font-size: 22px; font-weight: 700; margin: 0; }
.agents-actions { display: flex; gap: .5rem; }
.agents-stats { display: flex; gap: 1rem; font-size: 12px; color: var(--text-secondary); }
.agents-stats b { color: var(--accent); }

/* ===== Graph ===== */
.graph-wrap {
  position: relative; aspect-ratio: 900 / 560; max-height: 74vh; margin: 0 auto;
  animation: viewIn .4s var(--spring) both;
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  background-image:
    linear-gradient(to right, rgba(91,87,210,.05) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(91,87,210,.05) 1px, transparent 1px),
    linear-gradient(to right, rgba(91,87,210,.02) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(91,87,210,.02) 1px, transparent 1px);
  background-size: 44px 44px, 44px 44px, 11px 11px, 11px 11px;
  background-position: -1px -1px;
}
[data-theme="dark"] .graph-wrap {
  border-color: rgba(126,121,247,.14);
  background-image:
    linear-gradient(to right, rgba(126,121,247,.07) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(126,121,247,.07) 1px, transparent 1px),
    linear-gradient(to right, rgba(126,121,247,.03) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(126,121,247,.03) 1px, transparent 1px);
}
.graph-edges { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.graph-edge { stroke-width: 1.6; stroke-opacity: .3; stroke-dasharray: 5 9; animation: edgeFlow 1.1s linear infinite; transition: stroke-opacity .2s var(--ease), stroke-width .2s var(--ease); }
.graph-edge.hot { stroke-opacity: .85; stroke-width: 2.4; }
@keyframes edgeFlow { to { stroke-dashoffset: -14; } }

.g-node {
  position: absolute; transform: translate(-50%, -50%);
  width: var(--ns, 62px); height: var(--ns, 62px);
  cursor: grab; user-select: none; touch-action: none;
  transition: transform .22s var(--spring);
}
.g-node:hover { transform: translate(-50%, -50%) scale(1.08); }
.g-node.hover { transform: translate(-50%, -50%) scale(1.08); }
.g-node.dragging { cursor: grabbing; transform: translate(-50%, -50%) scale(1.12); z-index: 20; transition: none; }
.g-node.dragging .g-node-icon { box-shadow: 0 0 0 5px color-mix(in srgb, var(--ec) 22%, transparent), 0 10px 28px color-mix(in srgb, var(--ec) 26%, transparent); }
.g-node-icon {
  position: absolute; inset: 0;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background:
    var(--noise-medium),
    linear-gradient(180deg, rgba(255,255,255,.6), rgba(255,255,255,.3));
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1.5px solid rgba(255,255,255,.7);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.8), 0 6px 18px rgba(20,18,60,.1);
  color: var(--ec);
  transition: all .22s var(--spring);
}
[data-theme="dark"] .g-node-icon {
  background:
    var(--noise-medium),
    linear-gradient(180deg, rgba(44,48,72,.65), rgba(30,33,52,.45));
  border-color: rgba(255,255,255,.14);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 6px 18px rgba(0,0,0,.25);
}
.g-node:hover .g-node-icon, .g-node.hover .g-node-icon {
  border-color: var(--ec);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--ec) 18%, transparent), 0 8px 24px color-mix(in srgb, var(--ec) 22%, transparent);
}
.g-node-name {
  position: absolute; top: calc(100% + 6px); left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  font-size: 12.5px; font-weight: 650; color: var(--text);
  background: rgba(255,255,255,.55); backdrop-filter: blur(8px);
  border-radius: 8px; padding: 2px 9px;
  pointer-events: none;
}
[data-theme="dark"] .g-node-name { background: rgba(10,12,20,.5); }

.g-center { --ns: 88px; }
.g-center .g-node-icon {
  background:
    var(--noise-medium),
    linear-gradient(180deg, rgba(124,121,247,.5), rgba(91,87,210,.28));
  border-color: rgba(91,87,210,.4);
  color: #fff;
  box-shadow: 0 0 0 0 rgba(91,87,210,.45), 0 8px 26px rgba(91,87,210,.3);
  animation: centerPulse 2.6s ease-out infinite;
}
.g-center .g-node-name { font-size: 13.5px; color: var(--accent); }
.g-center.active .g-node-icon { box-shadow: 0 0 0 6px rgba(91,87,210,.16), 0 8px 26px rgba(91,87,210,.32); }
@keyframes centerPulse {
  0% { box-shadow: 0 0 0 0 rgba(91,87,210,.35), 0 8px 26px rgba(91,87,210,.3); }
  70% { box-shadow: 0 0 0 14px rgba(91,87,210,0), 0 8px 26px rgba(91,87,210,.3); }
  100% { box-shadow: 0 0 0 0 rgba(91,87,210,0), 0 8px 26px rgba(91,87,210,.3); }
}
.g-outer { --ns: 52px; }

.g-tooltip {
  position: absolute; z-index: 30; pointer-events: none;
  transform: translate(-50%, calc(-100% - 12px));
  padding: 8px 12px; border-radius: 10px;
  display: flex; flex-direction: column; gap: 2px;
  font-size: 12px; color: var(--text-secondary);
  white-space: nowrap;
}
.g-tooltip b { color: var(--text); font-size: 13px; }

.g-node-role {
  position: absolute; top: -19px; left: 50%; transform: translateX(-50%);
  font-size: 10.5px; font-weight: 600; white-space: nowrap;
  color: var(--text-muted);
  background: var(--surface);
  border: 1px solid var(--border-strong);
  padding: 1px 8px; border-radius: 999px;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  pointer-events: none;
  box-shadow: 0 1px 4px rgba(20,18,60,.08);
}
.g-node-role.main {
  color: var(--accent);
  border-color: rgba(91,87,210,.35);
  background: var(--accent-soft);
}
.g-node-role.custom {
  color: #8b5cf6;
  border-color: rgba(139,92,246,.35);
  background: color-mix(in srgb, #8b5cf6 10%, var(--surface));
}
.graph-legend {
  position: absolute; left: 12px; bottom: 12px; z-index: 5;
  display: flex; align-items: center; flex-wrap: wrap;
  gap: 6px 14px; row-gap: 4px;
  max-width: calc(100% - 24px);
  padding: 6px 12px; border-radius: 999px;
  font-size: 11.5px; font-weight: 600; color: var(--text-secondary);
  pointer-events: none;
}
.graph-legend span { display: inline-flex; align-items: center; gap: 5px; }
.lg-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--text-muted);
  display: inline-block;
}
.lg-dot.main { background: var(--accent); }
.lg-dot.custom { background: #8b5cf6; }

/* ===== Detail panel (anchored to node's top-right, flips at edges) ===== */
.detail-panel {
  position: absolute; z-index: 70;
  width: min(320px, 62vw); padding: 16px; border-radius: var(--radius-lg);
  display: flex; flex-direction: column; gap: 10px;
  animation: popIn .22s var(--spring) both;
}
.detail-panel.dragging { transition: none; animation: none; user-select: none; }
.detail-head { display: flex; align-items: center; gap: 10px; cursor: grab; }
.detail-head:active { cursor: grabbing; }
.detail-icon {
  width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: color-mix(in srgb, var(--ec) 15%, transparent); color: var(--ec);
}
.detail-title { flex: 1; min-width: 0; }
.detail-name { font-size: 15px; font-weight: 700; color: var(--text); display: flex; align-items: center; gap: 6px; }
.detail-id { font-size: 11.5px; color: var(--text-muted); font-family: var(--mono); margin-top: 1px; }
.badge { font-size: 10px; color: var(--accent); border: 1px solid var(--accent); padding: 0 6px; border-radius: 8px; }
.detail-close { width: 28px; height: 28px; border-radius: 8px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .15s; }
.detail-close:hover { background: var(--border); color: var(--text); }
.detail-desc { font-size: 13px; color: var(--text-secondary); line-height: 1.55; margin: 0; }
.detail-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; font-size: 12px; color: var(--text); }
.detail-meta .span2 { grid-column: 1 / -1; }
.detail-meta span { display: block; font-size: 10.5px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .4px; }
.detail-actions { display: flex; gap: 8px; }
.detail-actions .danger-ghost { border-color: var(--danger); color: var(--danger); }
.detail-actions .danger-ghost:hover { background: var(--danger-soft); }
.detail-readonly { font-size: 12px; color: var(--text-muted); }

/* ===== Form overlay ===== */
.form-overlay { position: fixed; inset: 0; z-index: 90; background: rgba(15,17,27,.46); display: flex; align-items: center; justify-content: center; padding: 1rem; animation: fadeIn .18s ease; }
.form-shell { width: 100%; max-width: 640px; max-height: 86vh; overflow-y: auto; border-radius: var(--radius-lg); padding: 1.4rem; animation: popIn .22s var(--spring) both; }
.form-title { font-size: 16px; font-weight: 700; margin-bottom: 1rem; }

/* ===== Mobile fallback ===== */
.mobile-list { display: none; flex-direction: column; gap: .7rem; margin-top: 1rem; }
.agent-card { border: 1px solid var(--border); border-radius: var(--radius); padding: .9rem 1rem; background: var(--surface); }
.agent-card-head { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
.agent-card-title { display: flex; align-items: center; gap: .5rem; }
.agent-card-name { font-size: 15px; font-weight: 650; color: var(--text); }
.agent-card-actions { display: flex; gap: .4rem; }
.agent-card-actions button { font-size: 12px; font-family: var(--font); padding: 3px 10px; border-radius: 7px; border: 1px solid var(--border-strong); background: transparent; color: var(--text-secondary); cursor: pointer; }
.agent-card-actions button:hover { border-color: var(--accent); color: var(--accent); }
.agent-card-actions button.del:hover { border-color: var(--danger); color: var(--danger); }
.agent-card-desc { font-size: 13px; color: var(--text-secondary); margin-top: .3rem; line-height: 1.5; }

@media (max-width: 768px) {
  .graph-wrap { display: none; }
  .mobile-list { display: flex; }
  .detail-panel { display: none; }
}
</style>