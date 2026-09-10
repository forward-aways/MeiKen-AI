<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { convs, activeId, user, theme, locale, sidebarCollapsed, showCollapsedWidget, systemPrompt, pinnedIds, view, setView, mode, setMode, t, applyTheme, setLocale, saveSystemPrompt, togglePin, logout } from '../store.js'

const MODES = [['code', 'modeCode'], ['work', 'modeWork'], ['general', 'modeGeneral']]
import { get, del, put, API_BASE } from '../api.js'

const NAV_ORDER = ['chat', 'skills', 'kb', 'agents', 'profile']
const navIndex = computed(() => Math.max(0, NAV_ORDER.indexOf(view.value)))

const emit = defineEmits(['new-chat', 'open-conv', 'search-mode', 'open-profile', 'open-agents'])
const searchQuery = ref('')
const searchOpen = ref(false)
const convMenuId = ref(null)
const popupOpen = ref(false)
const userMenuOpen = ref(false)
const editNickOpen = ref(false)
const nickEditVal = ref('')
const searchEl = ref(null)
const nickEditEl = ref(null)

function isImgAvatar(v) { return v && v.startsWith('data:') }
function avBgStyle(c) { return c ? { background: c } : {} }

const filteredConvs = computed(() => {
  let arr = (convs.value || []).slice()
  let q = searchQuery.value.toLowerCase()
  if (q) arr = arr.filter(c => c.title.toLowerCase().includes(q))
  let pinned = arr.filter(c => pinnedIds.value.has(c.id))
  let unpinned = arr.filter(c => !pinnedIds.value.has(c.id))
  return [...pinned, ...unpinned]
})

function toggleCollapse() {
  const delay = window.innerWidth <= 768 ? 300 : 250
  if (sidebarCollapsed.value) {
    showCollapsedWidget.value = false
    sidebarCollapsed.value = false
  } else {
    sidebarCollapsed.value = true
    showCollapsedWidget.value = false
    setTimeout(() => { showCollapsedWidget.value = true }, delay)
  }
}

function startEditNick() {
  editNickOpen.value = true
  nickEditVal.value = (user.value || {}).nickname || ''
  nextTick(() => nickEditEl.value?.focus())
}

async function saveNickname() {
  let v = nickEditVal.value.trim()
  if (!v || v === (user.value || {}).nickname) { editNickOpen.value = false; return }
  try {
    let r = await put('/auth/profile', { nickname: v })
    if (r) { user.value.nickname = v; editNickOpen.value = false }
    else { alert('Nickname already taken') }
  } catch (e) { alert(e.message) }
}

async function renameConv(conv) {
  let title = prompt(t('renamePh'), conv.title || '')
  if (title && title.trim() && title.trim() !== conv.title) {
    await fetch(API_BASE + '/conversations/' + conv.id, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ title: title.trim() }) })
    let d = await get('/conversations')
    if (d) convs.value = d
  }
  convMenuId.value = null
}

async function delConv(cid) {
  if (!confirm(t('confirm'))) return
  if (await del('/conversations/' + cid)) {
    if (activeId.value === cid) { emit('new-chat') }
    convMenuId.value = null
    let d = await get('/conversations')
    if (d) convs.value = d
  }
}

async function exportConv(conv) {
  let msgsToExport = []
  let d = await get('/conversations/' + conv.id)
  msgsToExport = d?.messages || []
  let title = conv.title || 'Chat'
  let md = '# ' + title + '\n\n' + msgsToExport.map(m => (m.role === 'user' ? '**You**' : '**MeiKen**') + ':\n' + m.content).join('\n\n---\n\n')
  let blob = new Blob([md], { type: 'text/markdown' })
  let a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = title.replace(/[^a-zA-Z0-9\u4e00-\u9fff]/g, '_') + '.md'
  a.click()
  URL.revokeObjectURL(a.href)
  convMenuId.value = null
}

watch(userMenuOpen, v => { if (!v) editNickOpen.value = false })
watch(systemPrompt, v => { localStorage.setItem('mk-sysprompt', v) })
</script>

