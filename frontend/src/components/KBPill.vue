<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { t, kbFiles, loadKBFiles, uploadKBFile, deleteKBFile } from '../store.js'

const showKbMenu = ref(false)
const uploading = ref(false)
const fileInput = ref(null)
const kbMenuRef = ref(null)

function toggleKbMenu() {
  showKbMenu.value = !showKbMenu.value
  if (showKbMenu.value) loadKBFiles()
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
}

function handleClickOutside(e) {
  if (kbMenuRef.value && !kbMenuRef.value.contains(e.target)) {
    showKbMenu.value = false
  }
}

onMounted(() => { document.addEventListener('click', handleClickOutside) })
onUnmounted(() => { document.removeEventListener('click', handleClickOutside) })
</script>

<template>
  <div class="kb-wrapper" ref="kbMenuRef">
    <button class="search-capsule glass-pill" :class="{ active: showKbMenu }" @click="toggleKbMenu">
      {{ t('rag') }}
      <svg class="kb-chevron" :class="{ open: showKbMenu }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
    </button>

    <div v-if="showKbMenu" class="kb-dropdown glass-pop">
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
    <input ref="fileInput" type="file" accept=".txt,.md,.pdf,.docx" @change="onFileChange" style="display:none" />
  </div>
</template>

<style scoped>
.kb-wrapper { position: relative; }
/* 材质来自全局 .glass-pill（凸起毛玻璃）；此处只保留布局 */
.search-capsule {
  padding: 5px 14px;
  border-radius: 20px;
  font-size: 12.5px;
  font-family: var(--font);
  cursor: pointer;
  white-space: nowrap;
  line-height: 1.4;
  display: flex;
  align-items: center;
  gap: 4px;
}
.kb-chevron { transition: transform .2s var(--ease); }
.kb-chevron.open { transform: rotate(180deg); }

.kb-dropdown {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 0;
  width: 280px;
  border-radius: var(--radius);
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

@media (max-width: 768px) {
  .search-capsule { padding: 4px 9px; font-size: 11px; }
  .kb-dropdown { width: calc(100vw - 32px); max-width: 280px; }
}
</style>