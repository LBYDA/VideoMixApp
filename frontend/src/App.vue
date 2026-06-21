<template>
  <div class="app" :class="themeClass">
    <AppLayout />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()

const themeClass = computed(() => {
  if (settings.theme === 'auto') {
    return 'theme-auto'
  }
  return `theme-${settings.theme}`
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --bg-primary: #f5f5f5;
  --bg-secondary: #ffffff;
  --bg-sidebar: #1a1a2e;
  --text-primary: #2c3e50;
  --text-secondary: #666;
  --text-sidebar: #ccc;
  --accent: #4a90d9;
  --accent-hover: #357abd;
  --border: #e0e0e0;
  --success: #27ae60;
  --error: #e74c3c;
  --warning: #f39c12;
}

.theme-dark {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --bg-sidebar: #0f0f1a;
  --text-primary: #e0e0e0;
  --text-secondary: #aaa;
  --text-sidebar: #888;
  --border: #2a2a4a;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.app {
  min-height: 100vh;
  display: flex;
}
</style>
