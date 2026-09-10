<script setup>
import { ref, onMounted } from 'vue'
import { t, kbFiles, loadKBFiles, uploadKBFile, deleteKBFile } from '../store.js'

const fileInput = ref(null)
const uploading = ref(false)

async function onFileChange(e) {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 10 * 1024 * 1024) { alert(t('fileTooBig')); e.target.value = ''; return }
  uploading.value = true
  await uploadKBFile(file)
  uploading.value = false
  e.target.value = ''
}

function fmtSize(n) {
  if (n > 1048576) return (n / 1048576).toFixed(1) + ' MB'
  return Math.max(1, Math.round(n / 1024)) + ' KB'
}

function fmtTime(s) {
  return (s || '').slice(0, 16).replace('T', ' ')
}

onMounted(loadKBFiles)
</script>

<template>
  <div class="kb-page">
    <div class="kb-head">
      <div class="kb-title">
        <h2>{{ t('kbTitle') }}</h2>
        <p class="kb-hint">{{ t('kbHint') }}</p>
      </div>
      <button class="btn primary" @click="fileInput?.click()" :disabled="uploading">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        {{ uploading ? '…' : t('uploadKb') }}
      </button>
      <input ref="fileInput" type="file" accept=".txt,.md,.pdf,.docx" @change="onFileChange" style="display:none" />
    </div>

    <div class="kb-list" v-if="kbFiles.length">
      <div v-for="f in kbFiles" :key="f.id" class="kb-item">
        <span class="kb-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></span>
        <div class="kb-meta">
          <div class="kb-name">{{ f.filename }}</div>
          <div class="kb-sub">{{ fmtSize(f.size) }} · {{ fmtTime(f.created_at) }}</div>
        </div>
        <button class="kb-del" :title="t('del')" @click="deleteKBFile(f.id)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </div>
    </div>
    <div class="kb-empty" v-else>{{ t('kbEmpty') }}</div>
  </div>
</template>

<style scoped>
.kb-page { max-width: 1080px; margin: 0 auto; padding: 40px 28px 60px; width: 100%; box-sizing: border-box; }
.kb-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }
.kb-title h2 { font-size: 22px; font-weight: 700; margin: 0 0 6px; }
.kb-hint { color: var(--text-muted); font-size: 13px; margin: 0; }
.kb-list { display: flex; flex-direction: column; gap: 8px; }
.kb-item {
  display: flex; align-items: center; gap: 12px; padding: 11px 14px;
  border: 1px solid rgba(255,255,255,.95); border-radius: var(--radius-lg);
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.04'/></svg>"),
    linear-gradient(180deg, rgba(255,255,255,.99), rgba(246,245,255,.975));
  backdrop-filter: blur(36px) saturate(180%);
  -webkit-backdrop-filter: blur(36px) saturate(180%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,1),
    inset 0 -1px 0 rgba(20,18,60,.05),
    0 1px 2px rgba(20,18,60,.06),
    0 8px 20px rgba(20,18,60,.12),
    0 22px 48px rgba(20,18,60,.16);
  transition: border-color .18s var(--ease), box-shadow .18s var(--ease), transform .18s var(--ease);
}
.kb-item:hover {
  border-color: rgba(91,87,210,.4);
  transform: translateY(-1px);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,1),
    inset 0 -1px 0 rgba(20,18,60,.05),
    0 2px 4px rgba(20,18,60,.07),
    0 12px 26px rgba(91,87,210,.14),
    0 28px 56px rgba(20,18,60,.18);
}
[data-theme="dark"] .kb-item {
  border-color: rgba(255,255,255,.14);
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.04'/></svg>"),
    linear-gradient(180deg, rgba(50,54,82,.99), rgba(36,39,62,.975));
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.1),
    inset 0 -1px 0 rgba(0,0,0,.35),
    0 1px 2px rgba(0,0,0,.25),
    0 10px 24px rgba(0,0,0,.35),
    0 26px 56px rgba(0,0,0,.45);
}
[data-theme="dark"] .kb-item:hover {
  border-color: rgba(126,121,247,.45);
  transform: translateY(-1px);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.12),
    inset 0 -1px 0 rgba(0,0,0,.35),
    0 2px 4px rgba(0,0,0,.3),
    0 14px 30px rgba(0,0,0,.4),
    0 32px 64px rgba(0,0,0,.5);
}
.kb-icon { color: var(--accent); display: flex; }
.kb-meta { flex: 1; min-width: 0; }
.kb-name { font-size: 13.5px; font-weight: 600; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kb-sub { font-size: 11.5px; color: var(--text-muted); margin-top: 2px; }
.kb-del { width: 30px; height: 30px; border-radius: 8px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .15s; flex-shrink: 0; }
.kb-del:hover { background: rgba(239,68,68,.12); color: #ef4444; }
.kb-empty {
  text-align: center; color: var(--text-muted); font-size: 13px; padding: 3rem 0;
  border: 1.5px dashed var(--border-strong); border-radius: var(--radius-lg);
  background: linear-gradient(180deg, rgba(255,255,255,.5), rgba(255,255,255,.3));
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}
[data-theme="dark"] .kb-empty { background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02)); }
</style>