<script setup>
import { ref, nextTick, computed } from 'vue'
import { msgs, user, locale, t } from '../store.js'
import { md, stripMd } from '../md.js'
import { API_BASE } from '../api.js'

const props = defineProps({
  message: { type: Object, required: true },
  index: { type: Number, required: true }
})

const emit = defineEmits(['regenerate', 'retry', 'send', 'delete'])
const editing = ref(false)
const editText = ref('')
const copiedLabel = ref(null)
const showThinking = ref(false)
const lightbox = ref(null)

const isThinking = computed(() => !!(props.message.streaming && props.message.reasoning && !props.message.thinkingTime))

function isImgAvatar(v) { return v && v.startsWith('data:') }
function avBgStyle(c) { return c ? { background: c } : {} }

function startEdit() {
  editText.value = props.message.content
  editing.value = true
  nextTick(() => document.querySelector('.edit-input')?.focus())
}

function onEditKeydown(e) {
  if (e.key === 'Escape') { editing.value = false }
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (editText.value.trim()) confirmEdit()
  }
}

function confirmEdit() {
  if (!editText.value.trim()) return
  editing.value = false
  emit('send', { content: editText.value })
}

async function copyText() {
  await navigator.clipboard.writeText(stripMd(props.message.content))
  copiedLabel.value = 'text-' + props.index
  setTimeout(() => { copiedLabel.value = null }, 2000)
}

async function copyMd() {
  await navigator.clipboard.writeText(props.message.content)
  copiedLabel.value = 'md-' + props.index
  setTimeout(() => { copiedLabel.value = null }, 2000)
}

function thinkingLabel(sec) {
  if (locale.value === 'zh') return `\u601D\u8003\u4E86 ${sec} \u79D2`
  return `Thought for ${sec}s`
}

function truncate(s, max) {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '...' : s
}
</script>

