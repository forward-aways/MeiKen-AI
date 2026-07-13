<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { t } from '../store.js'
import { get } from '../api.js'

const emit = defineEmits(['close', 'open-conv'])

const query = ref('')
const results = ref([])
const searchEl = ref(null)
let searchTimer = null

async function doSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    if (!query.value.trim()) {
      results.value = []
      return
    }
    try {
      const res = await get('/search?q=' + encodeURIComponent(query.value))
      results.value = res
    } catch {
      results.value = []
    }
  }, 250)
}

function openResult(r) {
  emit('open-conv', r.cid)
  emit('close')
}

onMounted(async () => {
  await nextTick()
  searchEl.value?.focus()
})
</script>

<template>
  <div class="top-bar" style="justify-content:flex-start;gap:8px">
    <button class="btn" @click="$emit('close')" style="padding:.35rem .5rem;width:34px;height:34px" title="Back">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
    </button>
  </div>
  <div class="search-page">
    <div class="search-page-inner">
      <div class="search-input-wrap">
        <input v-model="query" @input="doSearch" :placeholder="t('searchMessages')" ref="searchEl" autofocus>
      </div>
      <div v-if="results.length" style="margin-top:.5rem">
        <div v-for="r in results" :key="r.cid+'-'+r.created_at" class="search-result" @click="openResult(r)">
          <div class="r-title">{{ r.title }}</div>
          <div class="r-snippet">{{ r.snippet }}</div>
          <div class="r-meta">{{ r.role==='user' ? 'You' : 'MeiKen' }} · {{ r.created_at?.slice(0,16) }}</div>
        </div>
      </div>
      <div class="search-empty" v-if="query && !results.length">{{ t('noResults') }}</div>
    </div>
  </div>
</template>

<style scoped>
.top-bar {
  display: flex;
  align-items: center;
  padding: 1rem 1.5rem;
  background: transparent;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 10;
  flex-shrink: 0;
  border-bottom: none;
}

.search-page {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.search-page-inner {
  max-width: 640px;
  margin: 0 auto;
}

.search-input-wrap {
  position: relative;
}

.search-input-wrap input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background: var(--surface);
  color: var(--text);
  font-family: var(--font);
  font-size: 14px;
  outline: none;
  transition: border-color .2s var(--ease), box-shadow .2s var(--ease);
}

.search-input-wrap input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.search-input-wrap input::placeholder {
  color: var(--text-muted);
}

.search-result {
  padding: 12px 14px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color .2s var(--ease), background .2s var(--ease);
}

.search-result:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.r-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.r-snippet {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 6px;
}

.r-meta {
  font-size: 11px;
  color: var(--text-muted);
}

.search-empty {
  text-align: center;
  color: var(--text-muted);
  padding: 32px 0;
  font-size: 13px;
}

@media (max-width: 768px) {
  .top-bar { padding: .75rem .75rem; }
  .search-page { padding: 12px 8px; }
}
</style>
