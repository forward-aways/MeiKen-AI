<script setup>
import { ref, reactive, computed, nextTick, onMounted, watch } from 'vue'
import { authed, user, convs, activeId, msgs, input, busy, theme, locale, sidebarCollapsed, showCollapsedWidget, systemPrompt, pinnedIds, agents, currentAgentId, currentAgent, setCurrentAgent, mode, view, setView, modelOverride, effectiveEffort, t, applyTheme, setLocale, saveSystemPrompt, togglePin, loadAll, loadAgents, checkAuth, logout, uploadTempFile, deleteTempFile, setContextTokens, addContextTokens } from './store.js'
import { get, post, del as apiDel, fetchRaw } from './api.js'
import { stripMd } from './md.js'
import { log } from './logger.js'
import LoginPage from './components/LoginPage.vue'
import Sidebar from './components/Sidebar.vue'
import TopBar from './components/TopBar.vue'
import ActivityPanel from './components/ActivityPanel.vue'
import ChatMessage from './components/ChatMessage.vue'
import MessageInput from './components/MessageInput.vue'
import Dashboard from './components/Dashboard.vue'
import SearchPage from './components/SearchPage.vue'
import ProfilePage from './components/ProfilePage.vue'
import KbPage from './components/KbPage.vue'
import SkillsPage from './components/SkillsPage.vue'
import AgentRun from './components/AgentRun.vue'
import AgentConfigPage from './components/AgentConfigPage.vue'

const atBottom = ref(true)
const chatArea = ref(null)
const welcomeRef = ref(null)
const welcomeShow = ref(true)
const convKey = ref(0)
let abortCtrl = null
const editingIdx = ref(null)
const editText = ref('')
const searchingQuery = ref('')
const tempFileData = ref(null)
const isMobile = ref(window.innerWidth <= 768)
const disclaimerAgreed = ref(localStorage.getItem('mk-disclaimer') === '1')
const disclaimerChecked = ref(false)

function agreeDisclaimer() {
  if (!disclaimerChecked.value) return
  disclaimerAgreed.value = true
  localStorage.setItem('mk-disclaimer', '1')
}

async function onTempFile(file) {
  if (!file) {
    if (tempFileData.value) {
      await deleteTempFile(tempFileData.value.file.id)
      tempFileData.value = null
    }
    return
  }
  const data = await uploadTempFile(file)
  if (data && data.ok) {
    if (tempFileData.value) {
      await deleteTempFile(tempFileData.value.file.id)
    }
    tempFileData.value = data
  } else {
    alert(t('uploadFail'))
  }
}

function splitInterim(ast) {
  // Text emitted before a tool call is process talk — move it out of the
  // answer bubble so only the final answer stays in the main text.
  if (ast.content && ast.content.trim()) {
    ast.interim = ast.interim || []
    ast.interim.push(ast.content.trim())
    ast.content = ''
  }
}

