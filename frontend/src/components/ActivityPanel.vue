<script setup>
import { computed } from 'vue'
import { msgs, busy, t } from '../store.js'

// 可见性由"运行生命周期"决定，而不是"最后一条消息对象"的瞬时标志：
// - busy：整轮 run 期间恒为真 → 面板在运行期间稳定存在，不再随消息抖动；
// - streaming / pendingApproval：覆盖审批恢复运行与审批等待两个阶段；
// - hasActivity：该消息已产生时间线/计划，运行结束后继续保留供查看。
// 面板始终挂载，仅通过宽度过渡展开/收起，避免增删 DOM 引起的布局回流。
const live = computed(() => {
  const assistants = msgs.value.filter((m) => m.role === 'assistant')
  const m = assistants[assistants.length - 1]
  if (!m) return null
  const hasActivity = Boolean(
    (m.todos && m.todos.length) ||
    (m.toolCalls && m.toolCalls.length) ||
    (m.subagents && m.subagents.length) ||
    (m.approvals && m.approvals.length)
  )
  return (busy.value || m.streaming || m.pendingApproval || hasActivity) ? m : null
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

const doneCount = computed(() => (live.value?.todos || []).filter((x) => x.status === 'done').length)
</script>

<template>
  <aside class="activity-panel glass" :class="{ collapsed: !live }" :aria-hidden="!live">
    <div v-if="live" class="ap-inner">
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

      <div v-if="live.pendingApproval" class="ap-section">
        <div class="ap-label">{{ t('approvalTitle') }}</div>
        <div class="ap-hint">{{ t('approvalInTimeline') }}</div>
      </div>

      <div v-if="phaseLabel" class="ap-phase">{{ phaseLabel }}</div>
    </div>
  </aside>
</template>

<style scoped>
/* 顶部留出固定顶栏高度，避免内容被顶栏遮挡（与 .sidebar / .main 一致） */
.activity-panel {
  width: 260px; flex-shrink: 0; padding-top: 52px; overflow: hidden;
  display: flex; flex-direction: column;
  border-left: none; border-radius: 0; box-shadow: none;
  z-index: 10;
  transition: width .3s var(--spring), opacity .22s var(--ease);
}
.activity-panel.collapsed { width: 0; opacity: 0; pointer-events: none; }
.ap-inner {
  width: 260px; flex: 1; min-height: 0; overflow-y: auto;
  padding: 0 1rem 1.5rem; display: flex; flex-direction: column; gap: 14px;
}
.ap-section { animation: fadeSlide .3s var(--spring) both; }
.ap-section:nth-of-type(2) { animation-delay: 50ms; }
.ap-section:nth-of-type(3) { animation-delay: 100ms; }
.ap-section:nth-of-type(4) { animation-delay: 150ms; }
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
.ap-hint { font-size: 12px; color: var(--text-muted); line-height: 1.5; }
.ap-phase { font-size: 12.5px; color: var(--accent); font-weight: 600; }

@media (max-width: 1024px) {
  .activity-panel { display: none; }
}
</style>