<template>
  <div class="sidebar-inner">

    <template v-if="!sidebarCollapsed">
      <div class="sidebar-head">
        <div class="mode-switch" :data-mode="mode">
          <span class="mode-pill"></span>
          <button v-for="m in MODES" :key="m[0]" class="mode-btn" :class="{ active: mode === m[0] }" @click="setMode(m[0])">{{ t(m[1]) }}</button>
        </div>
        <button class="search-toggle" @click="emit('search-mode')" :title="t('search')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </button>
        <button class="sidebar-toggle" @click="toggleCollapse()" :title="t('collapse')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
      </div>

      <nav class="nav-modules" :style="{ '--nav-index': navIndex }">
        <span class="nav-pill"></span>
        <button class="nav-item" :class="{ active: view === 'chat' }" @click="setView('chat')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          {{ t('navChat') }}
        </button>
        <button class="nav-item" :class="{ active: view === 'skills' }" @click="setView('skills')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
          {{ t('navSkills') }}
        </button>
        <button class="nav-item" :class="{ active: view === 'kb' }" @click="setView('kb')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
          {{ t('navKb') }}
        </button>
        <button class="nav-item" :class="{ active: view === 'agents' }" @click="setView('agents')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15" stroke-linecap="round"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="10" r="2"/><path d="M6.5 17c.8-1.4 2.5-2 4.5-2s3.7.6 4.5 2"/></svg>
          {{ t('navAgents') }}
        </button>
        <button class="nav-item" :class="{ active: view === 'profile' }" @click="setView('profile')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          {{ t('navSettings') }}
        </button>
      </nav>

      <button class="btn primary wide" @click="emit('new-chat')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        {{ t('newChat') }}
      </button>

      <div class="search-box" v-if="searchOpen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input v-model="searchQuery" :placeholder="t('search')" type="text" ref="searchEl">
    </div>

    <div class="conv-label">{{ t('recent') }}</div>

    <div class="conv-list" v-if="filteredConvs.length">
      <div v-for="c in filteredConvs" :key="c.id" class="conv-item" :class="{ active: c.id === activeId }" @click="emit('open-conv', c.id)">
        <svg v-if="pinnedIds.has(c.id)" viewBox="0 0 24 24" fill="currentColor" width="12" height="12" style="flex-shrink:0;color:var(--accent)"><path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z"/></svg>
        <span class="t">{{ c.title }}</span>
        <span class="dots-btn" @click.stop="convMenuId = convMenuId === c.id ? null : c.id" :title="t('more')">
          <svg viewBox="0 0 16 4" fill="currentColor" width="16" height="4"><circle cx="2" cy="2" r="1.5"/><circle cx="8" cy="2" r="1.5"/><circle cx="14" cy="2" r="1.5"/></svg>
          <div class="conv-menu glass-pop" v-if="convMenuId === c.id" @click.stop>
            <button @click.stop="togglePin(c.id); convMenuId = null">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z"/></svg>
              {{ pinnedIds.has(c.id) ? t('unpin') : t('pin') }}
            </button>
            <button @click.stop="renameConv(c)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              {{ t('rename') }}
            </button>
            <button @click.stop="exportConv(c)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              {{ t('export') }}
            </button>
            <button class="danger" @click.stop="delConv(c.id)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              {{ t('del') }}
            </button>
          </div>
        </span>
      </div>
    </div>
    <div class="empty-convs" v-if="!filteredConvs.length">{{ searchQuery ? t('noResults') : t('empty') }}</div>

    <div class="sidebar-bottom">
      <div class="popup glass-pop" v-if="popupOpen" @click.stop>
        <div class="popup-label">{{ t('theme') }}</div>
        <div class="popup-row">
          <span>{{ t('theme_' + theme) }}</span>
          <div class="toggle-track" :class="{ on: theme === 'dark' }" @click="applyTheme(theme === 'dark' ? 'light' : 'dark')"><div class="toggle-knob"></div></div>
        </div>
        <div class="popup-label" style="margin-top:.3rem">{{ t('language') }}</div>
        <div class="lang-pills">
          <button class="lang-pill" :class="{ active: locale === 'zh' }" @click="setLocale('zh')">中文</button>
          <button class="lang-pill" :class="{ active: locale === 'en' }" @click="setLocale('en')">EN</button>
        </div>
      </div>

      <div style="display:flex;align-items:center;justify-content:space-between">
        <div class="user-row" @click.stop="userMenuOpen = !userMenuOpen; popupOpen = false">
          <div class="user-avatar" :style="avBgStyle((user || {}).avatar_color)">
            <img v-if="isImgAvatar((user || {}).avatar)" :src="(user || {}).avatar" />
            <template v-else-if="(user || {}).avatar">{{ (user || {}).avatar }}</template>
            <template v-else>{{ ((user || {}).nickname || (user || {}).email || 'U')[0].toUpperCase() }}</template>
          </div>
          <div class="user-name">{{ (user || {}).nickname || (user || {}).email }}</div>
          <div class="popup user-menu glass-pop" v-if="userMenuOpen" @click.stop>
            <div class="info-row">
              <span>{{ t('nickname') }}</span>
              <span class="val">{{ (user || {}).nickname || '—' }}</span>
              <span class="edit-link" v-if="!editNickOpen" @click.stop="startEditNick">{{ t('edit') }}</span>
            </div>
            <div class="nick-edit" v-if="editNickOpen">
              <input v-model="nickEditVal" @keydown.enter="saveNickname" maxlength="50" ref="nickEditEl" :placeholder="t('nicknamePh')" />
              <button @click="saveNickname">{{ t('save') }}</button>
            </div>
            <div class="info-row">
              <span>{{ t('email') }}</span>
              <span class="val">{{ (user || {}).email }}</span>
            </div>
            <div class="divider"></div>
            <button style="width:100%;padding:.4rem;border-radius:7px;border:none;background:transparent;color:var(--text);font-size:12.5px;cursor:pointer;text-align:left;font-family:var(--font);transition:background .15s;display:flex;align-items:center;gap:6px;padding-left:.5rem" @click="userMenuOpen = false; emit('open-profile')" onmouseover="this.style.background='var(--border)'" onmouseout="this.style.background='transparent'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              {{ t('editProfile') }}
            </button>
            <div class="divider"></div>
            <button class="logout-btn" @click="userMenuOpen = false; logout()">{{ t('logout') }}</button>
          </div>
        </div>
        <button class="settings-btn" @click.stop="popupOpen = !popupOpen; userMenuOpen = false" :title="t('settings')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        </button>
      </div>
    </div>
    </template>

    <template v-else>
      <div class="rail">
        <button class="rail-btn rail-logo" @click="toggleCollapse()" :title="t('expand')">
          <svg viewBox="0 0 40 40" width="22" height="22" fill="none"><rect width="40" height="40" rx="10" style="fill:var(--accent)"/><path d="M9 29V12l11 12 11-12v17" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <div class="rail-divider"></div>
        <button class="rail-btn" @click="emit('new-chat')" :title="t('newChat')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        </button>
        <button class="rail-btn" @click="emit('search-mode')" :title="t('search')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </button>
        <div class="rail-divider"></div>
        <button class="rail-btn" :class="{ active: view === 'chat' }" @click="setView('chat')" :title="t('navChat')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        </button>
        <button class="rail-btn" :class="{ active: view === 'skills' }" @click="setView('skills')" :title="t('navSkills')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
        </button>
        <button class="rail-btn" :class="{ active: view === 'kb' }" @click="setView('kb')" :title="t('navKb')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
        </button>
        <button class="rail-btn" :class="{ active: view === 'agents' }" @click="setView('agents')" :title="t('navAgents')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="10" r="2"/><path d="M6.5 17c.8-1.4 2.5-2 4.5-2s3.7.6 4.5 2"/></svg>
        </button>
        <button class="rail-btn" :class="{ active: view === 'profile' }" @click="setView('profile')" :title="t('navSettings')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        </button>
        <div class="rail-spacer"></div>
        <button class="rail-btn" @click="applyTheme(theme === 'dark' ? 'light' : 'dark')" :title="t('theme')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        </button>
        <button class="rail-btn" @click="emit('open-profile')" :title="t('editProfile')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.sidebar-inner { padding: 1rem .85rem; display: flex; flex-direction: column; height: 100%; position: relative; width: 276px; }
