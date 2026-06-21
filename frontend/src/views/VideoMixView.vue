<template>
  <div class="video-mix">
    <div class="page-section">
      <h3>轨道管理</h3>
      <p class="section-hint">添加视频轨道，每个轨道包含一个视频文件和时间范围</p>

      <div class="tracks">
        <div v-for="(track, i) in tracks" :key="i" class="track-card">
          <div class="track-header">
            <span class="track-label">轨道 {{ i + 1 }}</span>
            <button class="btn-icon" @click="removeTrack(i)" v-if="tracks.length > 1">X</button>
          </div>
          <div class="track-body">
            <div class="param">
              <label>视频文件</label>
              <FilePicker v-model="track.file_path" label="选择视频" />
            </div>
            <div class="track-row">
              <div class="param">
                <label>起始 (秒)</label>
                <input v-model.number="track.start" type="number" step="1" min="0" />
              </div>
              <div class="param">
                <label>结束 (秒, 0=末尾)</label>
                <input v-model.number="track.end" type="number" step="1" min="0" />
              </div>
            </div>
            <div class="track-row" v-if="tracks.length > 1">
              <div class="param">
                <label>缩放</label>
                <input v-model.number="track.scale" type="number" step="0.1" min="0.1" max="5" />
              </div>
              <div class="param">
                <label>音量</label>
                <input v-model.number="track.volume" type="number" step="0.1" min="0" max="2" />
              </div>
              <div class="param">
                <label>速度</label>
                <select v-model.number="track.speed">
                  <option :value="0.5">0.5x</option>
                  <option :value="1">1x</option>
                  <option :value="1.5">1.5x</option>
                  <option :value="2">2x</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>

      <button class="btn" @click="addTrack">+ 添加轨道</button>
    </div>

    <div class="page-section">
      <h3>输出设置</h3>
      <div class="output-grid">
        <div class="param">
          <label>分辨率</label>
          <select v-model="resolution">
            <option value="1920x1080">1920x1080</option>
            <option value="1280x720">1280x720</option>
          </select>
        </div>
        <div class="param">
          <label>视频编码</label>
          <select v-model="videoCodec">
            <option value="libx264">H.264</option>
            <option value="libx265">H.265</option>
          </select>
        </div>
        <div class="param">
          <label>CRF (质量)</label>
          <input v-model.number="crf" type="number" min="0" max="51" />
        </div>
        <div class="param">
          <label>preset</label>
          <select v-model="preset">
            <option value="fast">fast</option>
            <option value="medium">medium</option>
            <option value="slow">slow</option>
          </select>
        </div>
        <div class="param">
          <label>输出路径</label>
          <FilePicker v-model="outputDir" label="选择输出目录" :folders-only="true" />
        </div>
      </div>
    </div>

    <button class="btn btn-primary btn-lg" @click="startRender" :disabled="isRunning">
      {{ isRunning ? '渲染中...' : '开始渲染' }}
    </button>

    <ProgressBar
      v-if="jobStatus"
      title="视频混剪进度"
      :percent="jobStatus.percent"
      :status="jobStatus.status"
      :step="jobStatus.current_step"
      :current-file="jobStatus.current_file || ''"
      :logs="progressStore.logs"
      @cancel="cancelRender"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import axios from 'axios'
import { useSettingsStore } from '@/stores/settings'
import { useProgressStore } from '@/stores/progress'
import FilePicker from '@/components/common/FilePicker.vue'
import ProgressBar from '@/components/common/ProgressBar.vue'
import type { VideoTrack, JobProgress } from '@/types/api'

const settings = useSettingsStore()
const progressStore = useProgressStore()

const tracks = reactive<VideoTrack[]>([
  { file_path: '', start: 0, end: 0, layer: 0, position_x: null, position_y: null, scale: 1, volume: 1, speed: 1 },
])

const resolution = ref('1920x1080')
const videoCodec = ref('libx264')
const crf = ref(23)
const preset = ref('medium')
const outputDir = ref(settings.output_dir)

const isRunning = ref(false)
const jobId = ref('')
const jobStatus = ref<JobProgress | null>(null)

function addTrack() {
  tracks.push({ file_path: '', start: 0, end: 0, layer: tracks.length, position_x: null, position_y: null, scale: 1, volume: 1, speed: 1 })
}

function removeTrack(index: number) {
  tracks.splice(index, 1)
}

async function startRender() {
  const validTracks = tracks.filter(t => t.file_path)
  if (validTracks.length === 0) {
    alert('请至少添加一个有效轨道')
    return
  }

  const [w, h] = resolution.value.split('x').map(Number)
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  const outputPath = `${outputDir.value || settings.output_dir}/video_mix_${timestamp}.mp4`

  isRunning.value = true

  try {
    const { data } = await axios.post('/api/video-mix/render', {
      tracks: validTracks,
      filter_graph: [],
      output_path: outputPath,
      output_settings: {
        resolution_w: w,
        resolution_h: h,
        fps: 30,
        video_codec: videoCodec.value,
        audio_codec: 'aac',
        crf: crf.value,
        preset: preset.value,
      },
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
    alert('渲染失败: ' + (e.response?.data?.detail || e.message))
    isRunning.value = false
  }
}

function cancelRender() {
  if (jobId.value) {
    axios.post(`/api/video-mix/job/${jobId.value}/cancel`)
    progressStore.cancelJob()
  }
  isRunning.value = false
}
</script>

<style scoped>
.video-mix { max-width: 800px; }

.page-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}

.page-section h3 { font-size: 16px; margin-bottom: 4px; }
.section-hint { font-size: 12px; color: var(--text-secondary); margin-bottom: 16px; }

.tracks { display: flex; flex-direction: column; gap: 12px; }

.track-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.track-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border);
}

.track-label { font-size: 13px; font-weight: 600; }

.btn-icon {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
}

.track-body { padding: 12px; }

.track-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; }

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

.output-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.btn {
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 13px;
  margin-top: 10px;
}

.btn:hover { background: var(--bg-primary); }

.btn-primary { background: var(--accent); color: white; border: none; }
.btn-primary:hover { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-lg { padding: 12px 32px; font-size: 16px; margin-bottom: 20px; }
</style>