function applyEvent(ast, ev) {
  if (ev.token) { ast.content += ev.token; ast.phase = 'generating'; return true }
  if (ev.reasoning) { ast.reasoning = (ast.reasoning || '') + ev.reasoning; ast.phase = 'thinking'; return true }
  if (ev.thinking_done) { ast.thinkingTime = ev.thinking_done; return true }
  if (ev.tokens) { ast.tokens = ev.tokens; return true }
  if (ev.status === 'searching') { searchingQuery.value = ev.query || ''; return true }
  if (ev.status === 'searched') { searchingQuery.value = ''; if (ev.results) { ast.searchResults = ev.results; ast.searchQuery = ev.query } return true }
  if (ev.status === 'rag_loaded') { ast.ragSources = ev.sources || []; return true }
  if (ev.type === 'todo') { ast.todos = ev.todos; return true }
  if (ev.type === 'tool_call') {
    splitInterim(ast)
    ast.toolCalls = ast.toolCalls || []
    ast.seq = (ast.seq || 0) + 1
    ast.toolCalls.push({ id: ev.id || '', tool: ev.tool, args: ev.args, status: 'running', result: '', sources: [], seq: ast.seq })
    ast.phase = 'tool:' + ev.tool
    return true
  }
  if (ev.type === 'tool_result') {
    const list = ast.toolCalls || []
    // Match by tool_call id first (same tool may be called multiple times),
    // fall back to the first running call with the same name.
    let tc = ev.id ? list.find((x) => x.id === ev.id) : null
    if (!tc) tc = list.find((x) => x.tool === ev.tool && x.status === 'running')
    if (tc) {
      tc.status = 'done'
      tc.result = ev.result
      if (ev.sources) tc.sources = ev.sources
    }
    if (!list.some((x) => x.status === 'running')) ast.phase = ''
    return true
  }
  if (ev.status === 'sub_started') {
    splitInterim(ast)
    ast.subagents = ast.subagents || []
    ast.seq = (ast.seq || 0) + 1
    ast.subagents.push({ name: ev.subagent, task: ev.task, status: 'running', seq: ast.seq })
    ast.phase = 'sub:' + ev.subagent
    return true
  }
  if (ev.status === 'sub_done') {
    const s = (ast.subagents || []).find((x) => x.name === ev.subagent)
    if (s) s.status = 'done'
    ast.phase = ''
    return true
  }
  if (ev.type === 'approval_request') {
    ast.approvals = ast.approvals || []
    ast.approvals.push({ action_id: ev.action_id, tool: ev.tool, args: ev.args, allowed: ev.allowed, status: 'pending' })
    ast.pendingApproval = true
    ast.phase = 'approval'
    return true
  }
  if (ev.status === 'run_end') {
    if (typeof ev.final_text === 'string') ast.content = ev.final_text
    ast.interrupted = ev.interrupted; ast.phase = ''
    if (ev.tokens) addContextTokens(ev.tokens)
    return true
  }
  if (ev.error) { log.error('SSE error |', ev.error); ast.content = '⚠ ' + ev.error; ast.error = true; ast.phase = ''; return true }
  if (ev.done) { if (ev.tokens) ast.tokens = ev.tokens; return true }
  return false
}

async function readStream(r, ast, onDone) {
  const reader = r.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  while (true) {
    let { done, value } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let lines = buf.split('\n'); buf = lines.pop() || ''
    for (let l of lines) {
      if (!l.startsWith('data:')) continue
      let ev
      try { ev = JSON.parse(l.slice(5).trim()) } catch { continue }
      if (applyEvent(ast, ev)) { await nextTick(); if (atBottom.value) scroll() }
    }
  }
  if (onDone) onDone()
}

async function handleApproval(msg, approval, decision, editedArgs, message) {
  const ap = (msg.approvals || []).find((a) => a.action_id === approval.action_id)
  if (ap) ap.status = decision
  if (!(msg.approvals || []).some((a) => a.status === 'pending')) msg.pendingApproval = false
  msg.streaming = true
  try {
    let r = await fetchRaw('/approvals/' + approval.action_id, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, edited_args: editedArgs, message })
    })
    await readStream(r, msg)
  } catch (e) {
    log.error('approval request failed |', e)
    msg.content += '\n⚠ ' + (e.message || t('err'))
  } finally {
    msg.streaming = false
    await nextTick(); if (atBottom.value) scroll()
    setTimeout(() => loadAll(), 0)
  }
}

