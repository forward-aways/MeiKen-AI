<script setup>
import { ref, computed } from 'vue'
import { t } from '../store.js'

const props = defineProps({
  msg: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['approve'])

const editing = ref({})
const opened = ref({})
const showInterim = ref(false)

function toolLabel(name) {
  if (name === 'web_search') return t('toolSearch')
  if (name === 'knowledge_search') return t('toolKbSearch')
  return name
}

function subLabel(name) {
  return { researcher: t('subResearcher'), analyst: t('subAnalyst') }[name] || name
}

function isRunning(step) {
  return step.status === 'running' || step.status === 'in_progress' || step.status === 'pending'
}

function dedupeSources(list) {
  const seen = new Set()
  const out = []
  for (const s of list || []) {
    const k = s.url || s.title
    if (k && !seen.has(k)) { seen.add(k); out.push(s) }
  }
  return out
}

// Unified execution timeline in event order; consecutive calls of the same
// tool merge into one compact step (e.g. "Web search × 7").
const steps = computed(() => {
  const m = props.msg
  const raw = []
  for (const tc of m.toolCalls || []) {
    raw.push({ kind: 'tool', key: tc.id || 't' + (tc.seq || 0), seq: tc.seq || 0, ...tc })
  }
  for (const s of m.subagents || []) {
    raw.push({ kind: 'sub', key: 's' + (s.seq || 0), seq: s.seq || 0, ...s })
  }
  raw.sort((a, b) => a.seq - b.seq)

  const out = []
  for (const step of raw) {
    const last = out[out.length - 1]
    if (step.kind === 'tool' && last && last.kind === 'tool' && last.tool === step.tool) {
      last.calls.push(step)
      last.count = last.calls.length
      last.running = last.running || isRunning(step)
      last.status = last.running ? 'running' : 'done'
      last.sources = dedupeSources(last.sources.concat(step.sources || []))
    } else {
      out.push({
        kind: step.kind,
        key: step.key,
        tool: step.tool,
        name: step.name,
        task: step.task,
        args: step.args,
        result: step.result,
        status: step.status,
        running: isRunning(step),
        count: 1,
        calls: [step],
        sources: dedupeSources(step.sources || []),
      })
    }
  }
  return out
})

const show = computed(() => {
  const m = props.msg
  return Boolean(
    (m.interim && m.interim.length) ||
    (m.todos && m.todos.length) ||
    steps.value.length ||
    (m.approvals && m.approvals.filter((a) => a.status === 'pending').length)
  )
})

function hostOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url || '' }
}

const doneTodos = computed(() => (props.msg.todos || []).filter((td) => td.status === 'completed').length)

function stepTitle(step) {
  if (step.kind === 'sub') {
    return isRunning(step) ? `${subLabel(step.name)} · ${t('running')}…` : subLabel(step.name)
  }
  const base = toolLabel(step.tool)
  if (isRunning(step)) return `${t('callingTool')} ${base}…`
  return step.count > 1 ? `${base} × ${step.count}` : base
}

function hasSources(step) {
  return step.sources && step.sources.length > 0
}

function queries(step) {
  return (step.calls || []).map((c) => c.args && c.args.query).filter(Boolean)
}

function lastResult(step) {
  const calls = step.calls || []
  const last = calls[calls.length - 1]
  return (last && last.result) || ''
}

function stepSummary(step) {
  if (isRunning(step)) return ''
  if (step.kind === 'sub') return t('completed')
  if (hasSources(step)) {
    return step.tool === 'knowledge_search'
      ? `${step.sources.length} ${t('kbFilesCount')}`
      : `${step.sources.length} ${t('sources')}`
  }
  return ''
}

