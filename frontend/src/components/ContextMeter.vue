<template>
  <div class="cm" :title="`${t('contextUsed')}: ${fmtFull(contextTokens)} / 1M`">
    <div class="cm-track">
      <div class="cm-fill" :class="tone" :style="{ width: pct + '%' }"></div>
    </div>
    <span class="cm-label">{{ label }}<em>/1M</em></span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { t, contextTokens, CONTEXT_WINDOW } from '../store.js'

const pct = computed(() => Math.min(100, (contextTokens.value / CONTEXT_WINDOW) * 100))
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
.cm { display: flex; align-items: center; gap: 7px; min-width: 128px; }
.cm-track {
  flex: 1; height: 6px; border-radius: 999px; overflow: hidden;
  border: 1px solid rgba(255,255,255,.45);
  background: linear-gradient(180deg, rgba(255,255,255,.4), rgba(255,255,255,.15));
  backdrop-filter: blur(8px) saturate(160%);
  -webkit-backdrop-filter: blur(8px) saturate(160%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.5), inset 0 1px 3px rgba(20,18,60,.08);
}
[data-theme="dark"] .cm-track {
  border-color: rgba(255,255,255,.09);
  background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.03));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.06), inset 0 1px 3px rgba(0,0,0,.3);
}
.cm-fill {
  height: 100%; border-radius: 999px;
  background: linear-gradient(90deg, #34d399, #5b8def);
  transition: width .6s var(--spring);
  box-shadow: 0 0 8px rgba(91,141,239,.45);
}
.cm-fill.warn { background: linear-gradient(90deg, #fbbf24, #f59e0b); }
.cm-fill.hot { background: linear-gradient(90deg, #f87171, #ef4444); }
.cm-label {
  font-size: 11px; font-weight: 650; color: var(--text-secondary);
  font-variant-numeric: tabular-nums; white-space: nowrap; letter-spacing: .2px;
}
.cm-label em { font-style: normal; color: var(--text-muted); font-weight: 500; margin-left: 2px; }
</style>