async function send(txt, isRetry = false, imageIds = []) {
  let msg = (txt || '').trim()
  if ((!msg && !imageIds.length) || busy.value) return
  if (!activeId.value) {
    let d = await post('/conversations', { title: t('title') })
    if (!d) return
    activeId.value = d.id
await loadAll()
  }
  let cid = activeId.value
  input.value = ''
  editingIdx.value = null
  let useTempFile = tempFileData.value
  if (!isRetry) {
    let userMsg = { role: 'user', content: msg }
    if (imageIds.length) userMsg.images = [...imageIds]
    if (useTempFile) userMsg.tempFile = useTempFile.file.filename
    msgs.value.push(userMsg)
  }
  await nextTick(); scroll()
  busy.value = true
  let ctrl = new AbortController(); abortCtrl = ctrl
  let ast = reactive({ role: 'assistant', content: '', streaming: true })
  msgs.value.push(ast)
  await nextTick(); if (atBottom.value) scroll()
  try {
    let payload = {
      message: msg,
      image_ids: imageIds,
      system_prompt: systemPrompt.value,
      agent_id: currentAgentId.value,
      model: modelOverride.value || null,
      thinking: effectiveEffort().thinking,
      reasoning_effort: effectiveEffort().effort,
      mode: mode.value
    }
    if (useTempFile) {
      payload.rag_files = [useTempFile.file.id]
    }
    let r = await fetchRaw('/chat/' + cid, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: ctrl.signal
    })
    await readStream(r, ast)
    if (atBottom.value) { await nextTick(); scroll() }
  } catch (e) {
    if (e.name === 'AbortError') {
      if (ast.content) ast.content += '\n\n*[' + t('stopped') + ']*'
      else ast.content = '*[' + t('stopped') + ']*'
    } else {
      log.error('chat request failed |', e)
      ast.content = '⚠ ' + t('err') + ' ' + e.message
      ast.error = true
    }
  }
  ast.streaming = false
  busy.value = false; abortCtrl = null
  if (useTempFile) {
    await deleteTempFile(useTempFile.file.id)
    tempFileData.value = null
  }
  if (atBottom.value) {
    await nextTick(); scroll()
    requestAnimationFrame(() => { requestAnimationFrame(() => { if (atBottom.value) scroll() }) })
  }
  setTimeout(() => { if (!ast.error) loadAll() }, 0)
}

function stopGen() {
  if (abortCtrl) { abortCtrl.abort(); busy.value = false; abortCtrl = null }
  let last = msgs.value[msgs.value.length - 1]
  if (last && last.role === 'assistant') last.streaming = false
}

async function deleteMsg(idx, msgId) {
  if (!confirm(t('confirmDeleteMsg'))) return
  let cid = activeId.value
  if (cid && msgId) {
    await apiDel('/conversations/' + cid + '/messages/' + msgId)
  }
  msgs.value.splice(idx, 1)
}

function retry(idx) {
  for (let i = idx - 1; i >= 0; i--) {
    if (msgs.value[i].role === 'user') {
      let msg = msgs.value[i].content
      msgs.value.splice(i + 1)
      send(msg, true)
      return
    }
  }
}

function regenerate(idx) {
  for (let i = idx - 1; i >= 0; i--) {
    if (msgs.value[i].role === 'user') {
      let msg = msgs.value[i].content
      msgs.value.splice(i + 1)
      send(msg, true)
      return
    }
  }
}

async function openConv(cid) {
  setView('chat')
  if (isMobile.value && !sidebarCollapsed.value) {
    sidebarCollapsed.value = true
    showCollapsedWidget.value = true
  }
  let d = await get('/conversations/' + cid)
  if (!d) return
  activeId.value = cid
  msgs.value = d.messages || []
  setContextTokens((d.messages || []).reduce((s, m) => s + (m.tokens || 0), 0))
  welcomeShow.value = false
  convKey.value++
  await nextTick()
  scroll()
  highlightAll()
}

function newChat() {
  activeId.value = null
  msgs.value = []
  input.value = ''
  setContextTokens(0)
  welcomeShow.value = true
  editingIdx.value = null
  setView('chat')
  if (isMobile.value && !sidebarCollapsed.value) {
    sidebarCollapsed.value = true
    showCollapsedWidget.value = true
  }
  if (welcomeRef.value) welcomeRef.value.runTypewriter()
}

