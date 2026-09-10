<script setup>
import { computed } from 'vue'
import { t, agents, currentAgent, currentAgentId, setCurrentAgent, setView } from '../store.js'
import { EXPERTS, expertForAgent } from '../experts.js'

const selected = computed(() => currentAgent())
const selectedExpert = computed(() => expertForAgent(selected.value))

function choose(name) {
  const a = agents.value.find((x) => x.name === name)
  if (a) setCurrentAgent(a.id)
}
</script>

<template>
  <div class="expert-bar">
    <div class="expert-strip">
      <button
        v-for="e in EXPERTS"
        :key="e.agentName"
        class="expert-avatar"
        :class="{ active: selectedExpert && selectedExpert.agentName === e.agentName }"
        :style="{ '--ec': e.color }"
        :title="t(e.titleKey) + ' — ' + t(e.tagKey)"
        @click="choose(e.agentName)"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15" stroke-linecap="round" stroke-linejoin="round" v-html="e.icon"></svg>
      </button>
    </div>
    <span v-if="selectedExpert" class="expert-label">{{ selectedExpert.titleKey ? t(selectedExpert.titleKey) : selectedExpert.displayName }}</span>
    <button class="expert-add" :title="t('manageAgents')" @click="setView('agents')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
    </button>
  </div>
</template>

<style scoped>
.expert-bar { display: flex; align-items: center; gap: 8px; }
.expert-strip {
  display: flex; align-items: center; gap: 5px; padding: 3px 6px; border-radius: 14px;
  border: 1px solid rgba(255,255,255,.55);
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.04'/></svg>"),
    linear-gradient(180deg, rgba(255,255,255,.42), rgba(255,255,255,.2));
  backdrop-filter: blur(18px) saturate(180%);
  -webkit-backdrop-filter: blur(18px) saturate(180%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.6);
}
[data-theme="dark"] .expert-strip {
  border-color: rgba(255,255,255,.09);
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.05'/></svg>"),
    linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.025));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08);
}
.expert-avatar {
  width: 27px; height: 27px; border-radius: 50%; border: 2px solid transparent;
  display: flex; align-items: center; justify-content: center;
  background: color-mix(in srgb, var(--ec) 14%, transparent);
  color: var(--ec); cursor: pointer; padding: 0;
  transition: all .2s var(--ease);
}
.expert-avatar:hover { transform: translateY(-1px) scale(1.05); }
.expert-avatar.active { border-color: var(--ec); background: color-mix(in srgb, var(--ec) 22%, transparent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ec) 18%, transparent); }
.expert-label { font-size: 14px; font-weight: 650; color: var(--text); max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.expert-add { width: 27px; height: 27px; border-radius: 50%; border: 1.5px dashed var(--border-strong); background: transparent; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .18s var(--ease); flex-shrink: 0; }
.expert-add:hover { color: var(--accent); border-color: var(--accent); }

@media (max-width: 768px) {
  .expert-strip { overflow-x: auto; max-width: 150px; scrollbar-width: none; }
  .expert-strip::-webkit-scrollbar { display: none; }
}
</style>