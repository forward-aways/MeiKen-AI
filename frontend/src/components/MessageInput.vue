<script setup>
import { ref, watch, nextTick } from 'vue'
import { t } from '../store.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  placeholder: { type: String, default: '' },
  searchEnabled: { type: Boolean, default: false },
  thinkingEnabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'update:searchEnabled', 'update:thinkingEnabled', 'send', 'stop'])
const inputEl = ref(null)
const isSearchOn = ref(false)
const isThinkingOn = ref(false)

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
    if (!props.disabled && props.modelValue.trim()) emit('send')
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
        <div class="toolbar-spacer"></div>
        <button v-if="!disabled" class="send-btn" @click="emit('send')" :disabled="!modelValue.trim()" title="Send">
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

.send-btn { flex-shrink: 0; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 50%; border: none; background: var(--accent); color: #fff; cursor: pointer; transition: all .2s var(--ease); box-shadow: 0 2px 10px rgba(91,87,210,.22); }
.send-btn:hover { background: var(--accent-hover); box-shadow: 0 4px 18px rgba(91,87,210,.32); transform: scale(1.06); }
.send-btn:active { transform: scale(.92); transition-duration: .08s; }
.send-btn:disabled { opacity: .4; cursor: not-allowed; transform: none; box-shadow: none; }
.stop-btn { flex-shrink: 0; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 50%; border: 1.5px solid var(--danger); background: transparent; color: var(--danger); cursor: pointer; transition: all .2s var(--ease); }
.stop-btn:hover { background: var(--danger-soft); transform: scale(1.06); }
.stop-btn:active { transform: scale(.92); transition-duration: .08s; }
</style>
