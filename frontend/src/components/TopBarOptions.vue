<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  t, currentAgent, modelOverride, thinkMode, effortSel, modelGroups,
  setModelOverride, setThinkMode, setEffortSel
} from '../store.js'
import ContextMeter from './ContextMeter.vue'
import ModelManagerModal from './ModelManagerModal.vue'

const openWhich = ref(false)
const menuRef = ref(null)
const manageOpen = ref(false)
const activeGroupId = ref(null)
const flyoutPos = ref({ top: 0, left: 0 })
const activeGroup = computed(() => modelGroups.value.find((g) => g.id === activeGroupId.value) || null)

const modelLabel = computed(() => {
  if (!modelOverride.value) return t('followAgent')
  return modelOverride.value
})

const activeModel = computed(() => modelOverride.value || (currentAgent() || {}).model)

function thinkModeKey(v) { return { fast: 'thinkFast', standard: 'thinkStandard', deep: 'thinkDeep' }[v] || 'thinkStandard' }
function effortKey(v) { return { off: 'effOff', low: 'effLow', mid: 'effMid', high: 'effHigh' }[v] || 'effMid' }
function effortDescKey(v) { return { off: 'effOffDesc', low: 'effLowDesc', mid: 'effMidDesc', high: 'effHighDesc' }[v] || 'effMidDesc' }
function thinkDescKey(v) { return { fast: 'thinkFastDesc', standard: 'thinkStandardDesc', deep: 'thinkDeepDesc' }[v] || 'thinkStandardDesc' }

function mDesc(m, g) {
  if (g.name === 'DeepSeek' && g.is_builtin) {
    if (m.name === 'deepseek-flash') return t('modelFlash11Desc')
    if (m.name === 'deepseek-v4-flash') return t('modelFlashDesc')
    if (m.name === 'deepseek-v4-pro') return t('modelProDesc')
  }
  return g.deepseek_compat ? t('deepseekStyle') : t('standardStyle')
}

function groupSub(g) {
  if (modelOverride.value && g.models.some((m) => m.name === modelOverride.value)) {
    return '✓ ' + modelOverride.value
  }
  let s = t('modelsCount').replace('{n}', g.models.length)
  if (!g.key_configured) s += ' · ' + t('keyNotSetShort')
  return s
}

function toggle() {
  openWhich.value = !openWhich.value
  activeGroupId.value = null
}

function pickModel(m) {
  setModelOverride(m)
  openWhich.value = false
  activeGroupId.value = null
}

const FLYOUT_W = 248

function openGroup(g, e) {
  if (activeGroupId.value === g.id) {   // click again to collapse the flyout
    activeGroupId.value = null
    return
  }
  activeGroupId.value = g.id
  const el = e && e.currentTarget
  if (el) {
    const r = el.getBoundingClientRect()
    const flip = r.right + FLYOUT_W + 12 > window.innerWidth
    flyoutPos.value = {
      top: Math.max(8, Math.min(r.top, window.innerHeight - 280)),
      left: flip ? Math.max(8, r.left - FLYOUT_W - 6) : r.right + 6,
    }
  }
}

function backGroups() {
  activeGroupId.value = null
}

function closeFlyout() {
  if (activeGroupId.value) activeGroupId.value = null
}

function openManage() {
  openWhich.value = false
  activeGroupId.value = null
  manageOpen.value = true
}

function handleClickOutside(e) {
  if (menuRef.value && !menuRef.value.contains(e.target)) openWhich.value = false
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  window.addEventListener('scroll', closeFlyout, true)
  window.addEventListener('resize', closeFlyout)
})
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('scroll', closeFlyout, true)
  window.removeEventListener('resize', closeFlyout)
})
</script>

