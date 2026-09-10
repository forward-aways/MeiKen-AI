<script setup>
import { computed } from 'vue'
import { msgs, t } from '../store.js'

const emit = defineEmits(['approve'])

const live = computed(() => {
  const assistants = msgs.value.filter((m) => m.role === 'assistant')
  const m = assistants[assistants.length - 1]
  if (!m) return null
  const active = m.streaming || m.pendingApproval ||
    (m.todos && m.todos.length) || (m.toolCalls && m.toolCalls.length) ||
    (m.subagents && m.subagents.length) || (m.approvals && m.approvals.length)
  return active ? m : null
})

const phaseLabel = computed(() => {
  const p = live.value?.phase || ''
  if (p.startsWith('tool:')) return `${t('usingTool')} · ${p.slice(5)}`
  if (p.startsWith('sub:')) return `${t('runningSubagent')} · ${p.slice(4)}`
  if (p === 'thinking') return t('thinking')
  if (p === 'generating') return t('generating')
  if (p === 'approval') return t('approvalTitle')
  return ''
})

const pendingApprovals = computed(() => (live.value?.approvals || []).filter((a) => a.status === 'pending'))
const doneCount = computed(() => (live.value?.todos || []).filter((x) => x.status === 'done').length)
</script>

<template>
  <aside v-if="live" class="activity-panel glass">
    <div class="ap-title">
      <span class="ap-dot"></span>
      {{ t('activityTitle') }}
    </div>

    <div v-if="live.subagents && live.subagents.length" class="ap-section">
      <div class="ap-label">{{ t('expertCoordinating') }}</div>
      <div class="ap-subagent" v-for="(s, i) in live.subagents" :key="i">
        <span class="ap-avatar"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" stroke-linecap="round"><rect x="4" y="4" width="16" height="16" rx="4"/><circle cx="9" cy="10" r="1.6"/><path d="M7 16c.8-1.4 2.4-2 4-2s3.2.6 4 2"/></svg></span>
        <span class="ap-name">{{ s.name }}</span>
        <span class="ap-status" :class="s.status">{{ s.status === 'running' ? t('running') : t('done') }}</span>
      </div>
    </div>

    <div v-if="live.todos && live.todos.length" class="ap-section">
      <div class="ap-label">{{ t('todoList') }} ({{ doneCount }}/{{ live.todos.length }})</div>
      <div class="ap-todo" v-for="(td, i) in live.todos" :key="i" :class="{ done: td.status === 'done' }">
        <svg v-if="td.status === 'done'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="11" height="11" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11" stroke-linecap="round"><circle cx="12" cy="12" r="9"/></svg>
        <span>{{ td.title }}</span>
      </div>
    </div>

    <div v-if="live.toolCalls && live.toolCalls.length" class="ap-section">
      <div class="ap-label">{{ t('toolCalls') }}</div>
      <div class="ap-tool" v-for="(tc, i) in live.toolCalls" :key="i" :class="{ done: tc.status === 'done' }">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
        <span class="ap-tool-name">{{ tc.tool }}</span>
        <span class="ap-status" :class="tc.status">{{ tc.status === 'running' ? t('running') : t('done') }}</span>
      </div>
    </div>

    <div v-if="pendingApprovals.length" class="ap-section">
      <div class="ap-label">{{ t('approvalTitle') }}</div>
      <div class="ap-approval" v-for="a in pendingApprovals" :key="a.action_id">
        <div class="ap-tool-name">{{ a.tool }}</div>
        <pre class="ap-args">{{ JSON.stringify(a.args, null, 1).slice(0, 240) }}</pre>
        <div class="ap-actions">
          <button class="ap-btn ok" @click="emit('approve', live, a, 'approve', null, '')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            {{ t('approve') }}
          </button>
          <button class="ap-btn no" @click="emit('approve', live, a, 'reject', null, '')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            {{ t('reject') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="live.streaming && phaseLabel" class="ap-phase">{{ phaseLabel }}</div>
  </aside>
</template>

<style scoped>
.activity-panel { width: 260px; flex-shrink: 0; padding: 1rem 1rem 1.5rem; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; animation: slideInRight .35s var(--spring) both; border-left: none; border-radius: 0; box-shadow: none; }
.ap-section { animation: fadeSlide .3s var(--spring) both; }
.ap-section:nth-of-type(2) { animation-delay: 50ms; }
.ap-section:nth-of-type(3) { animation-delay: 100ms; }
.ap-section:nth-of-type(4) { animation-delay: 150ms; }
.ap-section:nth-of-type(5) { animation-delay: 200ms; }
.ap-title { display: flex; align-items: center; gap: 7px; font-size: 12.5px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: .4px; }
.ap-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: apPulse 1.4s ease-out infinite; }
@keyframes apPulse { 0% { box-shadow: 0 0 0 0 rgba(91,87,210,.45); } 70% { box-shadow: 0 0 0 6px rgba(91,87,210,0); } 100% { box-shadow: 0 0 0 0 rgba(91,87,210,0); } }
.ap-section { display: flex; flex-direction: column; gap: 6px; }
.ap-label { font-size: 11.5px; font-weight: 650; color: var(--text-muted); }
.ap-subagent, .ap-tool { display: flex; align-items: center; gap: 7px; font-size: 12.5px; color: var(--text); }
.ap-avatar { display: flex; color: var(--accent); }
.ap-name { flex: 1; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ap-tool-name { flex: 1; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ap-status { font-size: 10.5px; padding: 1px 7px; border-radius: 8px; flex-shrink: 0; }
.ap-status.running { background: var(--accent-soft); color: var(--accent); }
.ap-status.done { background: rgba(16,185,129,.12); color: #10b981; }
.ap-todo { display: flex; align-items: flex-start; gap: 6px; font-size: 12.5px; color: var(--text); line-height: 1.45; }
.ap-todo svg { flex-shrink: 0; margin-top: 2px; color: var(--accent); }
.ap-todo.done { color: var(--text-muted); text-decoration: line-through; }
.ap-todo.done svg { color: #10b981; }
.ap-approval { border: 1px solid var(--border-strong); border-radius: var(--radius); padding: 8px; display: flex; flex-direction: column; gap: 6px; background: var(--surface); }
.ap-args { font-size: 11px; color: var(--text-muted); margin: 0; max-height: 90px; overflow: auto; white-space: pre-wrap; word-break: break-all; font-family: var(--mono); }
.ap-actions { display: flex; gap: 6px; }
.ap-btn { flex: 1; display: flex; align-items: center; justify-content: center; gap: 4px; padding: 5px 0; border-radius: 7px; border: none; font-size: 12px; font-family: var(--font); cursor: pointer; transition: all .15s; }
.ap-btn.ok { background: rgba(16,185,129,.14); color: #10b981; }
.ap-btn.ok:hover { background: rgba(16,185,129,.24); }
.ap-btn.no { background: rgba(239,68,68,.12); color: #ef4444; }
.ap-btn.no:hover { background: rgba(239,68,68,.22); }
.ap-phase { font-size: 12.5px; color: var(--accent); font-weight: 600; }

@media (max-width: 1024px) {
  .activity-panel { display: none; }
}
</style>