.sidebar-inner:has(.rail) { padding: 0; width: 56px; }

.sidebar-head { display: flex; align-items: center; gap: 6px; margin-bottom: 1rem; }
.mode-switch {
  display: grid; grid-template-columns: repeat(3, 1fr);
  flex: 1; gap: 2px; padding: 2px;
  border-radius: 11px;
  position: relative;
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.045'/></svg>"),
    linear-gradient(180deg, rgba(255,255,255,.55), rgba(255,255,255,.3));
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(255,255,255,.65);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.75), 0 2px 10px rgba(20,18,60,.06);
  transition: border-color .2s var(--ease);
}
[data-theme="dark"] .mode-switch {
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.05'/></svg>"),
    linear-gradient(180deg, rgba(44,48,72,.6), rgba(30,33,52,.42));
  border-color: rgba(255,255,255,.12);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 2px 10px rgba(0,0,0,.22);
}
.mode-switch[data-mode="code"] { --step: 0 }
.mode-switch[data-mode="work"] { --step: 1 }
.mode-switch[data-mode="general"] { --step: 2 }
.mode-pill {
  position: absolute; top: 2px; bottom: 2px; left: 2px;
  width: calc((100% - 8px) / 3);
  z-index: 0;
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(255,255,255,.14), rgba(255,255,255,.04) 55%, rgba(255,255,255,.08));
  backdrop-filter: blur(48px) saturate(185%);
  -webkit-backdrop-filter: blur(48px) saturate(185%);
  border: 1px solid rgba(91,87,210,.16);
  box-shadow:
    0 1px 2px rgba(20,18,60,.05),
    0 4px 14px rgba(91,87,210,.12);
  transform: translateX(calc(var(--step) * (100% + 2px)));
  transition: transform .38s var(--spring);
  pointer-events: none;
  will-change: transform;
}
[data-theme="dark"] .mode-pill {
  background: linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.02) 55%, rgba(255,255,255,.05));
  border-color: rgba(126,121,247,.26);
  box-shadow:
    0 1px 2px rgba(0,0,0,.2),
    0 4px 14px rgba(0,0,0,.3);
}
.mode-btn { position: relative; z-index: 1; flex: 1; padding: 7px 6px; border: none; border-radius: 8px; background: transparent; color: var(--text-secondary); font-size: 13.5px; font-family: var(--font); cursor: pointer; transition: color .2s var(--ease); white-space: nowrap; }
.mode-btn:hover { color: var(--text); }
.mode-btn.active { color: var(--accent); font-weight: 650; }
.search-toggle { width: 32px; height: 32px; border-radius: 8px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .15s; flex-shrink: 0; }
.search-toggle:hover { background: var(--border); color: var(--text); }
.sidebar-toggle { width: 32px; height: 32px; border-radius: 8px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .15s; flex-shrink: 0; }
.sidebar-toggle:hover { background: var(--border); color: var(--text); }