<template>
  <div class="to-wrap" ref="menuRef">
    <div class="to-cap-wrap">
      <button
        class="to-btn"
        :class="{ active: openWhich || modelOverride || thinkMode !== 'fast' || effortSel !== 'mid' }"
        @click="toggle"
        :title="t('model')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
        <span class="to-label">{{ modelLabel }}</span>
        <svg class="to-chev" :class="{ open: openWhich }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="10" height="10" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
      </button>

      <div v-if="openWhich" class="to-menu">
        <div class="to-group-title">{{ t('model') }}</div>
        <div class="to-list">
          <button class="to-item" :class="{ on: !modelOverride }" @click="pickModel(null)">
            <span class="to-item-main">
              <span class="to-item-label">{{ t('followAgent') }}</span>
              <span class="to-item-sub">{{ activeModel }}</span>
            </span>
            <svg v-if="!modelOverride" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          </button>
          <button v-for="g in modelGroups" :key="g.id" class="to-item" :class="{ on: activeGroupId === g.id }" @click="openGroup(g, $event)">
            <span class="to-item-main">
              <span class="to-item-label">{{ g.name }}<span v-if="g.is_builtin" class="to-g-badge">{{ t('builtinProvider') }}</span></span>
              <span class="to-item-sub">{{ groupSub(g) }}</span>
            </span>
            <svg class="to-chev-r" :class="{ down: activeGroupId === g.id }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>
        <div class="to-add">
          <button class="to-add-btn" @click="openManage">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            {{ t('manageModels') }}
          </button>
        </div>

        <!-- Second-level flyout: models of the clicked provider -->
        <Teleport to="body">
          <div
            v-if="openWhich && activeGroup"
            class="to-flyout"
            :style="{ top: flyoutPos.top + 'px', left: flyoutPos.left + 'px' }"
          >
            <div class="to-flyout-head">{{ activeGroup.name }}</div>
            <button v-for="m in activeGroup.models" :key="m.name" class="to-item" :class="{ on: modelOverride === m.name }" @click="pickModel(m.name)">
              <span class="to-item-main">
                <span class="to-item-label">{{ m.name }}</span>
                <span class="to-item-sub">{{ mDesc(m, activeGroup) }}</span>
              </span>
              <svg v-if="modelOverride === m.name" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </button>
          </div>
        </Teleport>

        <div class="to-divider"></div>

        <div class="to-group-title">{{ t('thinkingMode') }}</div>
        <div class="to-list">
          <button v-for="v in ['fast', 'standard', 'deep']" :key="v" class="to-item" :class="{ on: thinkMode === v && effortSel !== 'off' }" @click="setThinkMode(v)">
            <span class="to-item-main">
              <span class="to-item-label">{{ t(thinkModeKey(v)) }}</span>
              <span class="to-item-sub">{{ t(thinkDescKey(v)) }}</span>
            </span>
            <svg v-if="thinkMode === v && effortSel !== 'off'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          </button>
        </div>

        <div class="to-divider"></div>

        <div class="to-group-title">{{ t('reasoningEffort') }}</div>
        <div class="to-list">
          <button v-for="v in ['off', 'low', 'mid', 'high']" :key="v" class="to-item" :class="{ on: effortSel === v }" @click="setEffortSel(v)">
            <span class="to-item-main">
              <span class="to-item-label">{{ t(effortKey(v)) }}</span>
              <span class="to-item-sub">{{ t(effortDescKey(v)) }}</span>
            </span>
            <svg v-if="effortSel === v" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          </button>
        </div>
      </div>
    </div>

    <ContextMeter />
    <ModelManagerModal v-if="manageOpen" @close="manageOpen = false" />
  </div>
</template>

<style scoped>
.to-wrap { display: flex; align-items: center; gap: 10px; flex-wrap: nowrap; }
.to-cap-wrap { position: relative; }
.to-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 11px; border-radius: 999px;
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.05'/></svg>"),
    linear-gradient(180deg, rgba(255,255,255,.62), rgba(255,255,255,.4));
  backdrop-filter: blur(22px) saturate(180%);
  -webkit-backdrop-filter: blur(22px) saturate(180%);
  border: 1px solid rgba(255,255,255,.7);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.75), 0 2px 8px rgba(20,18,60,.06);
  color: var(--text-secondary); font-size: 12px; font-family: var(--font);
  cursor: pointer; transition: all .2s var(--ease); white-space: nowrap; line-height: 1.4;
}
.to-btn:hover { transform: translateY(-1px); color: var(--text); border-color: rgba(91,87,210,.3); }
.to-btn:active { transform: scale(.95); transition-duration: .08s; }
.to-btn.active { color: var(--accent); border-color: rgba(91,87,210,.4); box-shadow: inset 0 1px 0 rgba(255,255,255,.8), 0 2px 10px rgba(91,87,210,.14); }
[data-theme="dark"] .to-btn {
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.05'/></svg>"),
    linear-gradient(180deg, rgba(44,48,72,.7), rgba(30,33,52,.5));
  border-color: rgba(255,255,255,.12);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 2px 8px rgba(0,0,0,.22);
}
.to-label { max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
.to-chev { color: var(--text-muted); transition: transform .2s var(--ease); flex-shrink: 0; }
.to-chev.open { transform: rotate(180deg); }

/* Acrylic dropdown: near-solid base (no text bleed), blurry edges, tactile depth */
.to-menu {
  position: absolute; top: calc(100% + 8px); right: 0; z-index: 70;
  width: 292px;
  max-height: min(560px, calc(100vh - 76px));
  overflow-y: auto;
  border-radius: 14px;
  padding: 10px;
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.04'/></svg>"),
    linear-gradient(180deg, rgba(255,255,255,.99), rgba(246,245,255,.975));
  backdrop-filter: blur(36px) saturate(180%);
  -webkit-backdrop-filter: blur(36px) saturate(180%);
  border: 1px solid rgba(255,255,255,.95);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,1),
    inset 0 -1px 0 rgba(20,18,60,.05),
    0 1px 2px rgba(20,18,60,.06),
    0 8px 20px rgba(20,18,60,.12),
    0 22px 48px rgba(20,18,60,.16);
  animation: toIn .18s var(--spring) both;
}
[data-theme="dark"] .to-menu {
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.04'/></svg>"),
    linear-gradient(180deg, rgba(50,54,82,.99), rgba(36,39,62,.975));
  border-color: rgba(255,255,255,.14);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.1),
    inset 0 -1px 0 rgba(0,0,0,.35),
    0 1px 2px rgba(0,0,0,.25),
    0 10px 24px rgba(0,0,0,.35),
    0 26px 56px rgba(0,0,0,.45);
}
@keyframes toIn { from { opacity: 0; transform: translateY(-8px) scale(.97); } to { opacity: 1; transform: translateY(0) scale(1); } }

