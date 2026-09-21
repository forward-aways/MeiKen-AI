import { reactive, ref, computed } from 'vue'
import { TXT } from './i18n.js'
import { get, post, put, del } from './api.js'
import { API_BASE } from './api.js'
import { effectiveEffortFor, normalizeEffort, normalizeThinkMode } from './thinking.js'

export const authed = ref(false)
export const user = ref({ email: '', nickname: '' })
export const convs = ref([])
export const activeId = ref(null)
export const msgs = ref([])
export const input = ref('')
export const busy = ref(false)
export const agents = ref([])
export const currentAgentId = ref(null)
export const mode = ref(localStorage.getItem('mk-mode') || 'general')  // code | work | general
export const MODE_DEFAULT_AGENTS = { code: 'coder', work: 'general', general: 'general' }
export const view = ref('chat')  // chat | skills | kb | agents | profile | search
export function setView(v) { view.value = v }

// Model / thinking capsules (persisted).
export const modelOverride = ref(localStorage.getItem('mk-model') || null)  // null(follow agent) | model name
// 思考强度（左胶囊）：fast=关闭思考 | standard=均衡 | deep=深入
export const thinkMode = ref(normalizeThinkMode(localStorage.getItem('mk-thinkmode')))
// 推理强度（右胶囊）：default=跟随思考强度 | low | mid | high
export const effortSel = ref(normalizeEffort(localStorage.getItem('mk-effort')))
export const providers = ref([])  // [{id,name,base_url,key_configured,key_masked,deepseek_compat,models,is_builtin,enabled}]

/** 计算本次请求的思考配置（映射规则见 thinking.js，唯一事实源）。 */
export function effectiveEffort() {
  return effectiveEffortFor(thinkMode.value, effortSel.value)
}

export async function loadProviders() {
  const d = await get('/providers')
  if (d) providers.value = d
}

/** Model list grouped by provider for the capsule menus (only enabled providers). */
export const modelGroups = computed(() => {
  return providers.value
    .filter((p) => p.enabled)
    .map((p) => ({ ...p, models: p.models || [] }))
})

export function setModelOverride(m) {
  modelOverride.value = m || null
  localStorage.setItem('mk-model', m || '')
}

export function setThinkMode(v) {
  thinkMode.value = v
  localStorage.setItem('mk-thinkmode', v)
}

export function setEffortSel(v) {
  effortSel.value = v
  localStorage.setItem('mk-effort', v)
}

// Expert-graph node positions (agentId -> {x, y} in 900x560 space), persisted.
export const graphPos = reactive(JSON.parse(localStorage.getItem('mk-graphpos') || '{}'))
export function saveGraphPos() {
  localStorage.setItem('mk-graphpos', JSON.stringify(graphPos))
}
export const kbFiles = ref([])
export let abortCtrl = null

export const theme = ref(localStorage.getItem('mk-theme') || 'light')
export const locale = ref(localStorage.getItem('mk-locale') || 'zh')
export const sidebarCollapsed = ref(false)
export const showCollapsedWidget = ref(false)

// 上下文用量：取"最近一次 LLM 调用"的 total_tokens（当前上下文占用），
// 而非历史累加——每轮请求都会重发全部历史，累加会重复计数（见 ADR-20260921）。
export const CONTEXT_WINDOW = 1_000_000  // DeepSeek V4 (flash & pro) 1M-token context
export const contextTokens = ref(0)
export function setContextTokens(n) {
  const v = Number(n) || 0
  // I6：未上报（0）不得覆盖已有值，避免用量回退为 0
  if (v <= 0) return
  contextTokens.value = v
}
export function resetContextTokens() {
  contextTokens.value = 0
}

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

export async function loadAll() {
  await Promise.all([loadConvs(), loadProviders()])
}

export async function loadKBFiles() {
  const d = await get('/kb/files')
  if (d) kbFiles.value = d
}

export async function uploadKBFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const r = await fetch(API_BASE + '/kb/upload', { method: 'POST', body: formData, credentials: 'include' })
  if (r.ok) {
    const data = await r.json()
    await loadKBFiles()
    return data
  }
  return null
}

export async function deleteKBFile(fileId) {
  await del('/kb/files/' + fileId)
  await loadKBFiles()
}

export async function uploadTempFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const r = await fetch(API_BASE + '/kb/upload?scope=temp', { method: 'POST', body: formData, credentials: 'include' })
  if (r.ok) {
    return await r.json()
  }
  return null
}

export async function uploadImage(file) {
  const formData = new FormData()
  formData.append('file', file)
  const r = await fetch(API_BASE + '/images', { method: 'POST', body: formData, credentials: 'include' })
  if (r.ok) return await r.json()
  const err = await r.json().catch(() => ({}))
  throw new Error(err.detail || 'upload failed')
}

export async function deleteTempFile(fileId) {
  await del('/kb/files/' + fileId)
}

export async function loadAgents() {
  const d = await get('/agents')
  if (d) agents.value = d
}

export function setMode(v) {
  if (!MODE_DEFAULT_AGENTS[v]) return
  mode.value = v
  localStorage.setItem('mk-mode', v)
}

export function currentAgent() {
  const sel = agents.value.find((a) => a.id === currentAgentId.value)
  if (sel) return sel
  const def = agents.value.find((a) => a.name === MODE_DEFAULT_AGENTS[mode.value])
  return def || agents.value.find((a) => a.name === 'general')
}

export function setCurrentAgent(id) {
  currentAgentId.value = id || null
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