async function delConv(cid) {
  if (!confirm(t('confirm'))) return
  await apiDel('/conversations/' + cid)
  if (activeId.value === cid) {
    activeId.value = null
    msgs.value = []
    welcomeShow.value = true
    if (welcomeRef.value) welcomeRef.value.runTypewriter()
  }
  loadAll()
}

function scroll() {
  if (chatArea.value) {
    chatArea.value.scrollTop = chatArea.value.scrollHeight
    atBottom.value = true
  }
}

function onScroll() {
  if (chatArea.value) {
    atBottom.value = chatArea.value.scrollHeight - chatArea.value.scrollTop - chatArea.value.clientHeight < 40
  }
}

function openProfile() {
  setView('profile')
  if (isMobile.value && !sidebarCollapsed.value) {
    sidebarCollapsed.value = true
    showCollapsedWidget.value = true
  }
}

function openAgents() {
  setView('agents')
  if (isMobile.value && !sidebarCollapsed.value) {
    sidebarCollapsed.value = true
    showCollapsedWidget.value = true
  }
}

function toggleCollapse() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  if (sidebarCollapsed.value) {
    setTimeout(() => { showCollapsedWidget.value = true }, isMobile.value ? 300 : 400)
  } else {
    showCollapsedWidget.value = false
  }
}

function onSidebarBackdrop() {
  if (isMobile.value) {
    sidebarCollapsed.value = true
    setTimeout(() => { showCollapsedWidget.value = true }, 300)
  }
}

function startEdit(i) {
  editingIdx.value = i
  editText.value = msgs.value[i].content
}

function confirmEdit() {
  if (!editText.value.trim()) return
  msgs.value.splice(editingIdx.value)
  send(editText.value, true)
}

function onEditKeydown(e) {
  if (e.key === 'Escape') { editingIdx.value = null; editText.value = '' }
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    confirmEdit()
  }
}

async function copyText(content, idx) {
  try {
    await navigator.clipboard.writeText(stripMd(content))
  } catch {
    await navigator.clipboard.writeText(content)
  }
}

async function copyMd(content, idx) {
  await navigator.clipboard.writeText(content)
}

function highlightAll() {
  if (window.hljs) {
    nextTick(() => { window.hljs.highlightAll() })
  }
}

onMounted(() => {
  if (isMobile.value) {
    sidebarCollapsed.value = true
    showCollapsedWidget.value = true
  }
  window.addEventListener('resize', onWindowResize)
  applyTheme(theme.value)
  checkAuth()
  loadAgents()
  const hash = window.location.hash.slice(1)
  const params = new URLSearchParams(hash)
  if (params.get('reset-token')) {
    localStorage.setItem('mk-reset-token', params.get('reset-token'))
  }
})

function onWindowResize() {
  const mobile = window.innerWidth <= 768
  if (mobile !== isMobile.value) {
    isMobile.value = mobile
    if (mobile) {
      sidebarCollapsed.value = true
      showCollapsedWidget.value = true
    } else {
      sidebarCollapsed.value = localStorage.getItem('sidebar_collapsed') === '1'
      showCollapsedWidget.value = sidebarCollapsed.value
    }
  }
}

watch([() => msgs.value.length, busy], ([len, b]) => {
  if (!b && len > 0) highlightAll()
})

watch(locale, () => {
  if (authed.value && !msgs.value.length && welcomeRef.value) {
    welcomeRef.value.runTypewriter()
  }
})

watch(view, () => {
  const main = document.querySelector('.main')
  if (!main) return
  main.classList.remove('view-anim')
  void main.offsetWidth
  main.classList.add('view-anim')
})
</script>

