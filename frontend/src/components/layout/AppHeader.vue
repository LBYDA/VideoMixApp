<template>
  <header class="header">
    <div class="header-left">
      <h2 class="page-title">{{ pageTitle }}</h2>
    </div>
    <div class="header-right">
      <span v-if="activeJob" class="job-indicator" :class="activeJob.status">
        {{ statusText }}
      </span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useJobsStore } from '@/stores/jobs'

const route = useRoute()
const jobsStore = useJobsStore()

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    home: '首页',
    'category-mix': '分类混剪',
    'ai-mix': 'AI智能混剪',
    'video-mix': '视频混剪',
    jobs: '任务历史',
    settings: '设置',
  }
  return titles[route.name as string] || '视频混剪工具'
})

const activeJob = computed(() => jobsStore.activeJob)

const statusText = computed(() => {
  if (!activeJob.value) return ''
  const texts: Record<string, string> = {
    pending: '等待中...',
    scanning: '扫描素材...',
    probing: '分析视频...',
    planning: '规划方案...',
    rendering: '编码中...',
    completed: '完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return texts[activeJob.value.status] || activeJob.value.status
})
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
}

.page-title {
  font-size: 18px;
  font-weight: 600;
}

.job-indicator {
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.job-indicator.rendering,
.job-indicator.scanning,
.job-indicator.probing,
.job-indicator.planning {
  background: #e3f2fd;
  color: #1976d2;
}

.job-indicator.completed {
  background: #e8f5e9;
  color: #2e7d32;
}

.job-indicator.failed {
  background: #ffebee;
  color: #c62828;
}

.job-indicator.cancelled {
  background: #fff3e0;
  color: #ef6c00;
}
</style>
