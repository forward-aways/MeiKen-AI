<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { t, locale, mode } from '../store.js'
import KBPill from './KBPill.vue'
import AgentOptions from './AgentOptions.vue'

const emit = defineEmits(['send', 'tempFile'])
const typewriterText = ref('')
const typewriterDone = ref(false)
const localInput = ref('')
const landingKey = ref(0)
const landingEl = ref(null)
const tempFileInput = ref(null)
const tempFileName = ref('')
let _typeTimer = null

const chips = computed(() => {
  if (mode.value === 'code') return t('tipsCode')
  if (mode.value === 'work') return t('tipsWork')
  return t('tips')
})
const promptList = computed(() => chips.value.slice(0, 3))
const descText = computed(() => {
  if (mode.value === 'code') return t('descCode')
  if (mode.value === 'work') return t('descWork')
  return t('desc')
})

function sendMsg(text) {
  emit('send', text)
  tempFileName.value = ''
}

function onTempFileChange(e) {
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

function runTypewriter() {
  clearInterval(_typeTimer)
  _typeTimer = null
  typewriterText.value = ''
  typewriterDone.value = false
  landingKey.value++
  const full = t('welcomeTitle')
  let idx = 0
  _typeTimer = setInterval(() => {
    idx++
    typewriterText.value = full.slice(0, idx)
    if (idx >= full.length) {
      clearInterval(_typeTimer)
      _typeTimer = null
      typewriterDone.value = true
    }
  }, 60)
}

function resizeTA(el) {
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 260) + 'px'
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (localInput.value.trim()) sendMsg(localInput.value)
  }
}

watch(locale, () => { runTypewriter() })

onMounted(() => {
  runTypewriter()
  landingEl.value?.focus()
})

onUnmounted(() => {
  clearInterval(_typeTimer)
  _typeTimer = null
})

defineExpose({ runTypewriter })
</script>

<template>
  <div class="dashboard" :key="landingKey">
    <div class="hero">
      <div class="icon"><svg viewBox="0 0 40 40" width="42" height="42" fill="none"><rect width="40" height="40" rx="10" style="fill:var(--accent)"/><path d="M9 29V12l11 12 11-12v17" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="30" cy="9" r="2" fill="#fff" opacity="0.5"/></svg></div>
      <h2>{{ typewriterText || t('welcomeTitle') }}<span v-if="!typewriterDone" class="type-cursor">|</span></h2>
      <p :class="{ 'desc-reveal': typewriterDone }">{{ descText }}</p>
    </div>

    <div class="landing-input">
      <textarea ref="landingEl" v-model="localInput" :placeholder="t('ph')" @keydown="onKeydown" @input="resizeTA($event.target)" rows="1"></textarea>
      <div class="landing-toolbar">
        <AgentOptions />
        <KBPill />
        <input ref="tempFileInput" type="file" accept=".txt,.md,.pdf,.docx" @change="onTempFileChange" style="display:none" />
        <div v-if="tempFileName" class="temp-file-tag">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span>{{ tempFileName }}</span>
          <button class="temp-file-close" @click="clearTempFile">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="10" height="10"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <button class="attach-btn" @click="tempFileInput?.click()" :title="t('uploadFile')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
        </button>
        <div class="toolbar-spacer"></div>
        <button @click="sendMsg(localInput)" :disabled="!localInput.trim()" :title="t('send')" class="send-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
        </button>
      </div>
    </div>

    <div class="prompts">
      <span class="prompts-label">{{ t('tryHint') }}</span>
      <button v-for="(q, i) in promptList" :key="i" class="prompt-chip" @click="sendMsg(q)">
        <span>{{ q }}</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.dashboard { display: flex; flex-direction: column; align-items: center; text-align: center; padding: 9vh 2rem 5vh; animation: fadeSlide .5s var(--spring) both; width: 100%; }
