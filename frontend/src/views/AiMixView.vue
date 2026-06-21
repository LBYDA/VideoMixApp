<template>
  <div class="ai-mix">
    <div class="page-section">
      <h3>文案录入</h3>
      <textarea
        v-model="copyText"
        class="copy-input"
        placeholder="粘贴你的产品文案、脚本或推广内容..."
        rows="6"
      ></textarea>
    </div>

    <div class="page-section">
      <h3>素材选择</h3>
      <p class="section-hint">输入视频或素材文件夹路径</p>
      <div class="path-input-row">
        <input
          v-model="videoPathInput"
          class="path-input"
          placeholder="输入文件夹或视频文件路径，多个用逗号分隔"
        />
        <button class="btn" @click="scanVideos" :disabled="scanLoading">
          {{ scanLoading ? '扫描中...' : '扫描' }}
        </button>
      </div>
      <div class="scan-result" v-if="scanSummary">
        {{ scanSummary }}
      </div>
      <div class="selected-files" v-if="videoPaths.length > 0">
        <span class="tag" v-for="fp in videoPaths" :key="fp">{{ getFileName(fp) }}</span>
      </div>
    </div>

    <div class="page-section">
      <h3>输出设置</h3>
      <div class="output-grid">
        <div class="param">
          <label>目标时长 (秒)</label>
          <input v-model.number="targetDuration" type="number" step="1" min="5" />
        </div>
        <div class="param">
          <label>混剪模式</label>
          <select v-model="style" @change="onModeChange">
            <option value="marketing">带货直播切片</option>
            <option value="vlog">Vlog 剪辑</option>
            <option value="general">通用混剪</option>
            <option value="rewrite">文案改写</option>
          </select>
          <span class="mode-hint">{{ modeHint }}</span>
        </div>
        <div class="param">
          <label>输出目录</label>
          <input v-model="outputDir" class="path-input" placeholder="如 D:\输出" />
        </div>
      </div>
    </div>

    <div class="actions">
      <button class="btn btn-secondary btn-lg" @click="generatePlan" :disabled="isGenerating">
        {{ isGenerating ? '生成中...' : '1. 生成混剪方案' }}
      </button>
      <button
        class="btn btn-primary btn-lg"
        @click="executePlan"
        :disabled="!planReady || isRunning"
      >
        {{ isRunning ? '渲染中...' : '2. 执行混剪' }}
      </button>
    </div>

    <!-- 方案预览 -->
    <div v-if="clipPlan" class="page-section">
      <h3>混剪方案</h3>
      <p class="section-hint">总时长: {{ clipPlan.total_duration.toFixed(1) }}s | 片段数: {{ clipPlan.segments.length }}</p>
      <div class="plan-table">
        <div class="plan-row plan-header">
          <span>#</span><span>源文件</span><span>开始</span><span>结束</span><span>时长</span><span>叠加文字</span>
        </div>
        <div v-for="(seg, i) in clipPlan.segments" :key="i" class="plan-row">
          <span>{{ i + 1 }}</span>
          <span class="file-cell">{{ getFileName(seg.source_file) }}</span>
          <span>{{ seg.start_time.toFixed(1) }}s</span>
          <span>{{ seg.end_time.toFixed(1) }}s</span>
          <span>{{ (seg.end_time - seg.start_time).toFixed(1) }}s</span>
          <span>{{ seg.text_overlay || '-' }}</span>
        </div>
      </div>
    </div>

    <ProgressBar
      v-if="jobStatus"
      :title="'AI混剪进度'"
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
import { ref, computed, watch } from 'vue'
import axios from 'axios'
import { useSettingsStore } from '@/stores/settings'
import { useProgressStore } from '@/stores/progress'
import ProgressBar from '@/components/common/ProgressBar.vue'
import type { AiClipPlan, JobProgress } from '@/types/api'

const settings = useSettingsStore()
const progressStore = useProgressStore()

const copyText = ref('')
const videoPathInput = ref('')
const videoPaths = ref<string[]>([])
const scanLoading = ref(false)
const scanSummary = ref('')
const targetDuration = ref(45)
const style = ref('marketing')
const outputDir = ref(settings.output_dir)

const isGenerating = ref(false)
const isRunning = ref(false)
const clipPlan = ref<AiClipPlan | null>(null)
const jobId = ref('')
const jobStatus = ref<JobProgress | null>(null)

const planReady = computed(() => clipPlan.value && clipPlan.value.segments.length > 0)