.to-group-title { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: .4px; margin: 8px 0 4px; padding: 0 2px; }
.to-group-title:first-child { margin-top: 0; }
.to-group-name { display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 650; color: var(--text-muted); text-transform: uppercase; letter-spacing: .4px; margin: 6px 2px 2px; }
.to-group-name:first-of-type { margin-top: 0; }
.to-g-badge { font-size: 9.5px; font-weight: 700; text-transform: none; padding: 1px 6px; border-radius: 999px; background: rgba(91,87,210,.1); color: var(--accent); letter-spacing: 0; margin-left: 6px; }
.to-chev-r { color: var(--text-muted); flex-shrink: 0; transition: transform .2s var(--ease); }
.to-chev-r.down { transform: rotate(90deg); color: var(--accent); }

/* Second-level flyout — fixed so it escapes menu clipping, auto left/right */
.to-flyout {
  position: fixed; z-index: 96;
  width: 248px;
  border-radius: 14px;
  padding: 10px;
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.04'/></svg>"),
    linear-gradient(180deg, rgba(255,255,255,.99), rgba(246,245,255,.975));
  backdrop-filter: blur(36px) saturate(180%);
  -webkit-backdrop-filter: blur(36px) saturate(180%);
  border: 1px solid rgba(255,255,255,.95);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,1),
    inset 0 -1px 0 rgba(20,18,60,.05),
    0 1px 2px rgba(20,18,60,.06),
    0 8px 20px rgba(20,18,60,.12),
    0 22px 48px rgba(20,18,60,.16);
  animation: toFlyIn .16s var(--spring) both;
}
[data-theme="dark"] .to-flyout {
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.04'/></svg>"),
    linear-gradient(180deg, rgba(50,54,82,.99), rgba(36,39,62,.975));
  border-color: rgba(255,255,255,.14);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.1),
    inset 0 -1px 0 rgba(0,0,0,.35),
    0 1px 2px rgba(0,0,0,.25),
    0 10px 24px rgba(0,0,0,.35),
    0 26px 56px rgba(0,0,0,.45);
}
.to-flyout-head {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; font-weight: 650; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: .4px;
  margin: 2px 4px 6px;
}
@keyframes toFlyIn { from { opacity: 0; transform: scale(.97); } to { opacity: 1; transform: scale(1); } }
.to-back { color: var(--text-muted); font-weight: 600; }
.to-back .to-item-label { font-size: 12px; color: var(--text-muted); }
.to-list { display: flex; flex-direction: column; gap: 2px; }
.to-divider { height: 1px; background: var(--border); margin: 8px 2px; }
.to-item {
  display: flex; align-items: center; gap: 10px;
  padding: 7px 9px; border: none; border-radius: 9px;
  background: transparent; color: var(--text-secondary);
  font-size: 12.5px; font-family: var(--font); cursor: pointer;
  transition: all .15s var(--ease); text-align: left; width: 100%;
}
.to-item:hover { background: rgba(91,87,210,.08); }
.to-item.on { background: rgba(91,87,210,.14); color: var(--accent); }
.to-item-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.to-item-label { font-weight: 650; color: var(--text); font-size: 13px; }
.to-item.on .to-item-label { color: var(--accent); }
.to-item-sub { font-size: 11px; color: var(--text-muted); line-height: 1.4; }
.to-item.on .to-item-sub { color: color-mix(in srgb, var(--accent) 55%, transparent); }
.to-item svg { flex-shrink: 0; color: var(--accent); }

.to-add { margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border); display: flex; gap: 6px; }
.to-add-btn {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 5px;
  padding: 6px 0; border: 1px dashed var(--border-strong); border-radius: 8px;
  background: transparent; color: var(--text-secondary); font-size: 12px;
  font-family: var(--font); cursor: pointer; transition: all .15s var(--ease);
}
.to-add-btn:hover { border-color: var(--accent); color: var(--accent); }
.to-add-input {
  flex: 1; min-width: 0; padding: 5px 8px; border-radius: 8px;
  border: 1px solid var(--border-strong); background: var(--surface);
  color: var(--text); font-size: 12px; font-family: var(--font); outline: none;
}
.to-add-input:focus { border-color: var(--accent); }
.to-add-confirm {
  padding: 5px 12px; border: none; border-radius: 8px;
  background: var(--accent); color: #fff; font-size: 12px; font-weight: 600;
  font-family: var(--font); cursor: pointer;
}

@media (max-width: 768px) {
  .to-btn { padding: 4px 8px; font-size: 11px; }
  .to-label { max-width: 110px; }
  .to-menu { width: min(292px, calc(100vw - 24px)); }
}
</style>