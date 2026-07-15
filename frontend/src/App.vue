<script setup>
import { ref, reactive, computed, nextTick, onMounted, watch } from 'vue'
import { authed, user, convs, activeId, msgs, input, busy, theme, locale, sidebarCollapsed, showCollapsedWidget, systemPrompt, searchEnabled, thinkingEnabled, ragEnabled, pinnedIds, t, applyTheme, setLocale, saveSystemPrompt, togglePin, loadConvs, checkAuth, logout, uploadTempFile, deleteTempFile } from './store.js'
import { get, post, del as apiDel, fetchRaw } from './api.js'
import { stripMd } from './md.js'
import LoginPage from './components/LoginPage.vue'
import Sidebar from './components/Sidebar.vue'
import ChatMessage from './components/ChatMessage.vue'
import MessageInput from './components/MessageInput.vue'
import WelcomeScreen from './components/WelcomeScreen.vue'
import SearchPage from './components/SearchPage.vue'
import ProfilePage from './components/ProfilePage.vue'

const atBottom = ref(true)
const chatArea = ref(null)
const welcomeRef = ref(null)
const searchMode = ref(false)
const profileMode = ref(false)
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

async function send(txt, isRetry = false) {
  let msg = (txt || '').trim()
  if (!msg || busy.value) return
  if (!activeId.value) {
    let d = await post('/conversations', { title: t('title') })
    if (!d) return
    activeId.value = d.id
    await loadConvs()
  }
  let cid = activeId.value
  input.value = ''
  editingIdx.value = null
  let useTempFile = tempFileData.value
  if (!isRetry) {
    let userMsg = { role: 'user', content: msg }
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
    let payload = { message: msg, system_prompt: systemPrompt.value, enable_search: searchEnabled.value, enable_thinking: thinkingEnabled.value, enable_rag: ragEnabled.value }
    if (useTempFile) {
      payload.enable_rag = true
      payload.rag_files = [useTempFile.file.id]
    }
    let r = await fetchRaw('/chat/' + cid, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: ctrl.signal
    })
    let reader = r.body.getReader()
    let dec = new TextDecoder()
    let buf = ''
    while (true) {
      let { done, value } = await reader.read()
      if (done) break
      buf += dec.decode(value, { stream: true })
      let lines = buf.split('\n'); buf = lines.pop() || ''
      for (let l of lines) {
        if (!l.startsWith('data:')) continue
        let ev = JSON.parse(l.slice(5).trim())
        if (ev.token) { ast.content += ev.token; await nextTick(); if (atBottom.value) scroll() }
        else if (ev.reasoning) { ast.reasoning = (ast.reasoning || '') + ev.reasoning; await nextTick(); if (atBottom.value) scroll() }
        else if (ev.thinking_done) { ast.thinkingTime = ev.thinking_done }
        else if (ev.tokens) { ast.tokens = ev.tokens }
        else if (ev.status === 'searching') { searchingQuery.value = ev.query || '' }
        else if (ev.status === 'searched') { searchingQuery.value = ''; if (ev.results) { ast.searchResults = ev.results; ast.searchQuery = ev.query } }
        else if (ev.status === 'rag_loaded') { ast.ragSources = ev.sources || [] }
        else if (ev.error) { ast.content = '⚠ ' + ev.error; ast.error = true }
        else if (ev.done) { if (ev.tokens) ast.tokens = ev.tokens }
      }
    }
    if (atBottom.value) { await nextTick(); scroll() }
  } catch (e) {
    if (e.name === 'AbortError') {
      if (ast.content) ast.content += '\n\n*[' + t('stopped') + ']*'
      else ast.content = '*[' + t('stopped') + ']*'
    } else {
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
  setTimeout(() => { if (!ast.error) loadConvs() }, 0)
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
  profileMode.value = false
  searchMode.value = false
  if (isMobile.value && !sidebarCollapsed.value) {
    sidebarCollapsed.value = true
    showCollapsedWidget.value = true
  }
  let d = await get('/conversations/' + cid)
  if (!d) return
  activeId.value = cid
  msgs.value = d.messages || []
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
  welcomeShow.value = true
  editingIdx.value = null
  searchMode.value = false
  profileMode.value = false
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
  await loadConvs()
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
  profileMode.value = true
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
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <Sidebar
        @new-chat="newChat"
        @open-conv="openConv"
        @search-mode="searchMode = true; if (isMobile) { sidebarCollapsed = true; showCollapsedWidget = true }"
        @open-profile="openProfile()"
      />
    </aside>

    <div v-if="isMobile && !sidebarCollapsed" class="sidebar-backdrop" @click="onSidebarBackdrop"></div>

    <section class="main">
      <SearchPage
        v-if="searchMode"
        @close="searchMode = false"
        @open-conv="(cid) => { searchMode = false; openConv(cid) }"
      />

      <template v-if="!searchMode && !profileMode">
        <div class="collapsed-group" v-if="showCollapsedWidget">
          <svg viewBox="0 0 40 40" width="26" height="26" fill="none"><rect width="40" height="40" rx="10" style="fill:var(--accent)"/><path d="M9 29V12l11 12 11-12v17" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <div class="collapsed-header">
            <button @click="toggleCollapse()" :title="t('expand')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button @click="searchMode = true; nextTick(() => {})" :title="t('search')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            </button>
            <button @click="newChat" :title="t('newChat')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
          </div>
        </div>

        <div class="top-bar" v-if="!sidebarCollapsed"><div style="flex:1"></div></div>

        <div class="chat-area" ref="chatArea" @scroll="onScroll">
          <div class="chat-inner">
            <WelcomeScreen v-if="!msgs.length && welcomeShow" ref="welcomeRef" @send="send" />

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

            <div class="typing" v-if="busy"><span></span><span></span><span></span></div>
            <div class="searching-bar" v-if="searchingQuery">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <span>{{ t('searching') }}</span>
            </div>
          </div>
        </div>

        <div class="ai-disclaimer" v-if="msgs.length">— {{ t('aiDisclaimer') }} —</div>

        <MessageInput
          v-if="msgs.length"
          :modelValue="input"
          :disabled="busy"
          :placeholder="t('ph')"
          :searchEnabled="searchEnabled.value"
          :thinkingEnabled="thinkingEnabled.value"
          @update:modelValue="(v) => { input = v }"
          @update:searchEnabled="(v) => { searchEnabled.value = v }"
          @update:thinkingEnabled="(v) => { thinkingEnabled.value = v }"
          @send="send(input)"
          @stop="stopGen"
          @tempFile="onTempFile"
        />

        <button class="scroll-btn" v-if="!atBottom && msgs.length" @click="scroll(); atBottom = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9" /></svg>
        </button>
      </template>

      <ProfilePage v-if="profileMode" @close="profileMode = false" />
    </section>
  </template>
  </template>
</template>

<style>
.collapsed-group {
  position: fixed;
  top: .85rem;
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
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 3px;
  box-shadow: var(--shadow-md);
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

.top-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 1rem 1.5rem;
  position: sticky;
  top: 0;
  z-index: 10;
  background: transparent;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: none;
}

.chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.5rem;
  scroll-behavior: smooth;
}

.chat-inner {
  max-width: 800px;
  margin: 0 auto;
}

.scroll-btn {
  position: fixed;
  bottom: 90px;
  right: 30px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-md);
  z-index: 20;
  transition: all .2s var(--ease);
  animation: fadeIn .2s var(--ease);
}

.scroll-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  transform: translateY(-2px);
}

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
  .scroll-btn { bottom: 80px; right: 12px; width: 40px; height: 40px; }
  .top-bar { padding: .6rem .75rem; }
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
  padding: .4rem 1rem .2rem;
  flex-shrink: 0;
  opacity: .7;
}

@media (max-width: 768px) {
  .disclaimer-modal { padding: 1.5rem 1.2rem; }
  .disclaimer-modal h2 { font-size: 18px; }
  .disclaimer-body { font-size: 12.5px; max-height: 35vh; }
}
</style>
