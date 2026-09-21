<template>
  <div class="skills-page">
    <div class="sp-header">
      <div>
        <h2 class="sp-title">{{ t('skillsTitle') }}</h2>
        <p class="sp-sub">{{ t('skillsSub') }}</p>
      </div>
      <div class="sp-actions">
        <button class="sp-btn" @click="fileInput.click()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          {{ t('skillUpload') }}
        </button>
        <button class="sp-btn primary" @click="openCreate">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="14" height="14" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          {{ t('skillCreate') }}
        </button>
        <input ref="fileInput" type="file" accept=".md,.txt,.docx" hidden @change="onUpload" />
      </div>
    </div>

    <div v-if="uploading" class="sp-banner">{{ t('skillUploading') }}</div>
    <div v-if="uploadErr" class="sp-banner err">{{ uploadErr }}</div>

    <div v-if="skills.length === 0 && !uploading" class="sp-empty">
      <span class="sp-empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="34" height="34" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
      </span>
      <p class="sp-empty-title">{{ t('skillEmpty') }}</p>
      <p class="sp-empty-sub">{{ t('skillEmptySub') }}</p>
    </div>

    <div v-else class="skills-grid">
      <div
        v-for="s in skills"
        :key="s.id"
        class="skill-card glass-card"
        :class="{ off: !s.enabled }"
        :style="{ '--sc': s.user_id === 0 ? '#8a86ff' : '#5b8def' }"
      >
        <span class="skill-actions" @click.stop>
          <span class="skill-src">{{ srcLabel(s) }}</span>
          <button
            class="skill-switch"
            :class="{ on: s.enabled }"
            @click="toggleEnabled(s)"
            :title="s.enabled ? t('skillDisable') : t('skillEnable')"
          >
            <span class="skill-knob"></span>
          </button>
        </span>
        <span class="skill-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
        </span>
        <span class="skill-name">{{ s.name }}</span>
        <span class="skill-desc">{{ s.description }}</span>
        <span class="skill-foot">
          <span v-if="s.user_id !== 0" class="skill-edit" @click="openEdit(s)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            {{ t('skillEdit') }}
          </span>
          <span v-if="s.user_id !== 0" class="skill-edit del" @click="remove(s)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            {{ t('skillDelete') }}
          </span>
        </span>
      </div>
    </div>

    <!-- Teleport 到 body：模态浮层不得渲染在页面容器内。
         页面容器带有入场动画残留的 transform，会成为 position:fixed 的包含块，
         导致弹窗错位、遮罩不覆盖视口（见 ADR-20260921-ModalFixedOffset）。 -->
    <Teleport to="body">
    <div v-if="formOpen" class="sp-modal" @click.self="closeForm">
      <div class="sp-modal-card glass-dialog">
        <h3 class="sp-modal-title">{{ editing ? t('skillEdit') : t('skillCreate') }}</h3>
        <label class="sp-field">
          <span class="sp-label">{{ t('skillName') }}</span>
          <input v-model="form.name" class="sp-input" :placeholder="t('skillNamePh')" :disabled="!!editing" />
        </label>
        <label class="sp-field">
          <span class="sp-label">{{ t('skillDesc') }}</span>
          <input v-model="form.description" class="sp-input" :placeholder="t('skillDescPh')" maxlength="300" />
        </label>
        <label class="sp-field">
          <span class="sp-label">{{ t('skillBody') }}</span>
          <textarea v-model="form.body" class="sp-textarea" :placeholder="t('skillBodyPh')" rows="9"></textarea>
        </label>
        <p class="sp-format">{{ t('skillFormatTitle') }}<code>---</code><code>name: …</code><code>description: …</code><code>---</code>{{ t('skillFormatHint') }}</p>
        <div class="sp-modal-actions">
          <button class="sp-btn" @click="closeForm">{{ t('skillCancel') }}</button>
          <button class="sp-btn primary" :disabled="saving" @click="save">{{ saving ? t('skillSaving') : t('skillSave') }}</button>
        </div>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { t } from '../store.js'
import { get, patch, del, fetchRaw } from '../api.js'

const emit = defineEmits(['close'])

const skills = ref([])
const uploading = ref(false)
const uploadErr = ref('')
const fileInput = ref(null)
const formOpen = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({ name: '', description: '', body: '' })

