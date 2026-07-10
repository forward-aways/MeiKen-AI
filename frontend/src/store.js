import { reactive, ref, computed } from 'vue'
import { TXT } from './i18n.js'
import { get, post, put } from './api.js'

export const authed = ref(false)
export const user = ref({ email: '', nickname: '' })
export const convs = ref([])
export const activeId = ref(null)
export const msgs = ref([])
export const input = ref('')
export const busy = ref(false)
export const searchEnabled = ref(false)
export const thinkingEnabled = ref(false)
export let abortCtrl = null

export const theme = ref(localStorage.getItem('mk-theme') || 'light')
export const locale = ref(localStorage.getItem('mk-locale') || 'zh')
export const sidebarCollapsed = ref(false)
export const showCollapsedWidget = ref(false)

export const systemPrompt = ref(localStorage.getItem('mk-sysprompt') || '')
export const pinnedIds = ref(new Set(JSON.parse(localStorage.getItem('mk-pinned') || '[]')))

export function t(k) {
  return TXT[locale.value]?.[k] ?? TXT.en?.[k] ?? k
}

export function applyTheme(v) {
  theme.value = v
  document.documentElement.setAttribute('data-theme', v)
  localStorage.setItem('mk-theme', v)
}

export function setLocale(v) {
  locale.value = v
  localStorage.setItem('mk-locale', v)
}

export function saveSystemPrompt(v) {
  localStorage.setItem('mk-sysprompt', v)
}

export function togglePin(cid) {
  const s = new Set(pinnedIds.value)
  if (s.has(cid)) s.delete(cid); else s.add(cid)
  pinnedIds.value = s
  localStorage.setItem('mk-pinned', JSON.stringify([...s]))
}

export const filteredConvs = computed(() => {
  return [] // computed in App.vue with searchQuery
})

export async function loadConvs() {
  const d = await get('/conversations')
  if (d) convs.value = d
}

const isLocal = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost'
const API = import.meta.env.DEV
  ? ''
  : (isLocal ? 'http://127.0.0.1:8000' : window.location.origin)

export async function checkAuth() {
  try {
    const r = await fetch(API + '/api/auth/me', { credentials: 'include' })
    if (r.ok) {
      user.value = await r.json()
      authed.value = true
      await loadConvs()
    }
  } catch (e) { /* not logged in */ }
}

export async function logout() {
  await fetch(API + '/api/auth/logout', { method: 'POST', credentials: 'include' })
  authed.value = false
  user.value = { email: '', nickname: '' }
  convs.value = []
  msgs.value = []
  activeId.value = null
}
