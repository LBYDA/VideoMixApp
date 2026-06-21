<template>
  <div class="progress-card">
    <div class="progress-header">
      <span class="progress-title">{{ title }}</span>
      <span class="progress-percent">{{ Math.round(percent) }}%</span>
    </div>
    <div class="progress-track">
      <div class="progress-fill" :style="{ width: percent + '%' }" :class="statusClass"></div>
    </div>
    <div class="progress-meta">
      <span class="progress-step">{{ step }}</span>
      <span class="progress-file" v-if="currentFile">{{ currentFile }}</span>
    </div>
    <div class="progress-logs" v-if="logs && logs.length > 0">
      <div
        v-for="(log, i) in (logs || []).slice(-5)"
        :key="i"
        class="log-line"
        :class="'log-' + log.level"
      >
        {{ log.message }}
      </div>
    </div>
    <div class="progress-actions" v-if="status === 'rendering' || status === 'scanning'">
      <button class="btn btn-danger" @click="$emit('cancel')">取消</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title?: string
  percent: number
  status: string
  step?: string
  currentFile?: string
  logs?: Array<{ level: string; message: string }>
}>()

defineEmits<{ cancel: [] }>()

const statusClass = computed(() => {
  if (props.status === 'completed') return 'fill-success'
  if (props.status === 'failed') return 'fill-error'
  return ''
})
</script>

<style scoped>
.progress-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-top: 16px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.progress-title {
  font-weight: 600;
  font-size: 14px;
}

.progress-percent {
  font-size: 20px;
  font-weight: 700;
  color: var(--accent);
}

.progress-track {
  height: 8px;
  background: var(--bg-primary);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-fill.fill-success {
  background: var(--success);
}

.progress-fill.fill-error {
  background: var(--error);
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
}

.progress-logs {
  margin-top: 12px;
  background: var(--bg-primary);
  padding: 10px 12px;
  border-radius: 6px;
  max-height: 150px;
  overflow-y: auto;
}

.log-line {
  font-size: 12px;
  padding: 2px 0;
  color: var(--text-secondary);
  word-break: break-all;
}

.log-line.log-error {
  color: var(--error);
}

.log-line.log-warn {
  color: var(--warning);
}

.progress-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.btn {
  padding: 8px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-danger {
  background: var(--error);
  color: white;
}

.btn-danger:hover {
  opacity: 0.9;
}
</style>
