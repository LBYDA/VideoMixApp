<template>
  <div class="job-history">
    <div class="page-section">
      <div class="header-row">
        <h3>任务历史</h3>
        <button class="btn" @click="loadJobs">刷新</button>
      </div>

      <div v-if="jobs.length === 0" class="empty-state">
        暂无任务记录
      </div>

      <div class="job-list" v-else>
        <div v-for="job in jobs" :key="job.job_id" class="job-card" :class="'status-' + job.status">
          <div class="job-top">
            <span class="job-type">{{ typeLabel(job.job_type) }}</span>
            <span class="job-status">{{ statusLabel(job.status) }}</span>
          </div>
          <div class="job-detail">
            <span class="job-id">{{ job.job_id }}</span>
            <span class="job-summary">{{ (job as any).input_summary || job.current_step }}</span>
          </div>
          <div class="job-bottom" v-if="job.output_path">
            <span class="job-output">{{ job.output_path }}</span>
          </div>
          <div class="job-bottom" v-if="job.error">
            <span class="job-error">{{ job.error }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import type { JobProgress } from '@/types/api'

const jobs = ref<JobProgress[]>([])

function typeLabel(type: string) {
  const labels: Record<string, string> = {
    category_mix: '分类混剪',
    ai_mix: 'AI混剪',
    video_mix: '视频混剪',
  }
  return labels[type] || type
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '等待中',
    scanning: '扫描中',
    probing: '分析中',
    planning: '规划中',
    rendering: '渲染中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return labels[status] || status
}

async function loadJobs() {
  try {
    const { data } = await axios.get('/api/jobs', { params: { limit: 50 } })
    jobs.value = data
  } catch (e) {
    console.error('Failed to load jobs:', e)
  }
}

onMounted(loadJobs)
</script>

<style scoped>
.job-history { max-width: 800px; }

.page-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-row h3 { font-size: 16px; }

.empty-state {
  text-align: center;
  color: var(--text-secondary);
  padding: 40px;
  font-size: 14px;
}

.job-list { display: flex; flex-direction: column; gap: 10px; }

.job-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
}

.job-card.status-completed { border-left: 3px solid var(--success); }
.job-card.status-failed { border-left: 3px solid var(--error); }
.job-card.status-rendering { border-left: 3px solid var(--accent); }

.job-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.job-type { font-weight: 600; font-size: 14px; }

.job-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--bg-primary);
}

.job-detail {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.job-id {
  font-family: monospace;
  color: var(--accent);
}

.job-output {
  font-size: 12px;
  color: var(--success);
  word-break: break-all;
}

.job-error {
  font-size: 12px;
  color: var(--error);
  word-break: break-all;
}

.btn {
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 12px;
}

.btn:hover { background: var(--bg-primary); }
</style>