function toggle(step) { opened.value[step.key] = !opened.value[step.key] }
function isOpen(step) { return !!opened.value[step.key] }

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
  <div v-if="show" class="agent-trace">
    <!-- Process notes: talk the model emitted before tool rounds (collapsed) -->
    <div v-if="msg.interim && msg.interim.length" class="trace-interim">
      <button class="interim-toggle" @click="showInterim = !showInterim">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
        <span>{{ t('processNotes') }}</span>
        <span class="interim-count">{{ msg.interim.length }}</span>
        <svg class="interim-chev" :class="{ open: showInterim }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
      </button>
      <div v-if="showInterim" class="interim-body">
        <p v-for="(txt, i) in msg.interim" :key="i">{{ txt }}</p>
      </div>
    </div>

    <!-- Plan -->
    <div v-if="msg.todos && msg.todos.length" class="trace-todos">
      <div class="trace-todos-title">
        <span>{{ t('todos') }}</span>
        <span class="todos-count">{{ doneTodos }}/{{ msg.todos.length }}</span>
      </div>
      <ul class="todo-list">
        <li v-for="(td, i) in msg.todos" :key="i" class="todo-item" :class="'st-' + (td.status || 'pending')">
          <span class="todo-icon" aria-hidden="true">
            <svg v-if="td.status === 'completed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
            <span v-else class="todo-spinner"></span>
          </span>
          <span class="todo-title">{{ td.title }}</span>
        </li>
      </ul>
    </div>

    <!-- Execution timeline -->
    <div v-if="steps.length" class="trace-steps">
      <div v-for="step in steps" :key="step.key" class="trace-step" :class="[step.kind, { running: isRunning(step) }]">
        <span class="tr-dot" :class="{ done: !isRunning(step) }">
          <svg v-if="!isRunning(step)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" width="8" height="8" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          <span v-else class="tr-spin"></span>
        </span>

        <div class="tr-main" :class="{ 'activity-glass glass-sweep': isRunning(step) }">
          <button class="tr-head" @click="toggle(step)">
            <span class="tr-ico">
              <svg v-if="step.kind === 'sub'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="10" r="2"/><path d="M6.5 17c.8-1.4 2.5-2 4.5-2s3.7.6 4.5 2"/></svg>
              <svg v-else-if="step.tool === 'web_search'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <svg v-else-if="step.tool === 'knowledge_search'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13" stroke-linecap="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
            </span>
            <span class="tr-title" :class="{ 'shine-text': isRunning(step) }">{{ stepTitle(step) }}</span>
            <span v-if="stepSummary(step)" class="tr-summary">{{ stepSummary(step) }}</span>
            <svg class="tr-chev" :class="{ open: isOpen(step) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
          </button>

          <div v-if="isOpen(step)" class="tr-body">
            <!-- Web search: source cards -->
            <div v-if="step.kind === 'tool' && step.tool === 'web_search' && hasSources(step)" class="tool-sources">
              <a v-for="(s, j) in step.sources" :key="j" class="tool-source" :href="s.url" target="_blank" rel="noopener">
                <span class="src-idx">{{ String(j + 1).padStart(2, '0') }}</span>
                <span class="src-main">
                  <span class="src-title">{{ s.title || hostOf(s.url) }}</span>
                  <span v-if="s.snippet" class="src-snippet">{{ s.snippet }}</span>
                  <span class="src-foot">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="10" height="10" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    <span class="src-host">{{ hostOf(s.url) }}</span>
                  </span>
                </span>
              </a>
            </div>
            <!-- Knowledge base: matched files -->
            <div v-else-if="step.kind === 'tool' && step.tool === 'knowledge_search' && hasSources(step)" class="tool-kb">
              <span v-for="(s, j) in step.sources" :key="j" class="kb-file">{{ s.title }}</span>
            </div>
            <!-- Subagent task -->
            <div v-if="step.kind === 'sub' && step.task" class="sub-task">{{ step.task }}</div>
            <!-- Tool technical details -->
            <template v-if="step.kind === 'tool'">
              <template v-if="step.count > 1">
                <div v-if="queries(step).length" class="tool-queries">
                  <span v-for="(q, j) in queries(step)" :key="j" class="tq-chip">{{ q }}</span>
                </div>
                <div v-if="!hasSources(step) && lastResult(step)" class="tool-result">{{ lastResult(step) }}</div>
              </template>
              <template v-else>
                <pre v-if="step.args && Object.keys(step.args).length" class="tool-args">{{ fmtArgs(step.args) }}</pre>
                <div v-if="step.result && !hasSources(step)" class="tool-result">{{ step.result }}</div>
              </template>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- Approval requests -->
    <div v-if="msg.approvals && msg.approvals.filter((a) => a.status === 'pending').length" class="approval-section">
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
.agent-trace { display: flex; flex-direction: column; gap: 10px; margin: 6px 0 12px; }

