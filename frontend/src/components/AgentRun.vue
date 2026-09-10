<script setup>
import { ref, computed } from 'vue'
import { t } from '../store.js'

const props = defineProps({
  msg: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['approve'])

const editing = ref({})

const show = computed(() => {
  const m = props.msg
  return Boolean(
    (m.streaming && m.phase) ||
    (m.todos && m.todos.length) ||
    (m.subagents && m.subagents.length) ||
    (m.toolCalls && m.toolCalls.length) ||
    (m.approvals && m.approvals.filter((a) => a.status === 'pending').length)
  )
})

const phaseLabel = computed(() => {
  const p = props.msg.phase || ''
  if (p.startsWith('tool:')) return `${t('usingTool')} · ${p.slice(5)}`
  if (p.startsWith('sub:')) return `${t('runningSubagent')} · ${p.slice(4)}`
  if (p === 'thinking') return t('thinking')
  if (p === 'generating') return t('generating')
  if (p === 'approval') return t('approvalTitle')
  return ''
})

function statusLabel(s) {
  return { pending: t('pending'), in_progress: t('inProgress'), running: t('running'), completed: t('completed'), done: t('completed') }[s] || s
}

function fmtArgs(args) {
  if (!args) return ''
  try { return JSON.stringify(args, null, 1) } catch { return String(args) }
}

function doDecision(a, decision) {
  let editedArgs = null
  let message = ''
  if (decision === 'edit') {
    try { editedArgs = JSON.parse(editing.value[a.action_id] || '{}') } catch { editedArgs = a.args }
  }
  emit('approve', props.msg, a, decision, editedArgs, message)
}
</script>

<template>
  <div v-if="show" class="agent-run glass-weak">
    <div v-if="msg.streaming && msg.phase" class="phase-bar">
      <span class="phase-dot"></span>
      <span class="phase-text">{{ phaseLabel }}</span>
    </div>

    <div v-if="msg.todos && msg.todos.length" class="run-section">
      <div class="run-section-title">{{ t('todos') }}</div>
      <ul class="todo-list">
        <li v-for="(td, i) in msg.todos" :key="i" class="todo-item" :class="'st-' + (td.status || 'pending')">
          <span class="todo-icon" aria-hidden="true">
            <svg v-if="td.status === 'completed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="13" height="13" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
            <span v-else class="todo-spinner"></span>
          </span>
          <span class="todo-title">{{ td.title }}</span>
          <span class="todo-status">{{ statusLabel(td.status) }}</span>
        </li>
      </ul>
    </div>

    <div v-if="msg.subagents && msg.subagents.length" class="run-section">
      <div class="run-section-title">{{ t('subagents') }}</div>
      <div v-for="(s, i) in msg.subagents" :key="i" class="subagent-card">
        <div class="subagent-head">
          <span class="subagent-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="10" r="2"/><path d="M6.5 17c.8-1.4 2.5-2 4.5-2s3.7.6 4.5 2"/></svg></span>
          <span class="subagent-name">{{ s.name }}</span>
          <span class="subagent-status" :class="s.status">{{ statusLabel(s.status) }}</span>
        </div>
        <div v-if="s.task" class="subagent-task">{{ s.task }}</div>
      </div>
    </div>

    <div v-if="msg.toolCalls && msg.toolCalls.length" class="run-section">
      <div class="run-section-title">{{ t('tools') }}</div>
      <div v-for="(tc, i) in msg.toolCalls" :key="i" class="tool-card" :class="tc.status">
        <div class="tool-head">
          <span class="tool-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13" stroke-linecap="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg></span>
          <span class="tool-name">{{ tc.tool }}</span>
          <span class="tool-status" :class="tc.status">{{ statusLabel(tc.status) }}</span>
        </div>
        <pre v-if="tc.args && Object.keys(tc.args).length" class="tool-args">{{ fmtArgs(tc.args) }}</pre>
        <div v-if="tc.result" class="tool-result">{{ tc.result }}</div>
      </div>
    </div>

    <div v-if="msg.approvals && msg.approvals.filter((a) => a.status === 'pending').length" class="run-section">
      <div class="run-section-title">{{ t('approvalTitle') }}</div>
      <div v-for="(a, i) in msg.approvals.filter((x) => x.status === 'pending')" :key="i" class="approval-card">
        <div class="approval-head">
          <span class="approval-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" stroke-linecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></span>
          <span class="approval-tool">{{ a.tool }}</span>
        </div>
        <pre class="approval-args">{{ fmtArgs(a.args) }}</pre>
        <textarea v-if="editing[a.action_id]" v-model="editing[a.action_id]" class="approval-edit" rows="4"></textarea>
        <div class="approval-actions">
          <button class="abtn ok" @click="doDecision(a, 'approve')">{{ t('approve') }}</button>
          <button class="abtn edit" @click="editing[a.action_id] = editing[a.action_id] ? '' : fmtArgs(a.args)">{{ t('editArgs') }}</button>
          <button class="abtn no" @click="doDecision(a, 'reject')">{{ t('reject') }}</button>
          <button v-if="editing[a.action_id]" class="abtn ok" @click="doDecision(a, 'edit')">{{ t('approveEdit') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent-run { display: flex; flex-direction: column; gap: 10px; margin: 6px 0 10px; border-radius: var(--radius-lg); padding: 10px 12px; }
.phase-bar {
  display: flex; align-items: center; gap: 8px;
  font-size: 12.5px; color: var(--accent);
  animation: fadeIn .2s var(--ease);
}
.phase-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 0 rgba(91,87,210,.5);
  animation: pulse 1.4s ease-out infinite;
}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(91,87,210,.45); }
  70% { box-shadow: 0 0 0 7px rgba(91,87,210,0); }
  100% { box-shadow: 0 0 0 0 rgba(91,87,210,0); }
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.run-section { border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); padding: 8px 10px; }
.run-section-title { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: .4px; margin-bottom: 6px; }

