<template>
  <div class="cm" :title="`${t('contextUsed')}: ${fmtFull(contextTokens)} / 1M`">
    <svg class="cm-ring" viewBox="0 0 20 20" width="23" height="23" aria-hidden="true">
      <defs>
        <linearGradient id="cm-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#34d399"/>
          <stop offset="100%" stop-color="#5b8def"/>
        </linearGradient>
      </defs>
      <circle class="cm-ring-track" cx="10" cy="10" r="8" fill="none" stroke-width="2.6"/>
      <circle
        class="cm-ring-fill" :class="tone"
        cx="10" cy="10" r="8" fill="none" stroke-width="2.6"
        stroke-linecap="round"
        :stroke-dasharray="CIRC" :stroke-dashoffset="offset"
        transform="rotate(-90 10 10)"
      />
    </svg>
    <span class="cm-label">{{ label }}<em>/1M</em></span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { t, contextTokens, CONTEXT_WINDOW } from '../store.js'

const CIRC = 2 * Math.PI * 8
const pct = computed(() => Math.min(100, (contextTokens.value / CONTEXT_WINDOW) * 100))
const offset = computed(() => CIRC * (1 - pct.value / 100))
const tone = computed(() => (pct.value > 85 ? 'hot' : pct.value > 60 ? 'warn' : 'ok'))
const label = computed(() => {
  const v = contextTokens.value
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M'
  if (v >= 1e3) return Math.round(v / 1e3) + 'K'
  return String(v || 0)
})
function fmtFull(v) {
  return v.toLocaleString()
}
</script>

<style scoped>
.cm { display: flex; align-items: center; gap: 6px; cursor: default; }
.cm-ring { flex-shrink: 0; }
.cm-ring-track { stroke: rgba(91,87,210,.15); }
[data-theme="dark"] .cm-ring-track { stroke: rgba(255,255,255,.12); }
.cm-ring-fill {
  stroke: url(#cm-grad);
  transition: stroke-dashoffset .6s var(--spring), stroke .3s var(--ease);
}
.cm-ring-fill.warn { stroke: #f59e0b; }
.cm-ring-fill.hot { stroke: #ef4444; }
.cm-label {
  font-size: 11px; font-weight: 650; color: var(--text-secondary);
  font-variant-numeric: tabular-nums; white-space: nowrap; letter-spacing: .2px;
  transition: color .15s var(--ease);
}
.cm:hover .cm-label { color: var(--text); }
.cm-label em { font-style: normal; color: var(--text-muted); font-weight: 500; margin-left: 2px; }
</style>
