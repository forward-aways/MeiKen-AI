<script setup>
/**
 * 网站页脚：ICP 备案号。
 *
 * 合规要求：备案号必须展示在网站首页底部，并链接至工信部备案官网首页。
 * 备案号与链接在此单点维护（唯一事实源），各页面只引用本组件，
 * 避免将来变更备案号或链接时漏改（守卫见 __tests__/material.test.js）。
 */
</script>

<template>
  <div class="site-footer">
    <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">辽ICP备2026015937号-1</a>
  </div>
</template>

<style scoped>
.site-footer { display: flex; justify-content: center; padding: .35rem 1rem .5rem; }
.site-footer a {
  font-size: 11.5px; color: var(--text-muted); text-decoration: none;
  opacity: .8; letter-spacing: .2px;
  transition: color .15s var(--ease), opacity .15s var(--ease);
}
.site-footer a:hover { color: var(--accent); opacity: 1; }
</style>