const modeHints: Record<string, string> = {
  marketing: '品类判定 → 噪声过滤 → 黄金钩子 → 暴力说服 → 终极行动',
  vlog: '噪声过滤 → 叙事弧识别（悬念→冲突→高潮→收尾）',
  general: '噪声过滤 → 自由编排 → 打破时间线 → 信息密度优先',
  rewrite: '拆解原文 → 逐点重写 → 多角度叙事（第一/第三人称）',
}

const modeHint = computed(() => modeHints[style.value] || '')

function onModeChange() {
  clipPlan.value = null
}

function getFileName(path: string) {
  return path.split('/').pop()?.split('\\').pop() || path
}

async function scanVideos() {
  const raw = videoPathInput.value.trim()
  if (!raw) return

  scanLoading.value = true
  scanSummary.value = ''
  videoPaths.value = []

  const parts = raw.split(/[,;，；]/).map(s => s.trim()).filter(Boolean)
  const found: string[] = []

  for (const p of parts) {
    try {
      const { data } = await axios.get('/api/files/scan', { params: { path: p } })
      if (data.count > 0) {
        for (const v of data.videos) {
          found.push(v.path)
        }
      } else {
        // 可能是个体文件
        found.push(p)
      }
    } catch {
      // 当文件处理
      found.push(p)
    }
  }

  videoPaths.value = [...new Set(found)]
  scanSummary.value = `找到 ${videoPaths.value.length} 个视频文件`
  scanLoading.value = false
}

async function generatePlan() {
  if (!copyText.value || videoPaths.value.length === 0) {
    alert('请填写文案并选择至少一个视频文件')
    return
  }

  isGenerating.value = true
  clipPlan.value = null

  try {
    const { data } = await axios.post('/api/ai-mix/generate-plan', {
      copy_text: copyText.value,
      video_paths: videoPaths.value,
      target_duration: targetDuration.value,
      style: style.value,
    })

    clipPlan.value = data
  } catch (e: any) {
    alert('方案生成失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    isGenerating.value = false
  }
}

async function executePlan() {
  if (!clipPlan.value) return

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  const outputPath = `${outputDir.value || settings.output_dir}/ai_mix_${timestamp}.mp4`

  isRunning.value = true

  try {
    const { data } = await axios.post('/api/ai-mix/execute', {
      clip_plan: clipPlan.value,
      output_path: outputPath,
      tts_enabled: false,
      tts_voice: 'zh-CN-XiaoxiaoNeural',
      tts_speed: 1.0,
      subtitle_enabled: false,
      subtitle_style: {},
      resolution_w: 1920,
      resolution_h: 1080,
      fps: 30,
      hw_encoder: null,
    })

    jobId.value = data.job_id
    progressStore.connect(data.job_id)

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
    alert('执行失败: ' + (e.response?.data?.detail || e.message))
    isRunning.value = false
  }
}

function cancelMix() {
  if (jobId.value) {
    axios.post(`/api/ai-mix/job/${jobId.value}/cancel`)
    progressStore.cancelJob()
  }
  isRunning.value = false
}
</script>

<style scoped>
.ai-mix { max-width: 800px; }

.page-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}

.page-section h3 { font-size: 16px; margin-bottom: 4px; }
.section-hint { font-size: 12px; color: var(--text-secondary); margin-bottom: 16px; }

.copy-input {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
  resize: vertical;
}

.copy-input:focus { border-color: var(--accent); }

.selected-files {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.tag {
  padding: 4px 10px;
  background: rgba(74, 144, 217, 0.1);
  color: var(--accent);
  border-radius: 4px;
  font-size: 12px;
}

.output-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.param { display: flex; flex-direction: column; gap: 4px; }
.param label { font-size: 12px; font-weight: 600; color: var(--text-secondary); }

.param input, .param select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 14px;
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
}

.param input:focus, .param select:focus { border-color: var(--accent); }

.mode-hint {
  font-size: 11px;
  color: var(--accent);
  margin-top: 4px;
  line-height: 1.3;
}

.actions {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
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

.btn:hover { background: var(--bg-primary); }

.btn-primary { background: var(--accent); color: white; border: none; }
.btn-primary:hover { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-secondary { background: var(--bg-primary); border-color: var(--accent); color: var(--accent); }

.btn-lg { padding: 12px 32px; font-size: 16px; }

.plan-table { font-size: 13px; }
.plan-row { display: grid; grid-template-columns: 30px 1fr 60px 60px 60px 100px; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border); align-items: center; }
.plan-header { font-weight: 600; color: var(--text-secondary); font-size: 12px; }
.file-cell { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