<template>
  <div v-if="!disclaimerAgreed" class="disclaimer-overlay">
    <div class="disclaimer-modal">
      <div class="disclaimer-logo">
        <svg viewBox="0 0 40 40" width="48" height="48" fill="none"><rect width="40" height="40" rx="10" style="fill:var(--accent)"/><path d="M9 29V12l11 12 11-12v17" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </div>
      <h2>{{ t('disclaimerTitle') }}</h2>
      <div class="disclaimer-body" v-html="t('disclaimerText').replace(/\n/g, '<br>')"></div>
      <label class="disclaimer-check">
        <input type="checkbox" v-model="disclaimerChecked" />
        <span>{{ t('disclaimerAgree') }}</span>
      </label>
      <button class="btn primary wide" :disabled="!disclaimerChecked" @click="agreeDisclaimer">
        {{ t('disclaimerBtn') }}
      </button>
    </div>
  </div>

  <template v-if="disclaimerAgreed">
  <LoginPage v-if="!authed" />

  <template v-if="authed">
    <TopBar />

    <div class="shell-body">
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <Sidebar
        @new-chat="newChat"
        @open-conv="openConv"
        @search-mode="setView('search'); if (isMobile) { sidebarCollapsed = true; showCollapsedWidget = true }"
        @open-profile="openProfile()"
      />
    </aside>

    <div v-if="isMobile && !sidebarCollapsed" class="sidebar-backdrop" @click="onSidebarBackdrop"></div>

    <section class="main">
      <SearchPage
        v-if="view === 'search'"
        @close="setView('chat')"
        @open-conv="(cid) => { setView('chat'); openConv(cid) }"
      />

      <template v-if="view === 'chat'">
        <div class="collapsed-group" v-if="isMobile && showCollapsedWidget">
          <svg viewBox="0 0 40 40" width="26" height="26" fill="none"><rect width="40" height="40" rx="10" style="fill:var(--accent)"/><path d="M9 29V12l11 12 11-12v17" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <div class="collapsed-header glass-pop">
            <button @click="toggleCollapse()" :title="t('expand')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button @click="setView('search'); nextTick(() => {})" :title="t('search')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            </button>
            <button @click="newChat" :title="t('newChat')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
          </div>
        </div>

        <div class="chat-area" ref="chatArea" @scroll="onScroll">
          <div class="chat-inner">
            <Dashboard v-if="!msgs.length && welcomeShow" ref="welcomeRef" @send="send" @tempFile="onTempFile" />

            <ChatMessage
              v-for="(m, i) in msgs"
              :key="convKey + '-' + i"
              :message="m"
              :index="i"
              @regenerate="regenerate(i)"
              @retry="retry(i)"
              @send="(payload) => send(payload?.content || m.content, true)"
              @delete="deleteMsg(i, m.id)"
            />
            <template v-for="(m, i) in msgs" :key="'run-' + convKey + '-' + i">
              <AgentRun v-if="m.role === 'assistant'" :msg="m" @approve="handleApproval" />
            </template>

            <div class="typing" v-if="busy"><span></span><span></span><span></span></div>
            <div class="searching-bar" v-if="searchingQuery">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <span>{{ t('searching') }}</span>
            </div>
          </div>
        </div>

        <MessageInput
          v-if="msgs.length"
          :modelValue="input"
          :disabled="busy"
          :placeholder="t('ph')"
          @update:modelValue="(v) => { input = v }"
          @send="(ids) => send(input, false, ids)"
          @stop="stopGen"
          @tempFile="onTempFile"
        />

        <div class="ai-disclaimer" v-if="msgs.length">— {{ t('aiDisclaimer') }} —</div>

        <button class="scroll-btn glass-pop" :class="{ 'with-activity': view === 'chat' && !isMobile }" v-if="!atBottom && msgs.length" @click="scroll(); atBottom = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9" /></svg>
        </button>
      </template>

      <ProfilePage v-if="view === 'profile'" @close="setView('chat')" />
      <AgentConfigPage v-if="view === 'agents'" @close="setView('chat')" />
      <KbPage v-if="view === 'kb'" />
      <SkillsPage v-if="view === 'skills'" @close="setView('chat')" />
    </section>

    <ActivityPanel v-if="view === 'chat'" @approve="handleApproval" />
    </div>
  </template>
  </template>
</template>