<template>
  <div class="msg" :class="message.role" :style="{ animationDelay: Math.min(index, 10) * 35 + 'ms' }">
    <div class="av" :style="message.role === 'user' ? avBgStyle(user.avatar_color) : {}">
      <template v-if="message.role === 'user'">
        <img v-if="isImgAvatar(user.avatar)" :src="user.avatar" />
        <template v-else-if="user.avatar">{{ user.avatar }}</template>
        <template v-else>{{ (user.nickname || 'U')[0].toUpperCase() }}</template>
      </template>
      <svg v-else viewBox="0 0 40 40" width="30" height="30" fill="none"><rect width="40" height="40" rx="10" style="fill:var(--accent)"/><path d="M9 29V12l11 12 11-12v17" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </div>
    <div class="msg-body">
      <div class="msg-sender" v-if="message.role === 'assistant'">MeiKen AI</div>

      <div v-if="message.reasoning" class="thinking-section">
        <button class="thinking-toggle" :class="{ 'activity-glass glass-sweep': isThinking }" @click="showThinking = !showThinking">
          <span class="think-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" stroke-linecap="round"><path d="M12 2a7 7 0 0 0-7 7c0 2.4 1.2 4.5 3 5.7V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.3c1.8-1.2 3-3.3 3-5.7a7 7 0 0 0-7-7z"/><line x1="9" y1="21" x2="15" y2="21"/></svg></span>
          <span class="think-title" :class="{ 'shine-text': isThinking }">{{ message.thinkingTime ? thinkingLabel(message.thinkingTime) : t('thinking') }}</span>
          <svg class="chevron" :class="{ open: showThinking }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
        </button>
        <div v-if="showThinking" class="thinking-content">
          <div v-html="md(message.reasoning)"></div>
        </div>
      </div>

      <div v-if="editing" class="edit-row">
        <textarea v-model="editText" @keydown="onEditKeydown" rows="2" class="edit-input"></textarea>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span class="edit-hint">Esc {{ t('cancel') }}</span>
          <button class="edit-send-btn" @click="confirmEdit" :disabled="!editText.trim()" :title="t('send')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
          </button>
        </div>
      </div>
      <div v-if="!editing && message.images && message.images.length" class="bubble-images">
        <img
          v-for="id in message.images"
          :key="id"
          :src="API_BASE + '/images/' + id"
          class="bubble-image"
          @click="lightbox = id"
        />
      </div>
      <div v-if="!editing && (message.content || message.role === 'assistant')" class="bubble" v-html="md(message.content)"></div>
      <div class="msg-actions" v-if="message.role === 'user' && !editing">
        <button @click="copyText" :class="{ copied: copiedLabel === 'text-' + index }">
          <svg v-if="copiedLabel !== 'text-' + index" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          <svg v-if="copiedLabel === 'text-' + index" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
        </button>
        <button @click="startEdit" :title="t('edit')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        </button>
        <button @click="emit('delete')" :title="t('deleteMsg')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </div>
      <div class="msg-actions" v-if="message.role === 'assistant' && !message.streaming && !message.error">
        <span v-if="message.tokens" class="token-badge">{{ message.tokens }} {{ t('tokens') }}</span>
        <button @click="copyText" :class="{ copied: copiedLabel === 'text-' + index }">
          <svg v-if="copiedLabel !== 'text-' + index" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          <svg v-if="copiedLabel === 'text-' + index" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          <span v-if="copiedLabel === 'text-' + index">{{ t('copied') }}</span>
        </button>
        <button @click="copyMd" :class="{ copied: copiedLabel === 'md-' + index }">
          <svg v-if="copiedLabel !== 'md-' + index" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          <svg v-if="copiedLabel === 'md-' + index" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          <span v-if="copiedLabel === 'md-' + index">{{ t('copied') }}</span>
        </button>
        <button @click="emit('regenerate')" :title="t('regen')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
        </button>
        <button @click="emit('delete')" :title="t('deleteMsg')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </div>
      <div class="msg-actions" v-if="message.role === 'assistant' && message.streaming && message.error">
        <button @click="emit('retry')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          <span>{{ t('retry') }}</span>
        </button>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="lightbox" class="img-lightbox" @click="lightbox = null">
        <img :src="API_BASE + '/images/' + lightbox" />
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.msg { display: flex; gap: 16px; margin-bottom: 1.35rem; animation: msgIn .35s var(--spring) both; }
@keyframes msgIn { from { opacity: 0; transform: translateY(16px) scale(.97); } to { opacity: 1; transform: translateY(0) scale(1); } }
.msg.user { flex-direction: row-reverse; }
.av { width: 30px; height: 30px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; color: #fff; transition: transform .2s var(--ease); }
.av:hover { transform: scale(1.1); }
.msg.user .av { background: var(--accent); box-shadow: 0 2px 8px rgba(91,87,210,.3); }
.msg.assistant .av { background: var(--text-muted); }
.av img { width: 100%; height: 100%; object-fit: cover; border-radius: 8px; }
.msg-body { flex: 1; min-width: 0; }
.msg.user .msg-body { display: flex; flex-direction: column; align-items: flex-end; }
.msg-sender { font-size: 18px; font-weight: 600; color: var(--text); margin-bottom: 6px; line-height: 30px; }

/* Thinking Section — same activity language as the tool timeline */
.thinking-section { margin-bottom: 10px; }
.thinking-toggle {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 10px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12.5px;
  font-family: var(--font);
  cursor: pointer;
  transition: background .15s var(--ease), border-color .15s var(--ease);
}
.thinking-toggle:hover { background: rgba(91,87,210,.07); }
.thinking-toggle.activity-glass {
  background: linear-gradient(180deg, rgba(91,87,210,.08), rgba(91,87,210,.03));
  border: 1px solid rgba(91,87,210,.2);
}
.thinking-toggle.activity-glass:hover { background: linear-gradient(180deg, rgba(91,87,210,.11), rgba(91,87,210,.05)); }
[data-theme="dark"] .thinking-toggle.activity-glass {
  background: linear-gradient(180deg, rgba(126,121,247,.14), rgba(126,121,247,.05));
  border-color: rgba(126,121,247,.28);
}
[data-theme="dark"] .thinking-toggle.activity-glass:hover { background: linear-gradient(180deg, rgba(126,121,247,.18), rgba(126,121,247,.07)); }
.think-ico { display: flex; color: var(--text-muted); flex-shrink: 0; }
.thinking-toggle.activity-glass .think-ico { color: var(--accent); }
.think-title { font-weight: 600; }
.thinking-toggle.activity-glass .think-title { font-weight: 650; }
.thinking-toggle .chevron { transition: transform .2s var(--ease); color: var(--text-muted); flex-shrink: 0; }
.thinking-toggle .chevron.open { transform: rotate(180deg); }
.thinking-content {
  margin-top: 6px;
  padding: 10px 14px;
  border-radius: 10px;
  background: var(--accent-soft);
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
  animation: sourcesIn .2s var(--ease);
}
.thinking-content :deep(p) { margin: 0 0 .4rem; }
.thinking-content :deep(p:last-child) { margin: 0; }

.bubble { padding: .62rem 0; line-height: 1.68; font-size: 15px; }
.msg.user .bubble {
  max-width: 78%; color: var(--user-text); padding: .62rem 1rem;
  background:
    var(--noise-strong),
    linear-gradient(180deg, rgba(99,95,222,.97), rgba(75,71,192,.93));
  border: 1px solid rgba(255,255,255,.26);
  border-radius: 18px 18px 6px 18px;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.32),
    inset 0 -1px 0 rgba(0,0,0,.14),
    0 2px 6px rgba(91,87,210,.22),
    0 10px 24px rgba(91,87,210,.18);
}
.msg.assistant .bubble { width: 100%; background: transparent; border: none; box-shadow: none; border-radius: 0; padding: .3rem 0; }
:deep(.bubble p) { margin: 0 0 .5rem; }
:deep(.bubble p:last-child) { margin: 0; }
:deep(.bubble p:empty) { display: none; }
:deep(.bubble code) { background: var(--code-bg); border: 1px solid var(--code-border); padding: 1.5px 6px; border-radius: 5px; font-size: 15px; font-family: var(--mono); }
:deep(.bubble ol) { list-style-type: decimal; padding-left: 1.3rem; margin: .35rem 0; }
:deep(.bubble ul) { list-style-type: disc; padding-left: 1.3rem; margin: .35rem 0; }
:deep(.bubble li) { display: list-item; margin: .15rem 0; line-height: 1.68; }
:deep(.bubble h1),:deep(.bubble h2),:deep(.bubble h3),:deep(.bubble h4) { margin: .4rem 0 .15rem; font-weight: 650; line-height: 1.4; }
:deep(.bubble strong) { font-weight: 650; }
:deep(.bubble em) { font-style: italic; }
:deep(.bubble blockquote) { border-left: 3px solid var(--accent); padding-left: .75rem; margin: .35rem 0; color: var(--text-secondary); }
:deep(.bubble a) { color: var(--accent); }
:deep(.bubble table) { border-collapse: collapse; width: 100%; border-radius: var(--radius); overflow: hidden; border: 1px solid var(--border-strong); margin: .6rem 0; }
  :deep(.bubble .katex-display), :deep(.thinking-content .katex-display) { margin: .5rem 0; overflow-x: auto; overflow-y: hidden; max-width: 100%; }
  :deep(.bubble .katex), :deep(.thinking-content .katex) { font-size: 1.03em; }
  :deep(.bubble .math-fallback), :deep(.thinking-content .math-fallback) { color: var(--danger, #e5484d); }
:deep(.bubble th),:deep(.bubble td) { padding: .55rem .8rem; text-align: left; font-size: 14px; border-bottom: 1px solid var(--border); }
:deep(.bubble th) { background: var(--accent-soft); color: var(--accent); font-weight: 650; font-size: 14px; letter-spacing: .5px; }
:deep(.bubble tr:last-child td) { border-bottom: none; }
:deep(.bubble tbody tr:hover) { background: rgba(99,102,241,.03); }
:deep(.code-block) { position: relative; margin: .6rem 0; border-radius: var(--radius); overflow: hidden; }
:deep(.code-block pre) { background: #0d1117; border: 1px solid #21262d; border-radius: var(--radius); padding: 2rem .9rem .7rem .9rem; overflow-x: auto; margin: 0; font-size: 15px; line-height: 1.5; }
:deep(.code-block pre code) { background: none; border: none; padding: 0; font-family: var(--mono); }
:deep(.code-block .copy-btn) { position: absolute; top: 6px; right: 8px; padding: 3px 10px; border-radius: 6px; border: 1px solid #30363d; background: #21262d; color: #c9d1d9; font-size: 11px; font-weight: 500; cursor: pointer; transition: all .15s var(--ease); font-family: var(--font); z-index: 2; }
:deep(.code-block .copy-btn:hover) { background: #30363d; border-color: #484f5a; }
:deep(.code-block .copy-btn.copied) { background: #1a7f37; border-color: #1a7f37; color: #fff; }
:deep(.code-block .lang-tag) { position: absolute; top: 7px; left: 12px; font-size: 11px; color: #8b949e; font-family: var(--font); z-index: 2; user-select: none; }
.msg-actions { display: flex; align-items: center; gap: 2px; padding: .2rem 0 0 0; }
.msg-actions button { display: flex; align-items: center; gap: 4px; background: none; border: none; color: var(--text-muted); font-size: 12px; cursor: pointer; padding: 4px 8px; border-radius: 6px; transition: all .15s var(--ease); font-family: var(--font); }
.msg-actions button:hover { color: var(--text); background: var(--border); }
.msg-actions button.copied { color: #1a7f37; background: rgba(26,127,55,.08); }
.msg-actions button svg { width: 14px; height: 14px; opacity: .65; flex-shrink: 0; }
.token-badge { font-size: 11px; color: var(--text-muted); padding: 2px 8px; border-radius: 10px; background: var(--border); margin-right: 4px; white-space: nowrap; }
.edit-row { display: flex; flex-direction: column; gap: 6px; }
.edit-input { width: 100%; padding: .55rem .8rem; border-radius: var(--radius); border: 1.5px solid var(--accent); background: var(--surface); color: var(--text); font-size: 14.5px; font-family: var(--font); resize: none; outline: none; line-height: 1.5; min-height: 52px; }
.edit-hint { font-size: 11px; color: var(--text-muted); padding: .2rem .2rem 0; }
.edit-send-btn { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%; border: none; background: var(--accent); color: #fff; cursor: pointer; flex-shrink: 0; }
.edit-send-btn:hover { background: var(--accent-hover); }
.edit-send-btn:disabled { opacity: .35; cursor: not-allowed; }

/* Attached images */
.bubble-images { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 6px; justify-content: flex-end; }
.bubble-image {
  max-width: 220px; max-height: 180px; object-fit: cover;
  border-radius: 12px; cursor: zoom-in;
  border: 1px solid rgba(255,255,255,.5);
  box-shadow: 0 2px 10px rgba(20,18,60,.12);
  transition: transform .15s var(--ease), box-shadow .15s var(--ease);
}
[data-theme="dark"] .bubble-image { border-color: rgba(255,255,255,.12); box-shadow: 0 2px 10px rgba(0,0,0,.35); }
.bubble-image:hover { transform: scale(1.02); box-shadow: 0 6px 20px rgba(91,87,210,.2); }
.img-lightbox {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(8,10,18,.78);
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
  display: flex; align-items: center; justify-content: center; padding: 3vw;
  cursor: zoom-out; animation: fadeIn .16s ease;
}
.img-lightbox img { max-width: 94vw; max-height: 92vh; border-radius: 12px; box-shadow: 0 24px 80px rgba(0,0,0,.5); }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

@media (max-width: 768px) {
  .msg { gap: 10px; margin-bottom: 1rem; }
  .bubble { font-size: 14.5px; }
  .msg.user .bubble { max-width: 88%; }
  .bubble-image { max-width: 150px; max-height: 130px; }
}
</style>