function srcLabel(s) {
  if (s.user_id === 0) return t('skillSourceBuiltin')
  return s.source === 'upload' ? t('skillSourceUpload') : t('skillSourceManual')
}

async function load() {
  skills.value = (await get('/skills')) || []
}

async function onUpload(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  uploading.value = true
  uploadErr.value = ''
  try {
    const fd = new FormData()
    fd.append('file', file)
    const r = await fetchRaw('/skills/upload', { method: 'POST', body: fd })
    if (!r.ok) {
      const err = await r.json().catch(() => ({}))
      uploadErr.value = err.detail || t('skillUploadErr')
    } else {
      await load()
    }
  } catch {
    uploadErr.value = t('skillUploadErr')
  } finally {
    uploading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.value = { name: '', description: '', body: '' }
  formOpen.value = true
}

async function openEdit(s) {
  const full = await get(`/skills/${s.id}`)
  if (!full) return
  editing.value = s
  form.value = { name: full.name, description: full.description, body: full.content || '' }
  formOpen.value = true
}

function closeForm() {
  formOpen.value = false
}

async function save() {
  saving.value = true
  try {
    const body = { name: form.value.name, description: form.value.description, body: form.value.body }
    const path = editing.value ? `/skills/${editing.value.id}` : '/skills'
    const method = editing.value ? 'PATCH' : 'POST'
    const r = await fetchRaw(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!r.ok) {
      const err = await r.json().catch(() => ({}))
      uploadErr.value = err.detail || t('skillSaveErr')
    } else {
      closeForm()
      await load()
    }
  } finally {
    saving.value = false
  }
}

async function toggleEnabled(s) {
  await patch(`/skills/${s.id}`, { enabled: !s.enabled })
  await load()
}

async function remove(s) {
  if (!confirm(t('confirmDelSkill'))) return
  await del(`/skills/${s.id}`)
  await load()
}

onMounted(load)
</script>

<style scoped>
.skills-page { max-width: 1080px; margin: 0 auto; padding: 40px 28px 60px; width: 100%; box-sizing: border-box; }
.sp-header { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 28px; gap: 16px; flex-wrap: wrap; }
.sp-title { font-size: 22px; font-weight: 700; margin: 0 0 6px; }
.sp-sub { margin: 0; color: var(--text-muted); font-size: 13px; }
.sp-actions { display: flex; gap: 8px; }
.sp-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 10px; border: 1px solid var(--border-strong);
  background: var(--surface-2); color: var(--text); font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all .18s var(--ease); font-family: var(--font);
}
.sp-btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-key); }
.sp-btn.primary {
  background: linear-gradient(135deg, #6a66f0, #8a55ea);
  border-color: transparent; color: #fff;
  box-shadow: 0 4px 14px rgba(106, 102, 240, .3);
}
.sp-btn:disabled { opacity: .5; cursor: default; }
.sp-banner {
  padding: 10px 14px; border-radius: 10px; margin-bottom: 16px;
  background: rgba(91, 141, 239, .12); border: 1px solid rgba(91, 141, 239, .3);
  color: var(--text); font-size: 13px;
}
.sp-banner.err { background: var(--danger-soft); border-color: var(--danger); color: var(--danger); }
.sp-empty { text-align: center; padding: 70px 0 80px; }
.sp-empty-icon {
  display: inline-flex; width: 74px; height: 74px; border-radius: 22px;
  align-items: center; justify-content: center; color: var(--accent);
  background: var(--surface-2); border: 1px dashed var(--border-strong);
  margin-bottom: 18px;
}
.sp-empty-title { font-size: 16px; font-weight: 700; margin: 0 0 8px; }
.sp-empty-sub { font-size: 13px; color: var(--text-muted); margin: 0; }
.skills-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.skill-card {
  position: relative; padding: 42px 18px 16px; border-radius: 16px;
  text-align: left; cursor: default; display: flex; flex-direction: column; gap: 6px;
}
.skill-card.off { opacity: .48; filter: grayscale(.35); }
.skill-icon {
  width: 40px; height: 40px; border-radius: 12px; display: inline-flex;
  align-items: center; justify-content: center; margin-bottom: 4px;
  color: var(--sc);
  background: color-mix(in srgb, var(--sc) 14%, transparent);
}
.skill-name { font-size: 15px; font-weight: 700; }
.skill-desc {
  font-size: 12.5px; color: var(--text-secondary); line-height: 1.55;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  min-height: 2.4em;
}
.skill-foot { display: flex; gap: 10px; margin-top: 4px; }
.skill-edit {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; color: var(--text-muted); cursor: pointer;
  padding: 4px 8px; border-radius: 8px; transition: all .15s;
}
.skill-edit:hover { color: var(--accent); background: var(--surface-2); }
.skill-edit.del:hover { color: var(--danger); background: var(--danger-soft); }
.skill-actions { position: absolute; top: 12px; right: 12px; display: flex; align-items: center; gap: 8px; }
.skill-src {
  font-size: 10.5px; font-weight: 600; padding: 2px 8px; border-radius: 999px;
  color: var(--accent); background: var(--surface-2); border: 1px solid var(--border-strong);
  letter-spacing: .02em;
}
.skill-switch {
  width: 38px; height: 21px; border-radius: 999px;
  position: relative; cursor: pointer; padding: 0;
  border: 1px solid var(--glass-edge-weak);
  background:
    var(--noise-medium),
    linear-gradient(180deg, rgba(255,255,255,.55), rgba(255,255,255,.3));
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.7), 0 2px 8px rgba(20,18,60,.08);
  transition: background .25s var(--ease), border-color .25s var(--ease), box-shadow .25s var(--ease);
}
.skill-switch.on {
  border-color: rgba(91,87,210,.5);
  background:
    var(--noise-medium),
    linear-gradient(180deg, rgba(124,121,247,.85), rgba(91,87,210,.7));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.35), 0 2px 10px rgba(91,87,210,.28);
}
[data-theme="dark"] .skill-switch {
  background:
    var(--noise-medium),
    linear-gradient(180deg, rgba(44,48,72,.75), rgba(30,33,52,.55));
  border-color: rgba(255,255,255,.14);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 2px 8px rgba(0,0,0,.25);
}
[data-theme="dark"] .skill-switch.on {
  border-color: rgba(126,121,247,.55);
  background:
    var(--noise-medium),
    linear-gradient(180deg, rgba(126,121,247,.9), rgba(91,87,210,.72));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.3), 0 2px 12px rgba(126,121,247,.35);
}
.skill-knob {
  position: absolute; top: 2px; left: 2px;
  width: 15px; height: 15px; border-radius: 50%;
  background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(255,255,255,.86));
  box-shadow: 0 1px 3px rgba(0,0,0,.18), inset 0 0 0 .5px rgba(255,255,255,.9);
  transition: transform .28s var(--spring);
}
.skill-switch.on .skill-knob { transform: translateX(17px); }
.sp-modal {
  position: fixed; inset: 0; z-index: 60; display: flex; align-items: center; justify-content: center;
  /* 遮罩层不使用 backdrop-filter：它会创建 backdrop root，令卡片的后背模糊失效 */
  background: rgba(15, 17, 27, .46);
  animation: spFade .2s var(--ease);
}
@keyframes spFade { from { opacity: 0; } to { opacity: 1; } }
.sp-modal-card {
  width: min(520px, 92vw); max-height: 88vh; overflow-y: auto;
  border-radius: 18px; padding: 24px; animation: spUp .25s var(--spring);
}
@keyframes spUp { from { transform: translateY(14px); opacity: 0; } to { transform: none; opacity: 1; } }
.sp-modal-title { font-size: 16px; font-weight: 700; margin: 0 0 18px; }
.sp-field { display: block; margin-bottom: 14px; }
.sp-label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.sp-input, .sp-textarea {
  width: 100%; padding: 9px 12px; border-radius: 10px;
  border: 1px solid var(--border-strong); background: var(--surface-1);
  color: var(--text); font-size: 13px; font-family: var(--font);
  transition: border-color .15s, box-shadow .15s; box-sizing: border-box;
}
.sp-input:focus, .sp-textarea:focus {
  outline: none; border-color: var(--accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent);
}
.sp-input:disabled { opacity: .55; }
.sp-textarea { resize: vertical; min-height: 140px; line-height: 1.6; }
.sp-format { font-size: 12px; color: var(--text-muted); line-height: 1.9; margin: 2px 0 18px; }
.sp-format code {
  font-family: var(--mono); font-size: 11px; background: var(--surface-2);
  border: 1px solid var(--border-strong); border-radius: 5px; padding: 1px 6px; margin: 0 2px;
}
.sp-modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>