@keyframes fadeSlide { from { opacity: 0; transform: translateY(36px); } to { opacity: 1; transform: translateY(0); } }
.hero { display: flex; flex-direction: column; align-items: center; }
.icon { width: 72px; height: 72px; border-radius: 20px; background: linear-gradient(135deg, var(--accent-soft), var(--surface)); display: flex; align-items: center; justify-content: center; margin-bottom: 1.4rem; box-shadow: 0 8px 32px rgba(91,87,210,.18); animation: iconFloat 4.5s ease-in-out infinite; }
@keyframes iconFloat { 0%, 100% { transform: translateY(0) rotate(0deg); } 25% { transform: translateY(-10px) rotate(-3deg); } 75% { transform: translateY(-10px) rotate(3deg); } }
.dashboard h2 { font-size: 28px; font-weight: 700; margin-bottom: .5rem; letter-spacing: -.4px; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.type-cursor { display: inline-block; color: var(--accent); margin-left: 1px; font-weight: 400; animation: blink .8s step-end infinite; }
.dashboard p { color: var(--text-secondary); font-size: 15.5px; max-width: 460px; line-height: 1.6; margin-bottom: 1.6rem; opacity: 0; transform: translateY(8px); }
.dashboard p.desc-reveal { opacity: 1; transform: translateY(0); transition: opacity .5s var(--ease), transform .5s var(--ease); }
.landing-input {
  width: 100%; max-width: 740px;
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, rgba(255,255,255,.94), rgba(255,255,255,.84));
  backdrop-filter: blur(20px) saturate(160%);
  -webkit-backdrop-filter: blur(20px) saturate(160%);
  border: 1.5px solid var(--border-strong);
  box-shadow: var(--shadow-ambient), var(--shadow-key);
  transition: border-color .25s var(--ease), box-shadow .25s var(--ease);
  animation: fadeSlide .55s var(--spring) .2s both;
}
[data-theme="dark"] .landing-input { background: linear-gradient(180deg, rgba(32,35,52,.94), rgba(27,30,46,.86)); }
.landing-input:focus-within { border-color: var(--accent); box-shadow: 0 0 0 4px rgba(91,87,210,.12), var(--shadow-ambient), var(--shadow-key); }
.landing-input textarea { width: 100%; padding: 1.2rem 1.2rem .3rem 1.2rem; border: none; outline: none; background: transparent; color: var(--text); font-size: 17px; font-family: var(--font); resize: none; line-height: 1.55; min-height: 80px; max-height: 260px; display: block; overflow: hidden; }
.landing-input textarea::placeholder { color: var(--text-muted); }
.landing-toolbar { display: flex; align-items: center; gap: 8px; padding: 0 8px 8px 8px; }
.toolbar-spacer { flex: 1; }
.send-btn { flex-shrink: 0; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 50%; border: none; background: var(--accent); color: #fff; cursor: pointer; transition: all .2s var(--ease); box-shadow: 0 2px 10px rgba(91,87,210,.22); }
.send-btn:hover { background: var(--accent-hover); transform: scale(1.06); }
.send-btn:active { transform: scale(.92); transition-duration: .08s; }
.send-btn:disabled { opacity: .35; cursor: not-allowed; transform: none; box-shadow: none; }
.attach-btn { flex-shrink: 0; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 50%; border: 1.5px solid var(--border-strong); background: transparent; color: var(--text-secondary); cursor: pointer; transition: all .2s var(--ease); }
.attach-btn:hover { background: var(--border); color: var(--accent); border-color: var(--accent); transform: translateY(-1px); }
.temp-file-tag { display: flex; align-items: center; gap: 4px; padding: 3px 8px 3px 10px; border-radius: 16px; background: var(--accent-soft); color: var(--accent); font-size: 12.5px; max-width: 180px; animation: kbIn .15s var(--ease); }
.temp-file-tag svg { flex-shrink: 0; }
.temp-file-tag span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.temp-file-close { flex-shrink: 0; border: none; background: none; color: var(--accent); cursor: pointer; padding: 2px; border-radius: 50%; display: flex; transition: background .15s; }
.temp-file-close:hover { background: rgba(91,87,210,.2); }
@keyframes kbIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
.prompts { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 10px; justify-content: center; margin-top: 1.8rem; animation: fadeSlide .55s var(--spring) .35s both; }
.prompts-label { font-size: 13px; color: var(--text-muted); margin-right: 2px; }
.prompt-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 15px;
  border-radius: 999px;
  font-size: 13.5px; font-family: var(--font); color: var(--text-secondary);
  cursor: pointer; user-select: none;
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.045'/></svg>"),
    linear-gradient(180deg, rgba(255,255,255,.55), rgba(255,255,255,.3));
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(255,255,255,.65);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.75), 0 4px 16px rgba(20,18,60,.08);
  transition: all .2s var(--spring);
}
.prompt-chip svg { color: var(--accent); opacity: 0; transform: translateX(-4px); transition: all .18s var(--ease); }
.prompt-chip:hover { transform: translateY(-2px); color: var(--accent); border-color: rgba(91,87,210,.35); box-shadow: inset 0 1px 0 rgba(255,255,255,.8), 0 6px 20px rgba(91,87,210,.14); }
.prompt-chip:hover svg { opacity: 1; transform: translateX(0); }
.prompt-chip:active { transform: scale(.96); transition-duration: .08s; }
[data-theme="dark"] .prompt-chip {
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='120' height='120' filter='url(%23n)' opacity='0.05'/></svg>"),
    linear-gradient(180deg, rgba(44,48,72,.6), rgba(30,33,52,.42));
  border-color: rgba(255,255,255,.12);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 4px 16px rgba(0,0,0,.25);
}

@media (max-width: 768px) {
  .dashboard { padding: 5vh 1rem 3vh; }
  .icon { width: 56px; height: 56px; margin-bottom: 1rem; }
  .dashboard h2 { font-size: 23px; }
  .dashboard p { font-size: 14px; margin-bottom: 1.2rem; }
  .landing-input textarea { padding: .8rem .6rem .2rem; font-size: 15.5px; min-height: 64px; }
  .landing-toolbar { flex-wrap: wrap; gap: 5px; }
  .landing-toolbar .toolbar-spacer { display: none; }
  .landing-toolbar .send-btn { width: 36px; height: 36px; }
  .landing-toolbar .attach-btn { width: 32px; height: 32px; }
  .prompt-link { font-size: 13.5px; }
  .prompts { gap: 4px 14px; margin-top: 1.3rem; }
}
</style>