/* ---- Plan (todos) ---- */
.trace-todos { border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); padding: 8px 10px; }
.trace-todos-title { display: flex; align-items: center; justify-content: space-between; font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: .4px; margin-bottom: 6px; }
.todos-count { font-weight: 700; color: var(--accent); letter-spacing: 0; }
.todo-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.todo-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-secondary); }
.todo-item.st-completed .todo-title { text-decoration: line-through; color: var(--text-muted); }
.todo-icon { display: flex; flex-shrink: 0; color: #16a34a; }
.todo-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.todo-spinner { width: 11px; height: 11px; border: 2px solid var(--border-strong); border-top-color: var(--accent); border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ---- Execution timeline ---- */
.trace-steps { display: flex; flex-direction: column; }
.trace-step { position: relative; padding-left: 24px; padding-bottom: 6px; }
.trace-step:last-child { padding-bottom: 0; }
.trace-step:not(:last-child)::before {
  content: ''; position: absolute; left: 5.5px; top: 19px; bottom: 0; width: 1.5px;
  background: var(--border-strong); opacity: .5; border-radius: 1px;
}
.tr-dot {
  position: absolute; left: 0; top: 5px; width: 13px; height: 13px;
  display: flex; align-items: center; justify-content: center; border-radius: 50%;
}
.tr-dot.done { background: rgba(34,197,94,.16); color: #16a34a; }
.tr-spin {
  width: 13px; height: 13px; border-radius: 50%;
  border: 2px solid rgba(91,87,210,.22); border-top-color: var(--accent);
  animation: spin .7s linear infinite;
}

.tr-main { border-radius: 10px; transition: background .15s var(--ease), border-color .15s var(--ease); }
.tr-head {
  display: flex; align-items: center; gap: 8px; width: 100%;
  padding: 5px 9px; border: none; border-radius: 10px;
  background: transparent; color: inherit; font-family: var(--font);
  cursor: pointer; text-align: left; position: relative; z-index: 1;
}
.tr-head:hover { background: rgba(91,87,210,.06); }
.trace-step.running .tr-head:hover { background: transparent; }
.tr-ico { display: flex; color: var(--text-muted); flex-shrink: 0; }
.trace-step.running .tr-ico { color: var(--accent); }
.tr-title {
  font-size: 13px; font-weight: 600;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tr-summary { margin-left: auto; font-size: 11.5px; color: var(--text-muted); white-space: nowrap; }
.tr-chev { color: var(--text-muted); flex-shrink: 0; transition: transform .18s var(--ease); }
.tr-chev.open { transform: rotate(180deg); }

.tr-body { padding: 2px 9px 8px; position: relative; z-index: 1; animation: fadeIn .15s var(--ease); }
.sub-task { font-size: 12px; color: var(--text-secondary); line-height: 1.55; }

/* ---- Source cards (e.g. web search results) ---- */
.tool-sources { display: flex; flex-direction: column; gap: 6px; }
.tool-source {
  display: flex; gap: 10px; padding: 10px 12px;
  border: 1px solid var(--border); border-radius: 11px;
  background: linear-gradient(180deg, rgba(255,255,255,.6), rgba(255,255,255,.3));
  text-decoration: none;
  transition: border-color .16s var(--ease), background .16s var(--ease), transform .16s var(--ease), box-shadow .16s var(--ease);
}
.tool-source:hover {
  border-color: rgba(91,87,210,.4);
  background: linear-gradient(180deg, rgba(255,255,255,.85), rgba(255,255,255,.5));
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(91,87,210,.12);
}
[data-theme="dark"] .tool-source { background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02)); }
[data-theme="dark"] .tool-source:hover { background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.04)); box-shadow: 0 4px 14px rgba(0,0,0,.3); }
.src-idx {
  flex-shrink: 0; width: 22px; height: 22px; border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
  font-size: 10.5px; font-weight: 700; font-variant-numeric: tabular-nums;
  background: rgba(91,87,210,.1); color: var(--accent);
}
.src-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.src-title {
  font-size: 12.5px; font-weight: 600; color: var(--text); line-height: 1.45;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.tool-source:hover .src-title { color: var(--accent); }
.src-snippet {
  font-size: 11.5px; color: var(--text-secondary); line-height: 1.55;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.src-foot { display: flex; align-items: center; gap: 4px; margin-top: 1px; }
.src-foot svg { color: var(--text-muted); flex-shrink: 0; }
.src-host { font-size: 10.5px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ---- Process notes (collapsed talk between tool rounds) ---- */
.trace-interim { }
.interim-toggle {
  display: flex; align-items: center; gap: 7px;
  padding: 4px 9px; border: none; border-radius: 9px;
  background: transparent; color: var(--text-muted);
  font-size: 12px; font-family: var(--font); cursor: pointer;
  transition: background .15s var(--ease), color .15s var(--ease);
}
.interim-toggle:hover { background: rgba(91,87,210,.06); color: var(--text-secondary); }
.interim-toggle svg { flex-shrink: 0; }
.interim-count {
  font-size: 10.5px; font-weight: 700; padding: 1px 7px; border-radius: 999px;
  background: var(--border); color: var(--text-muted); font-variant-numeric: tabular-nums;
}
.interim-chev { transition: transform .18s var(--ease); margin-left: auto; }
.interim-chev.open { transform: rotate(180deg); }
.interim-body {
  display: flex; flex-direction: column; gap: 8px;
  margin: 4px 0 2px; padding: 10px 12px;
  border-left: 2px solid var(--border-strong);
  animation: fadeIn .15s var(--ease);
}
.interim-body p { margin: 0; font-size: 12.5px; color: var(--text-muted); line-height: 1.6; white-space: pre-wrap; word-break: break-word; }

.tool-kb { display: flex; flex-wrap: wrap; gap: 5px; }
.kb-file { display: inline-flex; align-items: center; font-size: 11.5px; padding: 3px 9px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.tool-args { margin: 0 0 6px; font-size: 11.5px; color: var(--text-secondary); background: var(--bg); border-radius: 6px; padding: 6px 8px; overflow-x: auto; }
.tool-result { font-size: 12px; color: var(--text-muted); max-height: 160px; overflow-y: auto; white-space: pre-wrap; word-break: break-word; }
.tool-queries { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 7px; }
.tq-chip { display: inline-flex; align-items: center; font-size: 11.5px; padding: 3px 9px; border-radius: 999px; border: 1px solid var(--border-strong); color: var(--text-secondary); max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ---- Approvals ---- */
.run-section-title { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: .4px; margin-bottom: 6px; }
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

@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>
