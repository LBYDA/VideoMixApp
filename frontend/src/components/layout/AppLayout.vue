<template>
  <div class="layout">
    <AppSidebar />
    <div class="main-area">
      <AppHeader />
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
</script>

<style scoped>
.layout {
  display: flex;
  width: 100%;
  min-height: 100vh;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 240px;
}

.content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}
</style>
