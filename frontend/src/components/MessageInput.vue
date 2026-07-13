<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { t, ragEnabled, kbFiles, uploadKBFile, loadKBFiles, deleteKBFile } from '../store.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  placeholder: { type: String, default: '' },
  searchEnabled: { type: Boolean, default: false },
  thinkingEnabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'update:searchEnabled', 'update:thinkingEnabled', 'send', 'stop', 'tempFile'])
const inputEl = ref(null)
const isSearchOn = ref(false)
const isThinkingOn = ref(false)
const showKbMenu = ref(false)
const uploading = ref(false)
const fileInput = ref(null)
const tempFileInput = ref(null)
const kbMenuRef = ref(null)
const tempFileName = ref('')

watch(() => props.searchEnabled, (v) => { isSearchOn.value = v }, { immediate: true })
watch(() => props.thinkingEnabled, (v) => { isThinkingOn.value = v }, { immediate: true })

function resizeTA(el) {
  el.style.height = 'auto'
  let m = parseInt(getComputedStyle(el).maxHeight) || 200
  el.style.height = Math.min(el.scrollHeight, m) + 'px'
}

function onInput(e) {
  emit('update:modelValue', e.target.value)
  resizeTA(e.target)
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (!props.disabled && props.modelValue.trim()) { emit('send'); tempFileName.value = '' }
  } else if (e.key === 'Escape') {
    if (props.disabled) emit('stop')
  }
}

function toggleSearch() {
  isSearchOn.value = !isSearchOn.value
  emit('update:searchEnabled', isSearchOn.value)
}

function toggleThinking() {
  isThinkingOn.value = !isThinkingOn.value
  emit('update:thinkingEnabled', isThinkingOn.value)
}

function toggleKbMenu() {
  showKbMenu.value = !showKbMenu.value
  if (showKbMenu.value) {
    ragEnabled.value = true
    loadKBFiles()
  } else {
    ragEnabled.value = kbFiles.value.length > 0
  }
}

async function onFileChange(e) {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 10 * 1024 * 1024) {
    alert(t('fileTooBig'))
    e.target.value = ''
    return
  }
  uploading.value = true
  await uploadKBFile(file)
  uploading.value = false
  e.target.value = ''
}

async function onDelFile(fileId) {
  await deleteKBFile(fileId)
  if (!kbFiles.value.length) {
    ragEnabled.value = false
  }
}

async function onTempFileChange(e) {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 10 * 1024 * 1024) {
    alert(t('fileTooBig'))
    e.target.value = ''
    return
  }
  tempFileName.value = file.name
  emit('tempFile', file)
  e.target.value = ''
}

function clearTempFile() {
  tempFileName.value = ''
  emit('tempFile', null)
}

function handleClickOutside(e) {
  if (kbMenuRef.value && !kbMenuRef.value.contains(e.target)) {
    showKbMenu.value = false
    ragEnabled.value = kbFiles.value.length > 0
  }
}

onMounted(() => { document.addEventListener('click', handleClickOutside) })
onUnmounted(() => { document.removeEventListener('click', handleClickOutside) })

watch(() => props.modelValue, async () => {
  await nextTick()
  if (inputEl.value) resizeTA(inputEl.value)
})
</script>

<template>
  <div class="input-row">
    <div class="input-inner">
      <textarea ref="inputEl" :value="modelValue" :placeholder="placeholder" @keydown="onKeydown" @input="onInput" rows="1"></textarea>
      <div class="input-toolbar">
        <button class="search-capsule" :class="{ active: isThinkingOn }" @click="toggleThinking">{{ t('deepThink') }}</button>
        <button class="search-capsule" :class="{ active: isSearchOn }" @click="toggleSearch">{{ t('searchWeb') }}</button>
        <div class="kb-wrapper" ref="kbMenuRef">
          <button class="search-capsule" :class="{ active: ragEnabled.value || showKbMenu }" @click="toggleKbMenu">
            {{ t('rag') }}
            <svg class="kb-chevron" :class="{ open: showKbMenu }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
          </button>

          <div v-if="showKbMenu" class="kb-dropdown">
            <div class="kb-dropdown-header">
              <span class="kb-dropdown-title">{{ t('kbFiles') }}</span>
              <button class="kb-upload-btn" @click="fileInput?.click()" :disabled="uploading">
                <svg v-if="!uploading" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                {{ t('uploadFile') }}
              </button>
            </div>
            <div v-if="uploading" class="kb-uploading">{{ t('uploading') || '...' }}</div>
            <div v-if="!kbFiles.length && !uploading" class="kb-empty">{{ t('noKbFiles') }}</div>
            <div v-else class="kb-list">
              <div v-for="f in kbFiles" :key="f.id" class="kb-item">
                <svg class="kb-file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                <span class="kb-filename">{{ f.filename }}</span>
                <span class="kb-chunks">{{ f.chunks }}</span>
                <button class="kb-del" @click="onDelFile(f.id)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </div>
            </div>
          </div>
        </div>
        <input ref="fileInput" type="file" accept=".txt,.md,.pdf,.docx" @change="onFileChange" style="display:none" />
        <input ref="tempFileInput" type="file" accept=".txt,.md,.pdf,.docx" @change="onTempFileChange" style="display:none" />
        <div class="toolbar-spacer"></div>
        <div v-if="tempFileName" class="temp-file-tag">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span>{{ tempFileName }}</span>
          <button class="temp-file-close" @click="clearTempFile">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="10" height="10"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <button v-if="!disabled" class="icon-btn" @click="tempFileInput?.click()" :title="t('uploadFile')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
        </button>
        <button v-if="!disabled" class="send-btn" @click="emit('send'); tempFileName = ''" :disabled="!modelValue.trim()" title="Send">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
        </button>
        <button v-if="disabled" class="stop-btn" @click="emit('stop')" title="Stop">
          <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><rect x="5" y="5" width="14" height="14" rx="2.5"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.input-row { padding: .6rem 1.5rem 1.2rem; animation: slideUp .3s var(--ease); }