<style>
.collapsed-group {
  position: fixed;
  top: 52px;
  left: 20px;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 10px;
  animation: popIn .2s var(--spring);
}

.collapsed-logo {
  border-radius: 10px;
}

@keyframes popIn {
  from { opacity: 0; transform: translateY(6px) scale(.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.collapsed-header {
  display: flex;
  align-items: center;
  gap: 2px;
  border-radius: var(--radius-lg);
  padding: 3px;
}

.collapsed-header button {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .15s;
}

.collapsed-header button:hover {
  background: var(--border);
  color: var(--text);
}

.chat-area {
  flex: 1;
  overflow-y: auto;
  margin-top: -52px; /* stretch under the floating top bar so messages fade out at the very top */
  padding: calc(52px + 1rem) 1.5rem 1rem;
  scroll-behavior: smooth;
  /* messages dissolve inside the top bar region and vanish exactly at the very top */
  mask-image: linear-gradient(to bottom, rgba(0,0,0,0) 0, rgba(0,0,0,.3) 18px, rgba(0,0,0,.78) 42px, #000 60px);
  -webkit-mask-image: linear-gradient(to bottom, rgba(0,0,0,0) 0, rgba(0,0,0,.3) 18px, rgba(0,0,0,.78) 42px, #000 60px);
}

.chat-inner {
  max-width: 860px;
  margin: 0 auto;
  width: 100%;
}

.scroll-btn {
  position: fixed;
  bottom: 175px; /* floats just above the input box */
  right: 30px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  transition: all .2s var(--ease);
  animation: fadeIn .2s var(--ease);
}

.scroll-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  transform: translateY(-2px);
}
.scroll-btn.with-activity { right: 300px; }
@media (max-width: 1024px) { .scroll-btn.with-activity { right: 30px; } }

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.searching-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--accent);
  font-size: 13px;
  padding: 8px 0;
  animation: fadeIn .3s var(--ease);
}

@media (max-width: 768px) {
  .collapsed-group { top: .55rem; left: 10px; }
  .collapsed-header button { width: 38px; height: 38px; }
  .scroll-btn { bottom: 150px; right: 12px; width: 40px; height: 40px; }
  .chat-area {
    margin-top: -48px; padding: calc(48px + .6rem) .75rem .6rem;
    mask-image: linear-gradient(to bottom, rgba(0,0,0,0) 0, rgba(0,0,0,.3) 16px, rgba(0,0,0,.78) 38px, #000 54px);
    -webkit-mask-image: linear-gradient(to bottom, rgba(0,0,0,0) 0, rgba(0,0,0,.3) 16px, rgba(0,0,0,.78) 38px, #000 54px);
  }
}

.disclaimer-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0,0,0,.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.disclaimer-modal {
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  max-width: 560px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
  padding: 2.5rem 2rem;
  animation: fadeSlide .35s var(--spring);
}

.disclaimer-logo {
  display: flex;
  justify-content: center;
  margin-bottom: 1.2rem;
}

.disclaimer-modal h2 {
  font-size: 20px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 1.2rem;
  color: var(--text);
}

.disclaimer-body {
  font-size: 13.5px;
  line-height: 1.75;
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
  max-height: 40vh;
  overflow-y: auto;
  padding-right: .5rem;
}

.disclaimer-check {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--text);
  cursor: pointer;
  margin-bottom: 1.2rem;
  user-select: none;
}

.disclaimer-check input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: var(--accent);
  cursor: pointer;
  flex-shrink: 0;
}

.ai-disclaimer {
  text-align: center;
  font-size: 11.5px;
  color: var(--text-muted);
  padding: 0 1rem .4rem;
  margin-top: -.8rem;
  flex-shrink: 0;
  opacity: .7;
}

@media (max-width: 768px) {
  .disclaimer-modal { padding: 1.5rem 1.2rem; }
  .disclaimer-modal h2 { font-size: 18px; }
  .disclaimer-body { font-size: 12.5px; max-height: 35vh; }
}
</style>
