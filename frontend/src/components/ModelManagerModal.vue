<script setup>
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import { t, providers, loadProviders } from '../store.js'
import { patch, del, fetchRaw } from '../api.js'

const emit = defineEmits(['close'])

// Always start from the freshest provider list (the card grid depends on it).
onMounted(loadProviders)

const PRESETS = [
  { name: 'DeepSeek', base_url: 'https://api.deepseek.com', deepseek_compat: true, models: ['deepseek-flash', 'deepseek-v4-flash', 'deepseek-v4-pro'], recommended: true },
  { name: 'OpenAI', base_url: 'https://api.openai.com/v1', deepseek_compat: false, models: ['gpt-4o', 'gpt-4o-mini'] },
  { name: '智谱 GLM', base_url: 'https://open.bigmodel.cn/api/paas/v4', deepseek_compat: false, models: ['glm-4-plus', 'glm-4-flash'] },
  { name: 'Kimi', base_url: 'https://api.moonshot.cn/v1', deepseek_compat: false, models: ['moonshot-v1-8k', 'moonshot-v1-32k'] },
  { name: 'OpenRouter', base_url: 'https://openrouter.ai/api/v1', deepseek_compat: false, models: ['anthropic/claude-sonnet-4', 'google/gemini-2.5-pro'] },
  { name: 'Ollama 本地', base_url: 'http://127.0.0.1:11434/v1', deepseek_compat: false, models: ['llama3.1', 'qwen2.5'] },
]

const testState = reactive({})  // pid -> { loading, ok, latency, error }

// Unified config dialog: preset -> create, existing provider -> edit.
const dialog = ref(null)  // null | { mode:'create', preset } | { mode:'edit', provider }
const dlg = reactive({ name: '', base_url: '', api_key: '', deepseek_compat: false, models: [] })
const dlgErr = ref('')
const dlgSaving = ref(false)
const dlgKeyEl = ref(null)

const isBuiltinDialog = computed(() => dialog.value?.mode === 'edit' && !!dialog.value?.provider?.is_builtin)
const dlgCanSave = computed(() => !dlgSaving.value)

// Custom configuration (collapsible, collapsed by default) — blank create form.
const customOpen = ref(false)
const custom = reactive({ name: '', base_url: '', api_key: '', deepseek_compat: false, models: [] })
const customErr = ref('')
const customSaving = ref(false)

function providerByName(name) {
  return providers.value.find((p) => p.name.toLowerCase() === (name || '').toLowerCase())
}

const unaddedPresets = computed(() => PRESETS.filter((pr) => !providerByName(pr.name)))

function blankModels() {
  return [{ name: '', context_window: '' }]
}

// -- unified config dialog --
function openPreset(pr) {
  dialog.value = { mode: 'create', preset: pr }
  dlgErr.value = ''
  dlg.name = pr.name
  dlg.base_url = pr.base_url
  dlg.api_key = ''
  dlg.deepseek_compat = !!pr.deepseek_compat
  dlg.models = pr.models.map((n) => ({ name: n, context_window: '' }))
}

function openEdit(p) {
  dialog.value = { mode: 'edit', provider: p }
  dlgErr.value = ''
  dlg.name = p.name
  dlg.base_url = p.base_url
  dlg.api_key = ''
  dlg.deepseek_compat = !!p.deepseek_compat
  dlg.models = (p.models || []).map((m) => ({ name: m.name, context_window: m.context_window || '' }))
  if (!dlg.models.length) dlg.models = blankModels()
  nextTick(() => dlgKeyEl.value?.focus())
}

function addDlgRow() {
  dlg.models.push({ name: '', context_window: '' })
}

function delDlgRow(i) {
  dlg.models.splice(i, 1)
}