@keyframes slideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.input-inner { max-width: 800px; margin: 0 auto; border-radius: var(--radius-lg); border: 1.5px solid var(--border-strong); background: var(--surface); transition: border-color .25s var(--ease), box-shadow .25s var(--ease); position: relative; }
.input-inner:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(91,87,210,.12); }
.input-inner textarea { width: 100%; padding: .68rem 1rem; border: none; outline: none; background: transparent; color: var(--text); font-size: 14.5px; font-family: var(--font); resize: none; line-height: 1.5; min-height: 56px; max-height: 200px; display: block; overflow: hidden; }
.input-inner textarea::placeholder { color: var(--text-muted); }
.input-toolbar { display: flex; align-items: center; gap: 8px; padding: 0 8px 8px 8px; }
.toolbar-spacer { flex: 1; }

.search-capsule {
  padding: 5px 14px;
  border-radius: 20px;
  border: 1.5px solid var(--border-strong);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12.5px;
  font-family: var(--font);
  cursor: pointer;
  transition: all .2s var(--ease);
  white-space: nowrap;
  line-height: 1.4;
  display: flex;
  align-items: center;
  gap: 4px;
}
.search-capsule:hover {
  background: var(--border);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,.04);
}
.search-capsule:active {
  transform: scale(.95);
  transition-duration: .08s;
}
.search-capsule.active {
  background: rgba(91, 87, 210, 0.12);
  border-color: var(--accent);
  color: var(--accent);
}
[data-theme="dark"] .search-capsule.active {
  background: rgba(126, 121, 247, 0.15);
}

.kb-wrapper { position: relative; }
.kb-chevron { transition: transform .2s var(--ease); }
.kb-chevron.open { transform: rotate(180deg); }

.kb-dropdown {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 0;
  width: 280px;
  border-radius: var(--radius);
  border: 1px solid var(--border-strong);
  background: var(--surface);
  box-shadow: var(--shadow-md);
  padding: 10px;
  z-index: 50;
  animation: kbIn .15s var(--ease);
}
@keyframes kbIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

.kb-dropdown-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.kb-dropdown-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.kb-upload-btn { display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--accent); border: none; background: none; cursor: pointer; font-family: var(--font); padding: 2px 6px; border-radius: 6px; transition: background .15s; }
.kb-upload-btn:hover { background: var(--accent-soft); }
.kb-upload-btn:disabled { opacity: .5; cursor: not-allowed; }

.kb-uploading { font-size: 12px; color: var(--text-muted); padding: 4px 0; }
.kb-empty { font-size: 12px; color: var(--text-muted); padding: 8px 0; text-align: center; }

.kb-list { display: flex; flex-direction: column; gap: 2px; max-height: 200px; overflow-y: auto; }
.kb-item { display: flex; align-items: center; gap: 6px; padding: 5px 6px; border-radius: 6px; font-size: 12px; color: var(--text-secondary); transition: background .15s; }
.kb-item:hover { background: var(--border); }
.kb-file-icon { flex-shrink: 0; color: var(--text-muted); }
.kb-filename { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kb-chunks { font-size: 10px; color: var(--text-muted); background: var(--border); padding: 1px 6px; border-radius: 8px; flex-shrink: 0; }
.kb-del { border: none; background: none; color: var(--text-muted); cursor: pointer; padding: 2px; border-radius: 4px; display: flex; flex-shrink: 0; }
.kb-del:hover { color: var(--danger); background: var(--danger-soft); }

.icon-btn { flex-shrink: 0; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 50%; border: 1.5px solid var(--border-strong); background: transparent; color: var(--text-secondary); cursor: pointer; transition: all .2s var(--ease); }
.icon-btn:hover { background: var(--border); color: var(--accent); border-color: var(--accent); transform: translateY(-1px); }
.icon-btn:active { transform: scale(.92); transition-duration: .08s; }

.temp-file-tag { display: flex; align-items: center; gap: 4px; padding: 3px 8px 3px 10px; border-radius: 16px; background: var(--accent-soft); color: var(--accent); font-size: 11.5px; max-width: 180px; animation: kbIn .15s var(--ease); }
.temp-file-tag svg { flex-shrink: 0; }
.temp-file-tag span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.temp-file-close { flex-shrink: 0; border: none; background: none; color: var(--accent); cursor: pointer; padding: 2px; border-radius: 50%; display: flex; transition: background .15s; }
.temp-file-close:hover { background: rgba(91,87,210,.2); }

.send-btn { flex-shrink: 0; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 50%; border: none; background: var(--accent); color: #fff; cursor: pointer; transition: all .2s var(--ease); box-shadow: 0 2px 10px rgba(91,87,210,.22); }
.send-btn:hover { background: var(--accent-hover); box-shadow: 0 4px 18px rgba(91,87,210,.32); transform: scale(1.06); }
.send-btn:active { transform: scale(.92); transition-duration: .08s; }
.send-btn:disabled { opacity: .4; cursor: not-allowed; transform: none; box-shadow: none; }
.stop-btn { flex-shrink: 0; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 50%; border: 1.5px solid var(--danger); background: transparent; color: var(--danger); cursor: pointer; transition: all .2s var(--ease); }
.stop-btn:hover { background: var(--danger-soft); transform: scale(1.06); }
.stop-btn:active { transform: scale(.92); transition-duration: .08s; }
</style>
