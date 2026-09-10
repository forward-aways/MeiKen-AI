<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { t, uploadImage } from '../store.js'
import { log } from '../logger.js'
import KBPill from './KBPill.vue'
import AgentOptions from './AgentOptions.vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  placeholder: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'send', 'stop', 'tempFile'])
const inputEl = ref(null)
const tempFileInput = ref(null)
const tempFileName = ref('')

// Image attachments (max 4, 5MB each; uploaded immediately for preview).
const MAX_IMAGES = 4
const MAX_IMAGE_SIZE = 5 * 1024 * 1024
const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif']
const imageInput = ref(null)
const pendingImages = ref([])  // [{ key, name, url, id, uploading, error }]
const dragOver = ref(false)

const uploadingCount = computed(() => pendingImages.value.filter((i) => i.uploading).length)
const readyIds = computed(() => pendingImages.value.filter((i) => i.id && !i.error).map((i) => i.id))
const canSend = computed(() => !props.disabled && uploadingCount.value === 0 &&
  (props.modelValue.trim() || readyIds.value.length))

function resizeTA(el) {
  el.style.height = 'auto'
  let m = parseInt(getComputedStyle(el).maxHeight) || 200
  el.style.height = Math.min(el.scrollHeight, m) + 'px'
}

function onInput(e) {
  emit('update:modelValue', e.target.value)
  resizeTA(e.target)
}

function doSend() {
  if (!canSend.value) return
  const ids = readyIds.value
  emit('send', ids)
  clearImages()
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (!props.disabled && canSend.value) { emit('send', readyIds.value); clearImages(); tempFileName.value = '' }
  } else if (e.key === 'Escape') {
    if (props.disabled) emit('stop')
  }
}

async function addImageFiles(fileList) {
  const files = [...fileList]
  for (const file of files) {
    if (pendingImages.value.length >= MAX_IMAGES) { alert(t('imageMax')); break }
    if (!IMAGE_TYPES.includes(file.type)) { alert(t('imageUnsupported')); continue }
    if (file.size > MAX_IMAGE_SIZE) { alert(t('imageTooBig')); continue }
    const item = {
      key: Date.now() + '-' + Math.random().toString(36).slice(2),
      name: file.name,
      url: URL.createObjectURL(file),
      id: null, uploading: true, error: '',
    }
    pendingImages.value.push(item)
    try {
      const d = await uploadImage(file)
      item.id = d.id
    } catch (e) {
      log.error('image upload failed |', e)
      item.error = e.message || t('imageUploadFail')
    } finally {
      item.uploading = false
    }
  }
}

function onImageChange(e) {
  if (e.target.files?.length) addImageFiles(e.target.files)
  e.target.value = ''
}

function onPaste(e) {
  const items = e.clipboardData?.items || []
  const files = []
  for (const it of items) {
    if (it.kind === 'file' && it.type.startsWith('image/')) {
      const f = it.getAsFile()
      if (f) files.push(f)
    }
  }
  if (files.length) { e.preventDefault(); addImageFiles(files) }
}

function onDrop(e) {
  dragOver.value = false
  const files = [...(e.dataTransfer?.files || [])].filter((f) => f.type.startsWith('image/'))
  if (files.length) { e.preventDefault(); addImageFiles(files) }
}

function onDragOver(e) {
  if (props.disabled) return
  if ([...(e.dataTransfer?.types || [])].includes('Files')) {
    e.preventDefault()
    dragOver.value = true
  }
}

function removeImage(item) {
  URL.revokeObjectURL(item.url)
  pendingImages.value = pendingImages.value.filter((i) => i !== item)
}

