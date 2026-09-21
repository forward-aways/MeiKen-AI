<script setup>
/**
 * 图片附件预览行：聊天输入框与落地页输入框共用。
 * 样式与结构在此单点维护，避免两处输入框各自实现后漂移。
 */
import { t } from '../store.js'

defineProps({
  images: { type: Array, default: () => [] },
})
defineEmits(['remove'])
</script>

<template>
  <div v-if="images.length" class="attach-row">
    <div
      v-for="img in images"
      :key="img.key"
      class="attach-item"
      :class="{ loading: img.uploading, failed: img.error }"
      :title="img.error || img.name"
    >
      <img :src="img.url" :alt="img.name" />
      <span v-if="img.uploading" class="attach-spinner"></span>
      <button class="attach-remove" @click="$emit('remove', img)" :title="t('cancel')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="10" height="10" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.attach-row { display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 10px 0; }
.attach-item {
  position: relative; width: 62px; height: 62px; border-radius: 10px; overflow: hidden;
  border: 1px solid rgba(255,255,255,.55);
  box-shadow: 0 2px 8px rgba(20,18,60,.1);
}
[data-theme="dark"] .attach-item { border-color: rgba(255,255,255,.14); }
.attach-item img { width: 100%; height: 100%; object-fit: cover; display: block; }
.attach-item.loading img { opacity: .55; }
.attach-item.failed { border-color: #ef4444; }
.attach-remove {
  position: absolute; top: 2px; right: 2px; width: 16px; height: 16px; border-radius: 50%;
  border: none; background: rgba(15,17,27,.65); color: #fff; padding: 0;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.attach-remove:hover { background: rgba(239,68,68,.9); }
.attach-spinner {
  position: absolute; inset: 0; margin: auto; width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,.45); border-top-color: #fff; border-radius: 50%;
  animation: attachSpin .7s linear infinite;
}
@keyframes attachSpin { to { transform: rotate(360deg); } }
</style>