.nav-modules { position: relative; display: flex; flex-direction: column; gap: 4px; margin-bottom: .8rem; }
/* Glass lens frame that slides to the active button (buttons never move). */
.nav-pill {
  position: absolute; left: 0; right: 0; top: 0;
  height: 36px;
  transform: translateY(calc(var(--nav-index) * 40px));
  border-radius: 12px;
  z-index: 2;
  pointer-events: none;
  border: 1px solid rgba(91,87,210,.4);
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.05'/></svg>"),
    linear-gradient(180deg, rgba(124,121,247,.22), rgba(91,87,210,.13) 55%, rgba(124,121,247,.18));
  backdrop-filter: blur(24px) saturate(190%);
  -webkit-backdrop-filter: blur(24px) saturate(190%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.6),
    inset 0 -6px 14px rgba(255,255,255,.12),
    0 4px 18px rgba(91,87,210,.18);
  transition: transform .35s var(--spring);
  will-change: transform;
}
[data-theme="dark"] .nav-pill {
  border-color: rgba(126,121,247,.5);
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.05'/></svg>"),
    linear-gradient(180deg, rgba(126,121,247,.3), rgba(91,87,210,.2) 55%, rgba(126,121,247,.26));
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.16),
    inset 0 -6px 14px rgba(255,255,255,.05),
    0 4px 20px rgba(126,121,247,.3);
}
.nav-item {
  position: relative; z-index: 1; display: flex; align-items: center; gap: 9px;
  height: 36px; padding: 0 12px; box-sizing: border-box;
  border: 1px solid transparent; border-radius: 12px;
  background: transparent; color: var(--text-secondary);
  font-size: 14px; font-family: var(--font); cursor: pointer;
  transition: color .2s var(--ease), background .2s var(--ease);
  text-align: left;
}
.nav-item:hover { color: var(--text); }
.nav-item.active { color: var(--accent); font-weight: 650; }
.nav-item svg { flex-shrink: 0; transition: filter .2s var(--ease); }
.nav-item.active svg { filter: drop-shadow(0 0 4px rgba(91,87,210,.5)); }