function clearImages() {
  for (const i of pendingImages.value) URL.revokeObjectURL(i.url)
  pendingImages.value = []
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

watch(() => props.modelValue, async () => {
  await nextTick()
  if (inputEl.value) resizeTA(inputEl.value)
})
</script>

<template>
  <div class="input-row">
    <div class="input-inner" :class="{ 'drag-over': dragOver }"
         @dragover="onDragOver" @dragleave="dragOver = false" @drop="onDrop">
      <div v-if="pendingImages.length" class="image-preview-row">
        <div v-for="img in pendingImages" :key="img.key" class="image-preview" :class="{ loading: img.uploading, failed: img.error }" :title="img.error || img.name">
          <img :src="img.url" :alt="img.name" />
          <span v-if="img.uploading" class="image-spinner"></span>
          <button class="image-remove" @click="removeImage(img)" :title="t('cancel')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="10" height="10" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      </div>
      <textarea ref="inputEl" :value="modelValue" :placeholder="placeholder" @keydown="onKeydown" @input="onInput" @paste="onPaste" rows="1"></textarea>
      <div class="input-toolbar">
        <AgentOptions />
        <KBPill />
        <input ref="tempFileInput" type="file" accept=".txt,.md,.pdf,.docx" @change="onTempFileChange" style="display:none" />
        <input ref="imageInput" type="file" accept="image/png,image/jpeg,image/webp,image/gif" multiple style="display:none" @change="onImageChange" />
        <div class="toolbar-spacer"></div>
        <div v-if="tempFileName" class="temp-file-tag">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span>{{ tempFileName }}</span>
          <button class="temp-file-close" @click="clearTempFile">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="10" height="10"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <button v-if="!disabled" class="icon-btn" @click="imageInput?.click()" :title="t('imageUpload')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="17" height="17" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
        </button>
        <button v-if="!disabled" class="icon-btn" @click="tempFileInput?.click()" :title="t('uploadFile')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
        </button>
        <button v-if="!disabled" class="send-btn" @click="doSend(); tempFileName = ''" :disabled="!canSend" title="Send">
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
.input-inner {
  max-width: 800px; margin: 0 auto; border-radius: var(--radius-lg);
  border: 1.5px solid rgba(255,255,255,.65);
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.04'/></svg>"),
    linear-gradient(180deg, rgba(255,255,255,.58), rgba(255,255,255,.32));
  backdrop-filter: blur(28px) saturate(185%);
  -webkit-backdrop-filter: blur(28px) saturate(185%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.75), 0 4px 18px rgba(20,18,60,.07);
  transition: border-color .25s var(--ease), box-shadow .25s var(--ease);
  position: relative;
}
.input-inner:focus-within { border-color: var(--accent); box-shadow: inset 0 1px 0 rgba(255,255,255,.8), 0 0 0 3px rgba(91,87,210,.12), 0 4px 18px rgba(91,87,210,.12); }
[data-theme="dark"] .input-inner {
  border-color: rgba(255,255,255,.12);
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.05'/></svg>"),
    linear-gradient(180deg, rgba(44,48,72,.6), rgba(30,33,52,.45));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 4px 18px rgba(0,0,0,.25);
}
[data-theme="dark"] .input-inner:focus-within { border-color: var(--accent); box-shadow: inset 0 1px 0 rgba(255,255,255,.1), 0 0 0 3px rgba(126,121,247,.15), 0 4px 18px rgba(0,0,0,.3); }
.input-inner textarea { width: 100%; padding: .68rem 1rem; border: none; outline: none; background: transparent; color: var(--text); font-size: 14.5px; font-family: var(--font); resize: none; line-height: 1.5; min-height: 56px; max-height: 200px; display: block; overflow: hidden; }
.input-inner textarea::placeholder { color: var(--text-muted); }
.input-toolbar { display: flex; align-items: center; gap: 8px; padding: 0 8px 8px 8px; }
.toolbar-spacer { flex: 1; }

.icon-btn { flex-shrink: 0; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 50%; border: 1.5px solid var(--border-strong); background: transparent; color: var(--text-secondary); cursor: pointer; transition: all .2s var(--ease); }
.icon-btn:hover { background: var(--border); color: var(--accent); border-color: var(--accent); transform: translateY(-1px); }
.icon-btn:active { transform: scale(.92); transition-duration: .08s; }

.temp-file-tag { display: flex; align-items: center; gap: 4px; padding: 3px 8px 3px 10px; border-radius: 16px; background: var(--accent-soft); color: var(--accent); font-size: 11.5px; max-width: 180px; animation: kbIn .15s var(--ease); }
.temp-file-tag svg { flex-shrink: 0; }
.temp-file-tag span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.temp-file-close { flex-shrink: 0; border: none; background: none; color: var(--accent); cursor: pointer; padding: 2px; border-radius: 50%; display: flex; transition: background .15s; }
.temp-file-close:hover { background: rgba(91,87,210,.2); }

/* Image attachments */
.image-preview-row { display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 10px 0; }
.image-preview {
  position: relative; width: 62px; height: 62px; border-radius: 10px; overflow: hidden;
  border: 1px solid rgba(255,255,255,.55);
  box-shadow: 0 2px 8px rgba(20,18,60,.1);
}
[data-theme="dark"] .image-preview { border-color: rgba(255,255,255,.14); }
.image-preview img { width: 100%; height: 100%; object-fit: cover; display: block; }
.image-preview.loading img { opacity: .55; }
.image-preview.failed { border-color: #ef4444; }
.image-remove {
  position: absolute; top: 2px; right: 2px; width: 16px; height: 16px; border-radius: 50%;
  border: none; background: rgba(15,17,27,.65); color: #fff; padding: 0;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.image-remove:hover { background: rgba(239,68,68,.9); }
.image-spinner {
  position: absolute; inset: 0; margin: auto; width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,.45); border-top-color: #fff; border-radius: 50%;
  animation: imgSpin .7s linear infinite;
}
@keyframes imgSpin { to { transform: rotate(360deg); } }
.input-inner.drag-over {
  border-color: var(--accent);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.8), 0 0 0 3px rgba(91,87,210,.18), 0 4px 18px rgba(91,87,210,.15);
}

.send-btn { flex-shrink: 0; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 50%; border: none; background: var(--accent); color: #fff; cursor: pointer; transition: all .2s var(--ease); box-shadow: 0 2px 10px rgba(91,87,210,.22); }
.send-btn:hover { background: var(--accent-hover); box-shadow: 0 4px 18px rgba(91,87,210,.32); transform: scale(1.06); }
.send-btn:active { transform: scale(.92); transition-duration: .08s; }
.send-btn:disabled { opacity: .4; cursor: not-allowed; transform: none; box-shadow: none; }
.stop-btn { flex-shrink: 0; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 50%; border: 1.5px solid var(--danger); background: transparent; color: var(--danger); cursor: pointer; transition: all .2s var(--ease); }
.stop-btn:hover { background: var(--danger-soft); transform: scale(1.06); }
.stop-btn:active { transform: scale(.92); transition-duration: .08s; }

@media (max-width: 768px) {
  .input-row { padding: .5rem .5rem .8rem; }
  .input-inner textarea { padding: .55rem .6rem; font-size: 14px; min-height: 48px; }
  .input-toolbar { flex-wrap: wrap; gap: 5px; }
  .icon-btn, .send-btn { width: 34px; height: 34px; }
  .toolbar-spacer { display: none; }
}
</style>
