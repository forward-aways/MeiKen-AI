<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { t } from '../store.js'
import { useImageAttachments } from '../attachments.js'
import KBPill from './KBPill.vue'
import AgentOptions from './AgentOptions.vue'
import AttachPreview from './AttachPreview.vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  placeholder: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'send', 'stop', 'tempFile'])
const inputEl = ref(null)
const tempFileInput = ref(null)
const tempFileName = ref('')
const imageInput = ref(null)

// 图片附件行为来自共享组合式函数（与落地页输入框同一实现）
const {
  pendingImages, dragOver, uploadingCount, readyIds,
  onImageChange, onPaste, onDrop, onDragOver, removeImage, clearImages,
} = useImageAttachments()

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
    <div class="input-inner glass-input" :class="{ 'drag-over': dragOver }"
         @dragover="(e) => { if (!disabled) onDragOver(e) }" @dragleave="dragOver = false" @drop="onDrop">
      <AttachPreview :images="pendingImages" @remove="removeImage" />
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
        <button v-if="!disabled" class="icon-btn glass-icon-btn" @click="imageInput?.click()" :title="t('imageUpload')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="17" height="17" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
        </button>
        <button v-if="!disabled" class="icon-btn glass-icon-btn" @click="tempFileInput?.click()" :title="t('uploadFile')">
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
/* 材质（染色/噪点/模糊/高光/边缘/投影/焦点/拖拽态）来自全局 .glass-input，
   唯一事实源；此处只保留布局，避免与落地页输入框再次分叉。 */
.input-inner {
  max-width: 800px; margin: 0 auto; border-radius: var(--radius-lg);
  position: relative;
}
.input-inner textarea { width: 100%; padding: .68rem 1rem; border: none; outline: none; background: transparent; color: var(--text); font-size: 14.5px; font-family: var(--font); resize: none; line-height: 1.5; min-height: 56px; max-height: 200px; display: block; overflow: hidden; }
.input-inner textarea::placeholder { color: var(--text-muted); }
.input-toolbar { display: flex; align-items: center; gap: 8px; padding: 0 8px 8px 8px; }
.toolbar-spacer { flex: 1; }

/* 材质来自全局 .glass-icon-btn（凸起毛玻璃）；此处只保留布局 */
.icon-btn { flex-shrink: 0; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 50%; cursor: pointer; }

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

@media (max-width: 768px) {
  .input-row { padding: .5rem .5rem .8rem; }
  .input-inner textarea { padding: .55rem .6rem; font-size: 14px; min-height: 48px; }
  .input-toolbar { flex-wrap: wrap; gap: 5px; }
  .icon-btn, .send-btn { width: 34px; height: 34px; }
  .toolbar-spacer { display: none; }
}
</style>