.rail { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: .7rem .3rem; height: 100%; animation: railIn .3s var(--spring) both; }
.rail-btn { width: 36px; height: 36px; border-radius: 10px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .18s var(--ease); flex-shrink: 0; }
.rail-btn:hover { background: var(--border); color: var(--text); transform: translateY(-1px); }
.rail-btn.active { background: var(--accent-soft); color: var(--accent); }
.rail-logo { margin-bottom: 2px; }
.rail-divider { width: 24px; height: 1px; background: var(--border); margin: 2px 0; }
.rail-spacer { flex: 1; }
.search-box { display: flex; align-items: center; gap: 6px; padding: .35rem .5rem; margin: .4rem 0; border-radius: 9px; background: var(--surface); border: 1px solid var(--border); }
.search-box svg { color: var(--text-muted); flex-shrink: 0; opacity: .5; }
.search-box input { flex: 1; border: none; outline: none; background: transparent; color: var(--text); font-size: 14px; font-family: var(--font); }
.search-box input::placeholder { color: var(--text-muted); }
.conv-label { font-size: 11.5px; text-transform: uppercase; letter-spacing: 1.2px; color: var(--text-muted); font-weight: 600; margin: .7rem 0 .3rem; padding: 0 .2rem; }
.conv-list { flex: 1; overflow-y: auto; overflow-x: visible; margin: 0 -.3rem; padding: 0 .3rem; }
.conv-item { overflow: visible !important; display: flex; align-items: center; gap: 8px; padding: .48rem .5rem; margin: .06rem 0; border-radius: 9px; cursor: pointer; border: 1px solid transparent; transition: all .18s var(--ease); font-size: 14.5px; color: var(--text-secondary); user-select: none; }
.conv-item:hover { background: rgba(99,102,241,.06); color: var(--text); transform: translateX(2px); }
.conv-item.active { background: var(--accent-soft); border-color: color-mix(in srgb, var(--accent) 35%, transparent); color: var(--text); font-weight: 600; transform: none; }
.conv-item .t { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conv-item .dots-btn { opacity: 0; background: none; border: none; padding: 3px 4px; border-radius: 6px; color: var(--text-muted); cursor: pointer; transition: all .15s var(--ease); display: flex; position: relative; }
.conv-item:hover .dots-btn, .conv-item.active .dots-btn { opacity: 1; }
.conv-item .dots-btn:hover { color: var(--text); background: var(--border); }
.conv-menu { position: absolute; right: 0; top: 100%; margin-top: 4px; border-radius: var(--radius); padding: .3rem; z-index: 50; min-width: 140px; animation: popIn .15s var(--ease); }
@keyframes popIn { from { opacity: 0; transform: translateY(6px) scale(.96); } to { opacity: 1; transform: translateY(0) scale(1); } }
.conv-menu button { display: flex; align-items: center; gap: 8px; width: 100%; padding: .4rem .6rem; border: none; background: none; color: var(--text); font-size: 14px; cursor: pointer; border-radius: 7px; font-family: var(--font); transition: background .12s; white-space: nowrap; }
.conv-menu button:hover { background: var(--border); }
.conv-menu button.danger { color: var(--danger); }
.conv-menu button.danger:hover { background: var(--danger-soft); }
.conv-menu button svg { width: 14px; height: 14px; opacity: .6; }
.empty-convs { text-align: center; padding: 2rem 1rem; color: var(--text-muted); font-size: 14px; }
.sidebar-bottom { margin-top: auto; padding-top: .5rem; border-top: 1px solid var(--border); position: relative; }
.user-row { display: flex; align-items: center; gap: 8px; padding: .4rem; border-radius: 9px; cursor: pointer; transition: background .15s; position: relative; }
.user-row:hover { background: rgba(99,102,241,.05); }
.user-menu { left: 0; right: auto; min-width: 220px; }
.user-menu .info-row { display: flex; align-items: center; justify-content: space-between; padding: .35rem .5rem; font-size: 14px; color: var(--text-secondary); }
.user-menu .info-row .val { color: var(--text); font-weight: 500; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-left: .3rem; }
.user-menu .info-row .edit-link { color: var(--accent); font-size: 13px; cursor: pointer; flex-shrink: 0; margin-left: .4rem; }
.user-menu .info-row .edit-link:hover { text-decoration: underline; }
.user-menu .divider { margin: .3rem 0; border-top: 1px solid var(--border); }
.user-menu .nick-edit { display: flex; gap: 4px; padding: .3rem .5rem; }
.user-menu .nick-edit input { flex: 1; padding: .3rem .4rem; border-radius: 6px; border: 1px solid var(--border-strong); background: var(--bg); color: var(--text); font-size: 13px; font-family: var(--font); outline: none; }
.user-menu .nick-edit input:focus { border-color: var(--accent); }
.user-menu .nick-edit button { padding: .25rem .5rem; border-radius: 6px; border: none; background: var(--accent); color: #fff; font-size: 12px; font-weight: 600; cursor: pointer; font-family: var(--font); }
.user-avatar { width: 28px; height: 28px; border-radius: 7px; background: var(--accent); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0; }
.user-avatar img { width: 100%; height: 100%; object-fit: cover; border-radius: inherit; }
.user-name { font-size: 14px; font-weight: 550; color: var(--text); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.settings-btn { width: 28px; height: 28px; border-radius: 7px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .15s; }
.settings-btn:hover { background: var(--border); color: var(--text); }
.popup { position: absolute; bottom: 100%; left: 0; right: 0; margin-bottom: 8px; border-radius: var(--radius); padding: .5rem; z-index: 100; animation: popIn .2s var(--spring); }
.popup-label { font-size: 10.5px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); font-weight: 600; padding: .3rem .5rem .2rem; }
.popup-row { display: flex; align-items: center; justify-content: space-between; padding: .4rem .5rem; border-radius: 7px; font-size: 14px; color: var(--text); }
.toggle-track { width: 38px; height: 21px; border-radius: 11px; background: var(--border-strong); cursor: pointer; position: relative; transition: background .2s; }
.toggle-track.on { background: var(--accent); }
.toggle-knob { position: absolute; top: 2px; left: 2px; width: 17px; height: 17px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.15); transition: transform .2s var(--spring); }
.toggle-track.on .toggle-knob { transform: translateX(17px); }
.lang-pills { display: flex; gap: 3px; padding: 3px; border-radius: 7px; background: var(--border); margin: .2rem .3rem; }
.lang-pill { flex: 1; padding: .32rem 0; border-radius: 6px; border: none; background: transparent; color: var(--text-secondary); font-size: 13px; font-weight: 550; cursor: pointer; text-align: center; transition: all .15s; font-family: var(--font); }
.lang-pill.active { background: var(--surface); color: var(--text); font-weight: 650; box-shadow: var(--shadow-xs); }
.logout-btn { width: 100%; padding: .4rem; margin-top: .25rem; border-radius: 7px; border: none; background: transparent; color: var(--danger); font-size: 13.5px; cursor: pointer; text-align: center; font-family: var(--font); transition: background .15s; }
.logout-btn:hover { background: var(--danger-soft); }

@media (max-width: 768px) {
  .sidebar-inner { width: 276px; padding: .85rem .75rem; }
  .sidebar-toggle { width: 34px; height: 34px; }
  .search-toggle { width: 34px; height: 34px; }
}
</style>
