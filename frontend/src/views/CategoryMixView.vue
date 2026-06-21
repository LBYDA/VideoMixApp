<template>
  <div class="category-mix">
    <div class="page-section">
      <h3>分类组设置</h3>
      <p class="section-hint">每组选择一个包含视频素材的文件夹</p>

      <div class="groups">
        <div v-for="(group, i) in groups" :key="i" class="group-card">
          <div class="group-header">
            <input
              v-model="group.name"
              class="group-name-input"
              placeholder="分类组名称"
            />
            <button class="btn-icon" @click="removeGroup(i)" v-if="groups.length > 1">X</button>
          </div>

          <div class="group-body">
            <label>素材目录</label>
            <FilePicker
              v-model="group.source_dir"
              :label="'选择文件夹'"
              :folders-only="true"
            />

            <div class="group-params">
              <div class="param">
                <label>最小时长 (秒)</label>
                <input v-model.number="group.min_clip_duration" type="number" step="0.5" min="0.5" />
              </div>
              <div class="param">
                <label>最大时长 (秒)</label>
                <input v-model.number="group.max_clip_duration" type="number" step="0.5" min="1" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <button class="btn" @click="addGroup">+ 添加分类组</button>
    </div>

    <div class="page-section">
      <h3>输出设置</h3>
      <div class="output-grid">
        <div class="param">
          <label>目标总时长 (秒)</label>
          <input v-model.number="targetDuration" type="number" step="1" min="1" />
        </div>
        <div class="param">
          <label>画质</label>
          <select v-model="quality">
            <option value="speed">速度优先</option>
            <option value="balanced">均衡</option>
            <option value="quality_priority">质量优先</option>
          </select>
        </div>
        <div class="param">
          <label>分辨率</label>
          <select v-model="resolution">
            <option value="1920x1080">1920x1080 (1080p)</option>
            <option value="1280x720">1280x720 (720p)</option>
            <option value="3840x2160">3840x2160 (4K)</option>
          </select>
        </div>
        <div class="param">
          <label>输出路径</label>
          <FilePicker
            v-model="outputDir"
            :label="'选择输出目录'"
            :folders-only="true"
          />
        </div>
      </div>
    </div>

    <button
      class="btn btn-primary btn-lg"
      @click="startMix"
      :disabled="isRunning"
    >
      {{ isRunning ? '混剪中...' : '开始混剪' }}
    </button>

    <ProgressBar
      v-if="jobStatus"
      :title="'分类混剪进度'"
      :percent="jobStatus.percent"
      :status="jobStatus.status"
      :step="jobStatus.current_step"
      :current-file="jobStatus.current_file || ''"
      :logs="progressStore.logs"
      @cancel="cancelMix"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import axios from 'axios'
import { useSettingsStore } from '@/stores/settings'
import { useProgressStore } from '@/stores/progress'
import FilePicker from '@/components/common/FilePicker.vue'
import ProgressBar from '@/components/common/ProgressBar.vue'
import type { CategoryGroup, JobProgress } from '@/types/api'

const settings = useSettingsStore()
const progressStore = useProgressStore()

const groups = reactive<CategoryGroup[]>([
  {
    name: '分类组1',
    source_dir: '',
    max_clip_duration: 5,
    min_clip_duration: 2,
    scene_threshold: 0.3,
    priority: 0,
  },
])

const targetDuration = ref(60)
const quality = ref('balanced')
const resolution = ref('1920x1080')
const outputDir = ref(settings.output_dir)
const isRunning = ref(false)
const jobId = ref('')
const jobStatus = ref<JobProgress | null>(null)

function addGroup() {
  groups.push({
    name: `分类组${groups.length + 1}`,
    source_dir: '',
    max_clip_duration: 5,
    min_clip_duration: 2,
    scene_threshold: 0.3,
    priority: 0,
  })
}

function removeGroup(index: number) {
  groups.splice(index, 1)
}

async function startMix() {
  // 验证
  const validGroups = groups.filter(g => g.name && g.source_dir)
  if (validGroups.length === 0) {
    alert('请至少配置一个有效的分类组')
    return
  }

  const [w, h] = resolution.value.split('x').map(Number)
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  const outputPath = `${outputDir.value || settings.output_dir}/category_mix_${timestamp}.mp4`

  isRunning.value = true
  jobStatus.value = null

  try {
    const { data } = await axios.post('/api/category-mix/start', {
      groups: validGroups,
      target_duration: targetDuration.value,
      quality: quality.value,
      output_path: outputPath,
      resolution_w: w,
      resolution_h: h,
      fps: 30,
      transition: 'none',
      transition_duration: 0.5,
      scene_detection: false,
      hw_encoder: null,
    })

    jobId.value = data.job_id
    progressStore.connect(data.job_id)

    // 监听进度
    const stopWatch = watch(() => progressStore.currentJob, (job) => {
      if (job) {
        jobStatus.value = job
        if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
          isRunning.value = false
          stopWatch()
        }
      }
    })
  } catch (e: any) {
    alert('启动失败: ' + (e.response?.data?.detail || e.message))
    isRunning.value = false
  }
}

function cancelMix() {
  if (jobId.value) {
    axios.post(`/api/category-mix/job/${jobId.value}/cancel`)
    progressStore.cancelJob()
  }
  isRunning.value = false
}
</script>

<style scoped>
.category-mix {
  max-width: 800px;
}

.page-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}

.page-section h3 {
  font-size: 16px;
  margin-bottom: 4px;
}

.section-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.group-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border);
}

.group-name-input {
  border: none;
  background: transparent;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  outline: none;
  flex: 1;
}

.btn-icon {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
}

.group-body {
  padding: 16px;
}

.group-body label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  display: block;
  margin-bottom: 6px;
}

.group-params {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}

.param {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.param label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 2px;
}

.param input, .param select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 14px;
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
}

.param input:focus, .param select:focus {
  border-color: var(--accent);
}

.output-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.btn {
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 13px;
}

.btn:hover {
  background: var(--bg-primary);
}

.btn-primary {
  background: var(--accent);
  color: white;
  border: none;
}

.btn-primary:hover {
  background: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-lg {
  padding: 12px 32px;
  font-size: 16px;
  margin-bottom: 20px;
}
</style>
