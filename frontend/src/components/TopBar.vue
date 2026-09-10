<script setup>
import { t } from '../store.js'
import ExpertTeamBar from './ExpertTeamBar.vue'
import TopBarOptions from './TopBarOptions.vue'
</script>

<template>
  <header class="top-bar glass">
    <div class="brand">
      <svg viewBox="0 0 40 40" width="24" height="24" fill="none"><rect width="40" height="40" rx="10" style="fill:var(--accent)"/><path d="M9 29V12l11 12 11-12v17" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span class="brand-name">MeiKen AI <em>Harness</em></span>
    </div>

    <div class="top-spacer"></div>

    <ExpertTeamBar />

    <div class="top-opts">
      <TopBarOptions />
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  position: fixed; top: 0; left: 0; right: 0;
  display: flex; align-items: center; gap: 14px;
  padding: .55rem 1rem; height: 52px; flex-shrink: 0;
  z-index: 40;
  /* keep the native .glass tint (background stays visible), just a softer blur */
  backdrop-filter: blur(18px) saturate(170%);
  -webkit-backdrop-filter: blur(18px) saturate(170%);
  animation: barIn .4s var(--spring) both;
}
.brand { display: flex; align-items: center; gap: 8px; }
.brand-name { font-size: 16px; font-weight: 750; letter-spacing: -.3px; color: var(--text); }
.brand-name em { font-style: normal; font-size: 12.5px; font-weight: 600; color: var(--accent); background: var(--accent-soft); padding: 2px 7px; border-radius: 8px; margin-left: 5px; }
.top-spacer { flex: 1; }
.top-opts { display: flex; align-items: center; }

@media (max-width: 768px) {
  .top-bar { gap: 8px; padding: .45rem .6rem; height: 48px; }
  .brand-name { display: none; }
  .top-opts { display: none; }
  .expert-bar .expert-label { display: none; }
}
</style>