async function saveDialog() {
  const d = dialog.value
  if (!d || dlgSaving.value) return
  dlgErr.value = ''
  const isBuiltin = isBuiltinDialog.value
  let body
  if (isBuiltin) {
    // Built-ins allow an empty key on purpose: leave blank to keep it
    // unconfigured (e.g. fresh server deploys), or clear an existing key.
    const nextKey = dlg.api_key.trim()
    if (!nextKey && d.provider.key_configured && !confirm(t('confirmClearKey'))) return
    body = { api_key: nextKey }
  } else {
    const models = dlg.models
      .filter((m) => m.name.trim())
      .map((m) => ({ name: m.name.trim(), context_window: m.context_window ? Number(m.context_window) : null }))
    if (!models.length) { dlgErr.value = t('modelRows') + ' ✕'; return }
    body = { models }
    if (dlg.api_key.trim()) body.api_key = dlg.api_key.trim()
    if (d.mode === 'create') {
      // Creation carries the preset identity; edits never touch name/url/compat.
      body.name = d.preset.name
      body.base_url = d.preset.base_url
      body.deepseek_compat = !!d.preset.deepseek_compat
    }
  }
  dlgSaving.value = true
  try {
    const isCreate = d.mode === 'create'
    const path = isCreate ? '/providers' : `/providers/${d.provider.id}`
    const r = await fetchRaw(path, {
      method: isCreate ? 'POST' : 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!r.ok) {
      const e = await r.json().catch(() => ({}))
      if (r.status === 409 && isCreate) {
        // Duplicate name: the provider already exists — refresh so its card
        // shows up in the grid, and guide the user there instead.
        dlgErr.value = t('providerExistsHint')
        await loadProviders()
        return
      }
      dlgErr.value = e.detail || t('providerSaveErr')
      return
    }
    await loadProviders()
    dialog.value = null
  } finally {
    dlgSaving.value = false
  }
}

// -- custom configuration (create only) --
function toggleCustom() {
  customOpen.value = !customOpen.value
  if (customOpen.value && !custom.name && !custom.base_url) resetCustom()
}

function resetCustom() {
  customErr.value = ''
  custom.name = ''
  custom.base_url = ''
  custom.api_key = ''
  custom.deepseek_compat = false
  custom.models = blankModels()
}

function addCustomRow() {
  custom.models.push({ name: '', context_window: '' })
}

function delCustomRow(i) {
  custom.models.splice(i, 1)
}

async function saveCustom() {
  customErr.value = ''
  if (!custom.name.trim()) { customErr.value = t('providerName') + ' ✕'; return }
  if (!/^https?:\/\/\S+$/.test(custom.base_url.trim())) { customErr.value = t('baseUrl') + ' ✕'; return }
  const models = custom.models
    .filter((m) => m.name.trim())
    .map((m) => ({ name: m.name.trim(), context_window: m.context_window ? Number(m.context_window) : null }))
  if (!models.length) { customErr.value = t('modelRows') + ' ✕'; return }
  const body = {
    name: custom.name.trim(),
    base_url: custom.base_url.trim(),
    deepseek_compat: custom.deepseek_compat,
    models,
  }
  if (custom.api_key.trim()) body.api_key = custom.api_key.trim()
  customSaving.value = true
  try {
    const r = await fetchRaw('/providers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!r.ok) {
      const e = await r.json().catch(() => ({}))
      customErr.value = e.detail || t('providerSaveErr')
      return
    }
    await loadProviders()
    resetCustom()
    customOpen.value = false
  } finally {
    customSaving.value = false
  }
}

// -- card ops --
async function toggleEnabled(p) {
  await patch(`/providers/${p.id}`, { enabled: !p.enabled })
  await loadProviders()
}

async function remove(p) {
  if (!confirm(t('confirmDelProvider').replace('{name}', p.name))) return
  await del(`/providers/${p.id}`)
  await loadProviders()
}

async function testConn(p) {
  testState[p.id] = { loading: true }
  try {
    const r = await fetchRaw(`/providers/${p.id}/test`, { method: 'POST' })
    const d = await r.json().catch(() => ({}))
    if (r.ok && d.ok) {
      testState[p.id] = { loading: false, ok: true, latency: d.latency_ms }
    } else if (!r.ok) {
      testState[p.id] = { loading: false, ok: false, error: d.detail || t('testFail') }
    } else {
      testState[p.id] = { loading: false, ok: false, error: d.error || t('testFail') }
    }
  } catch {
    testState[p.id] = { loading: false, ok: false, error: t('testFail') }
  }
}

function close() {
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div class="pmm-overlay" @click.self="close">
      <div class="pmm-card glass-dialog">
        <div class="pmm-head">
          <h3 class="pmm-title">{{ t('providerTitle') }}</h3>
          <button class="pmm-x" @click="close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <div class="pmm-scroll">
          <!-- One grid: configured providers first, then not-yet-added presets -->
          <div class="pmm-grid">
            <div v-for="p in providers" :key="p.id" class="pmm-item configured" @click="openEdit(p)">
              <div class="pmm-item-head">
                <span class="pmm-item-name">{{ p.name }}</span>
                <span v-if="p.is_builtin" class="pmm-badge builtin">{{ t('builtinProvider') }}</span>
                <span class="pmm-dot" :class="p.key_configured ? 'on' : 'off'" :title="p.key_configured ? t('keyConfigured') : t('keyNotSet')"></span>
              </div>
              <div class="pmm-item-url">{{ p.base_url }}</div>
              <div class="pmm-item-models">
                <span v-for="m in p.models.slice(0, 3)" :key="m.name" class="pmm-chip">{{ m.name }}</span>
                <span v-if="p.models.length > 3" class="pmm-chip more">+{{ p.models.length - 3 }}</span>
              </div>
              <div class="pmm-item-ops" @click.stop>
                <button class="pmm-op" :disabled="testState[p.id]?.loading" @click="testConn(p)">
                  {{ testState[p.id]?.loading ? t('testing') : t('testConn') }}
                </button>
                <span v-if="testState[p.id] && !testState[p.id].loading && testState[p.id].ok" class="pmm-test ok">{{ t('testOk').replace('{ms}', testState[p.id].latency) }}</span>
                <span v-else-if="testState[p.id] && !testState[p.id].loading && testState[p.id].error" class="pmm-test fail">{{ testState[p.id].error }}</span>
                <span class="pmm-spacer"></span>
                <button class="pmm-switch" :class="{ on: p.enabled }" :title="p.enabled ? t('providerEnabled') : t('providerDisabled')" @click="toggleEnabled(p)">
                  <span class="pmm-knob"></span>
                </button>
                <button v-if="!p.is_builtin" class="pmm-op del" @click="remove(p)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </div>
            </div>

            <button v-for="pr in unaddedPresets" :key="pr.name" class="pmm-item preset" @click="openPreset(pr)">
              <div class="pmm-item-head">
                <span class="pmm-item-name">{{ pr.name }}</span>
                <span v-if="pr.recommended" class="pmm-rec">{{ t('recommended') }}</span>
              </div>
              <div class="pmm-item-url">{{ pr.base_url }}</div>
              <div class="pmm-item-hint">{{ t('clickToConfigure') }}</div>
            </button>
          </div>

          <!-- Custom configuration (collapsible, collapsed by default) -->
          <button class="pmm-collapse-head" @click="toggleCustom">
            <svg class="pmm-collapse-chev" :class="{ open: customOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            <span class="pmm-collapse-title">{{ t('customConfig') }}</span>
            <span class="pmm-collapse-sub">{{ t('customConfigHint') }}</span>
          </button>

          <div v-if="customOpen" class="pmm-custom-body">
            <label class="pmm-field">
              <span class="pmm-label">{{ t('providerName') }}</span>
              <input v-model="custom.name" class="pmm-input" :placeholder="t('providerNamePh')" maxlength="40" />
            </label>
            <label class="pmm-field">
              <span class="pmm-label">{{ t('baseUrl') }}</span>
              <input v-model="custom.base_url" class="pmm-input" :placeholder="t('baseUrlPh')" maxlength="500" />
            </label>
            <label class="pmm-field">
              <span class="pmm-label">{{ t('apiKey') }}</span>
              <input v-model="custom.api_key" class="pmm-input" type="password" :placeholder="t('apiKeyPh')" maxlength="500" autocomplete="off" />
            </label>
            <div class="pmm-switch-row">
              <div>
                <span class="pmm-label" style="display:block;margin-bottom:2px">{{ t('deepseekStyle') }}</span>
                <span class="pmm-hint">{{ t('deepseekStyleHint') }}</span>
              </div>
              <button class="pmm-switch" :class="{ on: custom.deepseek_compat }" @click="custom.deepseek_compat = !custom.deepseek_compat">
                <span class="pmm-knob"></span>
              </button>
            </div>
            <div class="pmm-models">
              <div class="pmm-models-head">
                <span class="pmm-label">{{ t('modelRows') }}</span>
                <button class="pmm-add-row" @click="addCustomRow">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  {{ t('addModelRow') }}
                </button>
              </div>
              <div v-for="(m, i) in custom.models" :key="i" class="pmm-model-row">
                <input v-model="m.name" class="pmm-input" :placeholder="t('modelNameCol')" maxlength="128" />
                <input v-model="m.context_window" class="pmm-input pmm-ctx" type="number" min="0" :placeholder="t('ctxWinCol')" />
                <button class="pmm-row-del" @click="delCustomRow(i)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
            </div>
            <p v-if="customErr" class="pmm-err">{{ customErr }}</p>
            <div class="pmm-actions">
              <button class="pmm-btn" @click="resetCustom">{{ t('cancel') }}</button>
              <button class="pmm-btn primary" :disabled="customSaving" @click="saveCustom">{{ customSaving ? '…' : t('save') }}</button>
            </div>
          </div>
        </div>

        <!-- Unified config dialog: API key + models only -->
        <div v-if="dialog" class="pmm-dlg-overlay" @click.self="dialog = null">
          <div class="pmm-dlg-card glass-dialog">
            <div class="pmm-dlg-title">
              {{ dialog.mode === 'create' ? t('configureProvider') : t('editProvider') }}
              <b>{{ dlg.name || dialog.preset?.name }}</b>
              <span v-if="isBuiltinDialog" class="pmm-badge builtin" style="margin-left:7px">{{ t('builtinProvider') }}</span>
            </div>
            <div v-if="dialog.mode === 'create'" class="pmm-dlg-url">{{ dialog.preset.base_url }}</div>

            <label class="pmm-field">
              <span class="pmm-label">
                {{ t('apiKey') }}
                <span v-if="dialog.mode === 'edit' && dialog.provider.key_configured" class="pmm-hint">
                  {{ dialog.provider.key_masked }} · {{ t('apiKeyKeepHint') }}
                </span>
              </span>
              <input ref="dlgKeyEl" v-model="dlg.api_key" class="pmm-input" type="password" :placeholder="t('apiKeyPh')" maxlength="500" autocomplete="off" @keydown.enter="saveDialog" />
            </label>

            <div class="pmm-models">
              <div class="pmm-models-head">
                <span class="pmm-label">{{ t('modelRows') }}</span>
                <button v-if="!isBuiltinDialog" class="pmm-add-row" @click="addDlgRow">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  {{ t('addModelRow') }}
                </button>
              </div>
              <template v-if="isBuiltinDialog">
                <div class="pmm-builtin-hint">
                  <span v-for="m in dlg.models" :key="m.name" class="pmm-chip">{{ m.name }}</span>
                  <span class="pmm-hint">{{ t('builtinModelsHint') }}</span>
                </div>
              </template>
              <template v-else>
                <div v-for="(m, i) in dlg.models" :key="i" class="pmm-model-row">
                  <input v-model="m.name" class="pmm-input" :placeholder="t('modelNameCol')" maxlength="128" />
                  <input v-model="m.context_window" class="pmm-input pmm-ctx" type="number" min="0" :placeholder="t('ctxWinCol')" />
                  <button class="pmm-row-del" @click="delDlgRow(i)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                </div>
              </template>
            </div>

            <p v-if="dlgErr" class="pmm-err">{{ dlgErr }}</p>
            <div class="pmm-dlg-actions">
              <button class="pmm-btn" @click="dialog = null">{{ t('cancel') }}</button>
              <button class="pmm-btn primary" :disabled="!dlgCanSave" @click="saveDialog">{{ dlgSaving ? '…' : t('save') }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.pmm-overlay {
  position: fixed; inset: 0; z-index: 90;
  /* 遮罩层不使用 backdrop-filter：它会创建 backdrop root，令卡片的后背模糊失效 */
  background: rgba(15,17,27,.46);
  display: flex; align-items: center; justify-content: center; padding: 1rem;
  animation: fadeIn .18s ease;
}
/* 材质来自全局 .glass-dialog（近实心毛玻璃），此处只保留布局 */
.pmm-card {
  position: relative;
  width: min(720px, 100%); max-height: 84vh; display: flex; flex-direction: column;
  border-radius: 18px; padding: 22px 24px;
}
.pmm-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.pmm-title { font-size: 17px; font-weight: 700; margin: 0; }
.pmm-x {
  width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
  border: none; border-radius: 8px; background: transparent; color: var(--text-muted); cursor: pointer;
}
.pmm-x:hover { background: rgba(91,87,210,.1); color: var(--text); }

.pmm-scroll { overflow-y: auto; padding: 2px; margin: 0 -2px; }

/* Unified card grid */
.pmm-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.pmm-item {
  position: relative;
  display: flex; flex-direction: column; gap: 7px; text-align: left; min-width: 0;
  padding: 13px 15px; border-radius: 14px;
  border: 1px solid rgba(255,255,255,.65);
  background:
    var(--noise-subtle),
    linear-gradient(180deg, rgba(255,255,255,.55), rgba(255,255,255,.26));
  backdrop-filter: blur(18px) saturate(180%);
  -webkit-backdrop-filter: blur(18px) saturate(180%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.72), 0 3px 12px rgba(20,18,60,.06);
  font-family: var(--font);
  transition: border-color .18s var(--ease), box-shadow .18s var(--ease), transform .18s var(--ease);
}
[data-theme="dark"] .pmm-item {
  border-color: rgba(255,255,255,.1);
  background:
    var(--noise-medium),
    linear-gradient(180deg, rgba(255,255,255,.09), rgba(255,255,255,.03));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.1), 0 3px 12px rgba(0,0,0,.25);
}
.pmm-item.configured { cursor: pointer; }
.pmm-item.configured:hover { border-color: rgba(91,87,210,.45); box-shadow: inset 0 1px 0 rgba(255,255,255,.8), 0 6px 20px rgba(91,87,210,.15); transform: translateY(-1px); }
[data-theme="dark"] .pmm-item.configured:hover { border-color: rgba(126,121,247,.5); box-shadow: inset 0 1px 0 rgba(255,255,255,.14), 0 6px 20px rgba(0,0,0,.38); }
.pmm-item.preset { cursor: pointer; border-style: dashed; }
.pmm-item.preset:hover { border-color: var(--accent); border-style: solid; box-shadow: inset 0 1px 0 rgba(255,255,255,.8), 0 6px 20px rgba(91,87,210,.14); transform: translateY(-1px); }
.pmm-item-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.pmm-item-name { font-weight: 700; font-size: 14.5px; color: var(--text); }
.pmm-badge { font-size: 10.5px; padding: 2px 8px; border-radius: 999px; font-weight: 600; }
.pmm-badge.builtin { background: rgba(91,87,210,.12); color: var(--accent); }
.pmm-dot { width: 8px; height: 8px; border-radius: 50%; margin-left: auto; flex-shrink: 0; }
.pmm-dot.on { background: #22c55e; box-shadow: 0 0 6px rgba(34,197,94,.6); }
.pmm-dot.off { background: #ef4444; box-shadow: 0 0 6px rgba(239,68,68,.5); }
.pmm-item-url {
  font-size: 11px; color: var(--text-muted); font-family: ui-monospace, monospace;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.pmm-item-models { display: flex; flex-wrap: wrap; gap: 6px; }
.pmm-chip {
  font-size: 11px; padding: 3px 9px; border-radius: 7px; font-weight: 600;
  background:
    var(--noise-medium),
    linear-gradient(180deg, rgba(124,121,247,.14), rgba(91,87,210,.07));
  color: var(--text-secondary);
  border: 1px solid rgba(91,87,210,.2);
  backdrop-filter: blur(10px) saturate(160%);
  -webkit-backdrop-filter: blur(10px) saturate(160%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.5);
}
.pmm-chip.more { color: var(--text-muted); }
.pmm-item-hint { font-size: 11.5px; color: var(--accent); opacity: .85; }
.pmm-rec {
  font-size: 9.5px; font-weight: 700; padding: 1px 7px; border-radius: 999px;
  background: linear-gradient(135deg, rgba(124,121,247,.9), rgba(91,87,210,.85));
  color: #fff; box-shadow: 0 1px 6px rgba(91,87,210,.4);
}
.pmm-item-ops { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 2px; }
.pmm-op {
  display: flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 8px;
  border: 1px solid var(--border-strong); background: transparent; color: var(--text-secondary);
  font-size: 11.5px; font-family: var(--font); cursor: pointer; transition: all .15s var(--ease);
}
.pmm-op:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.pmm-op.del:hover { border-color: #ef4444; color: #ef4444; }
.pmm-op:disabled { opacity: .5; cursor: default; }
.pmm-test { font-size: 11px; font-weight: 600; }
.pmm-test.ok { color: #16a34a; }
.pmm-test.fail { color: #dc2626; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pmm-spacer { flex: 1; }

/* Toggle switch */
.pmm-switch {
  position: relative; width: 38px; height: 21px; border-radius: 999px;
  border: 1px solid var(--border-strong); background: rgba(120,124,150,.16);
  cursor: pointer; transition: all .25s var(--ease); flex-shrink: 0; padding: 0;
}
[data-theme="dark"] .pmm-switch { background: rgba(255,255,255,.12); }
.pmm-switch.on {
  border-color: rgba(91,87,210,.5);
  background:
    var(--noise-medium),
    linear-gradient(180deg, rgba(124,121,247,.85), rgba(91,87,210,.8));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.5), 0 2px 8px rgba(91,87,210,.35);
}
.pmm-knob {
  position: absolute; top: 2px; left: 2px; width: 15px; height: 15px; border-radius: 50%;
  background: linear-gradient(180deg, #fff, #eef);
  box-shadow: 0 1px 3px rgba(20,18,60,.3);
  transition: transform .25s var(--spring);
}
.pmm-switch.on .pmm-knob { transform: translateX(17px); }

/* Custom configuration collapse */
.pmm-collapse-head {
  display: flex; align-items: center; gap: 7px; width: 100%;
  margin-top: 16px; padding: 10px 12px;
  border: 1px dashed var(--border-strong); border-radius: 12px;
  background: transparent; cursor: pointer; font-family: var(--font);
  transition: all .15s var(--ease);
}
.pmm-collapse-head:hover { border-color: var(--accent); background: rgba(91,87,210,.04); }
.pmm-collapse-chev { color: var(--text-muted); transition: transform .2s var(--ease); flex-shrink: 0; }
.pmm-collapse-chev.open { transform: rotate(90deg); }
.pmm-collapse-title { font-size: 12.5px; font-weight: 650; color: var(--text-secondary); }
.pmm-collapse-sub { font-size: 11px; color: var(--text-muted); margin-left: auto; }
.pmm-custom-body { padding: 14px 2px 2px; }

/* Form fields (shared by custom + dialog) */
.pmm-field { display: flex; flex-direction: column; gap: 5px; margin-bottom: 12px; }
.pmm-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.pmm-hint { font-size: 10.5px; color: var(--text-muted); margin-left: 6px; font-weight: 400; }
.pmm-input {
  padding: 8px 11px; border-radius: 10px; border: 1px solid var(--border-strong);
  background: var(--surface); color: var(--text); font-size: 13px; font-family: var(--font); outline: none;
  transition: border-color .15s var(--ease);
}
.pmm-input:focus { border-color: var(--accent); }
.pmm-switch-row {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  margin-bottom: 14px; padding: 10px 12px; border-radius: 10px;
  border: 1px solid rgba(255,255,255,.6);
  background: linear-gradient(180deg, rgba(255,255,255,.35), rgba(255,255,255,.15));
  backdrop-filter: blur(14px) saturate(170%);
  -webkit-backdrop-filter: blur(14px) saturate(170%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.6);
}
[data-theme="dark"] .pmm-switch-row {
  border-color: rgba(255,255,255,.09);
  background: linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.025));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08);
}
.pmm-models { margin-bottom: 10px; }
.pmm-models-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.pmm-add-row {
  display: flex; align-items: center; gap: 4px; border: none; background: transparent;
  color: var(--accent); font-size: 12px; font-family: var(--font); font-weight: 600; cursor: pointer;
}
.pmm-model-row { display: flex; gap: 8px; margin-bottom: 8px; }
.pmm-model-row .pmm-input { flex: 1; }
.pmm-model-row .pmm-ctx { flex: 0 0 130px; }
.pmm-row-del {
  width: 30px; flex-shrink: 0; border: 1px solid transparent; border-radius: 8px;
  background: transparent; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.pmm-row-del:hover { color: #ef4444; background: rgba(239,68,68,.08); }
.pmm-err { color: #dc2626; font-size: 12px; margin: 0 0 10px; }
.pmm-actions { display: flex; justify-content: flex-end; gap: 8px; }
.pmm-builtin-hint { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.pmm-btn {
  padding: 8px 16px; border-radius: 10px; border: 1px solid var(--border-strong);
  background: transparent; color: var(--text-secondary); font-size: 13px; font-family: var(--font); cursor: pointer;
  transition: all .15s var(--ease);
}
.pmm-btn:hover { border-color: var(--accent); color: var(--accent); }
.pmm-btn.primary {
  background:
    var(--noise-medium),
    linear-gradient(180deg, rgba(124,121,247,.95), rgba(91,87,210,.9));
  border-color: rgba(91,87,210,.5); color: #fff; font-weight: 600;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.4), 0 3px 12px rgba(91,87,210,.3);
}
.pmm-btn.primary:hover { filter: brightness(1.06); color: #fff; }
.pmm-btn:disabled { opacity: .55; cursor: default; }

/* Config dialog */
.pmm-dlg-overlay {
  position: absolute; inset: -1px; z-index: 5;  /* -1px: cover the parent card's border too */
  /* 遮罩层不使用 backdrop-filter（否则子卡片的后背模糊会失效） */
  background: rgba(15,17,27,.46);
  display: flex; align-items: center; justify-content: center; padding: 1.5rem;
  border-radius: 18px; animation: fadeIn .16s ease;
}
/* 材质来自全局 .glass-dialog，此处只保留布局 */
.pmm-dlg-card {
  width: min(430px, 100%); max-height: 100%; overflow-y: auto;
  border-radius: 16px; padding: 20px 22px; box-sizing: border-box;
  animation: dlgIn .2s var(--spring) both;
}
@keyframes dlgIn { from { opacity: 0; transform: translateY(10px) scale(.97); } to { opacity: 1; transform: none; } }
.pmm-dlg-title { font-size: 14.5px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.pmm-dlg-title b { color: var(--text); font-size: 15.5px; margin-left: 2px; }
.pmm-dlg-url { font-size: 11.5px; color: var(--text-muted); font-family: ui-monospace, monospace; margin: 4px 0 12px; word-break: break-all; }
.pmm-dlg-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }

@media (max-width: 640px) {
  .pmm-grid { grid-template-columns: 1fr; }
  .pmm-dlg-overlay { padding: .8rem; }
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>