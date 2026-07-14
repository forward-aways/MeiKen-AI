<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { t, locale, searchEnabled, thinkingEnabled } from '../store.js'

const emit = defineEmits(['send'])
const typewriterText = ref('')
const typewriterDone = ref(false)
const localInput = ref('')
const landingKey = ref(0)
const landingEl = ref(null)
const isSearchOn = computed(() => searchEnabled.value)
const isThinkingOn = computed(() => thinkingEnabled.value)
let _typeTimer = null

const chips = computed(() => t('tips'))

function toggleSearch() {
  searchEnabled.value = !searchEnabled.value
}

function toggleThinking() {
  thinkingEnabled.value = !thinkingEnabled.value
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
    if (localInput.value.trim()) emit('send', localInput.value)
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
  <div class="welcome" :key="landingKey">
    <div class="icon"><svg viewBox="0 0 40 40" width="42" height="42" fill="none"><rect width="40" height="40" rx="10" style="fill:var(--accent)"/><path d="M9 29V12l11 12 11-12v17" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="30" cy="9" r="2" fill="#fff" opacity="0.5"/></svg></div>
    <h2>{{ typewriterText || t('welcomeTitle') }}<span v-if="!typewriterDone" class="type-cursor">|</span></h2>
    <p :class="{ 'desc-reveal': typewriterDone }">{{ t('desc') }}</p>
    <div class="landing-input">
      <textarea ref="landingEl" v-model="localInput" :placeholder="t('ph')" @keydown="onKeydown" @input="resizeTA($event.target)" rows="1"></textarea>
      <div class="landing-toolbar">
        <button class="search-capsule" :class="{ active: isThinkingOn }" @click="toggleThinking">{{ t('deepThink') }}</button>
        <button class="search-capsule" :class="{ active: isSearchOn }" @click="toggleSearch">{{ t('searchWeb') }}</button>
        <div class="toolbar-spacer"></div>
        <button @click="emit('send', localInput)" :disabled="!localInput.trim()" :title="t('send')" class="send-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
        </button>
      </div>
    </div>
    <div class="chips">
      <button class="chip" v-for="(q, i) in chips" :key="i" @click="emit('send', q)">{{ q }}</button>
    </div>
  </div>
</template>

<style scoped>
.welcome { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 12vh 2rem 8vh; animation: fadeSlide .5s var(--spring) both; }
@keyframes fadeSlide { from { opacity: 0; transform: translateY(36px); } to { opacity: 1; transform: translateY(0); } }
.icon { width: 88px; height: 88px; border-radius: 22px; background: linear-gradient(135deg, var(--accent-soft), var(--surface)); display: flex; align-items: center; justify-content: center; margin-bottom: 2rem; box-shadow: 0 8px 32px rgba(91,87,210,.18); animation: iconFloat 4.5s ease-in-out infinite; }
@keyframes iconFloat { 0%, 100% { transform: translateY(0) rotate(0deg); } 25% { transform: translateY(-10px) rotate(-3deg); } 75% { transform: translateY(-10px) rotate(3deg); } }
.welcome h2 { font-size: 28px; font-weight: 700; margin-bottom: .5rem; letter-spacing: -.4px; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.type-cursor { display: inline-block; color: var(--accent); margin-left: 1px; font-weight: 400; animation: blink .8s step-end infinite; }
.welcome p { color: var(--text-secondary); font-size: 15px; max-width: 460px; line-height: 1.6; margin-bottom: 2.5rem; opacity: 0; transform: translateY(8px); }
.welcome p.desc-reveal { opacity: 1; transform: translateY(0); transition: opacity .5s var(--ease), transform .5s var(--ease); }
.landing-input { width: 100%; max-width: 740px; border-radius: var(--radius-lg); border: 1.5px solid var(--border-strong); background: var(--surface); transition: border-color .25s var(--ease), box-shadow .25s var(--ease); animation: fadeSlide .55s var(--spring) .2s both; }
.landing-input:focus-within { border-color: var(--accent); box-shadow: 0 0 0 4px rgba(91,87,210,.1); }
.landing-input textarea { width: 100%; padding: 1.2rem 1.2rem .3rem 1.2rem; border: none; outline: none; background: transparent; color: var(--text); font-size: 16px; font-family: var(--font); resize: none; line-height: 1.55; min-height: 80px; max-height: 260px; display: block; overflow: hidden; }
.landing-input textarea::placeholder { color: var(--text-muted); }
.landing-toolbar { display: flex; align-items: center; gap: 8px; padding: 0 8px 8px 8px; }
.toolbar-spacer { flex: 1; }
.search-capsule { padding: 5px 14px; border-radius: 20px; border: 1.5px solid var(--border-strong); background: transparent; color: var(--text-secondary); font-size: 12.5px; font-family: var(--font); cursor: pointer; transition: all .2s var(--ease); white-space: nowrap; line-height: 1.4; }
.search-capsule:hover { background: var(--border); transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,.04); }
.search-capsule:active { transform: scale(.95); transition-duration: .08s; }
.search-capsule.active { background: rgba(91, 87, 210, 0.12); border-color: var(--accent); color: var(--accent); }
.send-btn { flex-shrink: 0; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 50%; border: none; background: var(--accent); color: #fff; cursor: pointer; transition: all .2s var(--ease); box-shadow: 0 2px 10px rgba(91,87,210,.22); }
.send-btn:hover { background: var(--accent-hover); transform: scale(1.06); }
.send-btn:active { transform: scale(.92); transition-duration: .08s; }
.send-btn:disabled { opacity: .35; cursor: not-allowed; transform: none; box-shadow: none; }
.chips { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-top: 2.25rem; animation: fadeSlide .55s var(--spring) .4s both; }
.chip { padding: .55rem 1.15rem; border-radius: var(--radius-xl); border: 1px solid var(--border-strong); background: var(--surface); color: var(--text-secondary); font-size: 13px; cursor: pointer; transition: all .2s var(--ease); font-family: var(--font); user-select: none; }
.chip:hover { border-color: var(--accent); color: var(--accent); box-shadow: var(--shadow-sm); transform: translateY(-2px); }
.chip:active { transform: scale(.96); transition-duration: .08s; }

@media (max-width: 768px) {
  .welcome { padding: 6vh 1rem 4vh; }
  .icon { width: 64px; height: 64px; margin-bottom: 1.25rem; }
  .welcome h2 { font-size: 22px; }
  .welcome p { font-size: 13.5px; margin-bottom: 1.5rem; }
  .landing-input textarea { padding: .8rem .6rem .2rem; font-size: 14.5px; min-height: 64px; }
  .landing-toolbar { flex-wrap: wrap; gap: 5px; }
  .landing-toolbar .toolbar-spacer { display: none; }
  .landing-toolbar .search-capsule { padding: 4px 9px; font-size: 11px; }
  .landing-toolbar .send-btn { width: 36px; height: 36px; }
  .chip { padding: .45rem .9rem; font-size: 12px; }
  .chips { gap: 8px; margin-top: 1.5rem; }
}
</style>