.todo-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.todo-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-secondary); }
.todo-item.st-completed .todo-title { text-decoration: line-through; color: var(--text-muted); }
.todo-icon { display: flex; flex-shrink: 0; color: var(--accent); }
.todo-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.todo-status { font-size: 11px; color: var(--text-muted); flex-shrink: 0; }
.todo-spinner { width: 12px; height: 12px; border: 2px solid var(--border-strong); border-top-color: var(--accent); border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.subagent-card { border: 1px solid var(--border); border-radius: var(--radius); padding: 7px 9px; margin-bottom: 6px; }
.subagent-head { display: flex; align-items: center; gap: 8px; }
.subagent-icon { color: var(--accent); display: flex; }
.subagent-name { font-size: 13px; font-weight: 600; color: var(--text); flex: 1; }
.subagent-status { font-size: 11px; padding: 1px 8px; border-radius: 10px; background: var(--border); color: var(--text-muted); }
.subagent-status.done, .subagent-status.completed { background: rgba(34,197,94,.12); color: #16a34a; }
.subagent-task { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

.tool-card { border: 1px solid var(--border); border-radius: var(--radius); padding: 7px 9px; margin-bottom: 6px; }
.tool-head { display: flex; align-items: center; gap: 8px; }
.tool-icon { color: var(--accent); display: flex; }
.tool-name { font-size: 13px; font-weight: 600; color: var(--text); flex: 1; }
.tool-status { font-size: 11px; padding: 1px 8px; border-radius: 10px; background: var(--border); color: var(--text-muted); }
.tool-status.done, .tool-status.completed { background: rgba(34,197,94,.12); color: #16a34a; }
.tool-status.running { background: rgba(91,87,210,.12); color: var(--accent); }
.tool-args { margin: 6px 0 0; font-size: 11.5px; color: var(--text-secondary); background: var(--bg); border-radius: 6px; padding: 6px 8px; overflow-x: auto; }
.tool-result { margin-top: 6px; font-size: 12px; color: var(--text-muted); max-height: 120px; overflow-y: auto; white-space: pre-wrap; word-break: break-word; }

.approval-card { border: 1px solid rgba(234,179,8,.4); border-radius: var(--radius); padding: 9px; background: rgba(234,179,8,.05); }
.approval-head { display: flex; align-items: center; gap: 8px; }
.approval-icon { color: #ca8a04; display: flex; }
.approval-tool { font-size: 13px; font-weight: 600; color: var(--text); }
.approval-args { margin: 6px 0; font-size: 11.5px; color: var(--text-secondary); background: var(--bg); border-radius: 6px; padding: 6px 8px; overflow-x: auto; }
.approval-edit { width: 100%; font-family: var(--font-mono, monospace); font-size: 12px; color: var(--text); background: var(--bg); border: 1px solid var(--border-strong); border-radius: 6px; padding: 6px 8px; margin-bottom: 6px; resize: vertical; }
.approval-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.abtn { font-size: 12px; font-family: var(--font); padding: 4px 12px; border-radius: 8px; border: 1.5px solid var(--border-strong); background: transparent; color: var(--text-secondary); cursor: pointer; transition: all .15s var(--ease); }
.abtn:hover { transform: translateY(-1px); }
.abtn.ok { border-color: var(--accent); color: var(--accent); }
.abtn.ok:hover { background: rgba(91,87,210,.1); }
.abtn.no { border-color: var(--danger); color: var(--danger); }
.abtn.no:hover { background: var(--danger-soft); }
.abtn.edit { border-color: var(--border-strong); color: var(--text-muted); }
</style>