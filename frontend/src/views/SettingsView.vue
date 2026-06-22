<template>
  <div class="settings">
    <!-- LLM API -->
    <div class="page-section">
      <h3>LLM API 设置（AI智能混剪）</h3>
      <p class="section-hint">支持 OpenAI 兼容接口：OpenAI / 火山引擎 / 通义千问 / DeepSeek 等</p>

      <div class="api-presets">
        <span class="preset-label">快速选择：</span>
        <button v-for="p in apiPresets" :key="p.name"
          class="btn btn-preset" @click="applyPreset(p)">{{ p.name }}</button>
      </div>

      <div class="setting-row">
        <label>API 地址</label>
        <input v-model="settings.llm_api_base" placeholder="https://api.openai.com/v1" />
      </div>
      <div class="setting-row">
        <label>API Key</label>
        <div class="setting-input-group">
          <input v-model="settings.llm_api_key" :type="showKey ? 'text' : 'password'" placeholder="sk-..." />
          <button class="btn btn-sm" @click="showKey = !showKey">{{ showKey ? '隐藏' : '显示' }}</button>
        </div>
      </div>
      <div class="setting-row">
        <label>模型名称</label>
        <input v-model="settings.llm_model" placeholder="gpt-4o / deepseek-chat / doubao-pro-32k" />
      </div>
      <div class="setting-row">
        <label>最大 Token</label>
        <input v-model.number="settings.llm_max_tokens" type="number" min="256" max="32768" />
      </div>
      <div class="setting-row">
        <label>Temperature</label>
        <div class="setting-inline">
          <input v-model.number="settings.llm_temperature" type="range" min="0" max="2" step="0.1" class="slider" />
          <span class="slider-val">{{ settings.llm_temperature }}</span>
        </div>
      </div>
    </div>

    <!-- TTS API -->
    <div class="page-section">
      <h3>TTS API 设置（可选）</h3>
      <p class="section-hint">AI混剪中为视频添加配音</p>
      <div class="setting-row">
        <label>启用 TTS</label>
        <input type="checkbox" v-model="settings.tts_enabled" />
      </div>
      <div class="setting-row">
        <label>TTS API 地址</label>
        <input v-model="settings.tts_api_base" placeholder="https://openspeech.bytedance.com/api/v3/tts" />
      </div>
      <div class="setting-row">
        <label>TTS API Key</label>
        <input v-model="settings.tts_api_key" type="password" placeholder="火山引擎 TTS Key" />
      </div>
      <div class="setting-row">
        <label>默认音色</label>
        <select v-model="settings.tts_voice">
          <option value="zh-CN-XiaoxiaoNeural">晓晓 (女-温柔)</option>
          <option value="zh-CN-YunxiNeural">云希 (男-磁性)</option>
          <option value="zh-CN-XiaoyiNeural">晓伊 (女-活泼)</option>
          <option value="zh-CN-YunjianNeural">云健 (男-阳光)</option>
          <option value="BV001_streaming">豆包-女声 (火山)</option>
          <option value="BV002_streaming">豆包-男声 (火山)</option>
        </select>
      </div>
    </div>

    <!-- 自定义 Prompt -->
    <div class="page-section">
      <h3>自定义 Prompt（高级）</h3>
      <p class="section-hint">覆盖内置的4种Prompt。留空则使用内置Prompt</p>

      <div class="setting-row">
        <label>带货直播切片 Prompt</label>
        <textarea v-model="settings.custom_prompt_marketing" rows="3" placeholder="留空使用内置"></textarea>
      </div>
      <div class="setting-row">
        <label>Vlog 剪辑 Prompt</label>
        <textarea v-model="settings.custom_prompt_vlog" rows="3" placeholder="留空使用内置"></textarea>
      </div>
      <div class="setting-row">
        <label>通用混剪 Prompt</label>
        <textarea v-model="settings.custom_prompt_general" rows="3" placeholder="留空使用内置"></textarea>
      </div>
      <div class="setting-row">
        <label>文案改写 Prompt</label>
        <textarea v-model="settings.custom_prompt_rewrite" rows="3" placeholder="留空使用内置"></textarea>
      </div>
    </div>

    <!-- FFmpeg -->
    <div class="page-section">
      <h3>FFmpeg 设置</h3>
      <div class="setting-row">
        <label>FFmpeg 路径</label>
        <div class="setting-input-group">
          <input v-model="settings.ffmpeg_path" placeholder="自动检测" />
          <button class="btn" @click="autoDetect">自动检测</button>
        </div>
      </div>
      <div class="setting-row">
        <label>FFprobe 路径</label>
        <input v-model="settings.ffprobe_path" placeholder="自动检测" />
      </div>
      <div class="setting-row">
        <label>硬件加速</label>
        <select v-model="settings.hw_encoder">
          <option value="">无 (libx264)</option>
          <option value="h264_nvenc">NVIDIA NVENC</option>
          <option value="h264_amf">AMD AMF</option>
          <option value="h264_qsv">Intel QSV</option>
        </select>
      </div>
    </div>

    <!-- 默认输出 -->
    <div class="page-section">
      <h3>默认输出设置</h3>
      <div class="setting-row">
        <label>分辨率</label>
        <div class="setting-inline">
          <input v-model.number="settings.default_resolution_w" type="number" class="small" />
          <span>x</span>
          <input v-model.number="settings.default_resolution_h" type="number" class="small" />
        </div>
      </div>
      <div class="setting-row">
        <label>帧率</label>
        <input v-model.number="settings.default_fps" type="number" />
      </div>
      <div class="setting-row">
        <label>视频编码</label>
        <select v-model="settings.default_video_codec">
          <option value="libx264">H.264</option>
          <option value="libx265">H.265</option>
        </select>
      </div>
      <div class="setting-row">
        <label>CRF (质量)</label>
        <input v-model.number="settings.default_crf" type="number" min="0" max="51" />
      </div>
      <div class="setting-row">
        <label>输出目录</label>
        <input v-model="settings.output_dir" placeholder="如 D:\输出" />
      </div>
    </div>

    <button class="btn btn-primary btn-lg" @click="saveSettings">保存设置</button>
    <span v-if="saved" class="saved-msg">保存成功</span>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import axios from 'axios'

interface ApiPreset {
  name: string
  base: string
  model: string
}

const apiPresets: ApiPreset[] = [
  { name: 'OpenAI', base: 'https://api.openai.com/v1', model: 'gpt-4o' },
  { name: '火山引擎(豆包)', base: 'https://ark.cn-beijing.volces.com/api/v3', model: 'doubao-pro-32k' },
  { name: '通义千问', base: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  { name: 'DeepSeek', base: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
]

const saved = ref(false)
const showKey = ref(false)

const settings = reactive({
  // LLM
  llm_api_base: 'https://api.openai.com/v1',
  llm_api_key: '',
  llm_model: 'gpt-4o',
  llm_max_tokens: 4096,
  llm_temperature: 0.7,
  // TTS
  tts_enabled: false,
  tts_api_base: 'https://openspeech.bytedance.com/api/v3/tts',
  tts_api_key: '',
  tts_voice: 'zh-CN-XiaoxiaoNeural',
  // Custom prompts
  custom_prompt_marketing: '',
  custom_prompt_vlog: '',
  custom_prompt_general: '',
  custom_prompt_rewrite: '',
  // FFmpeg
  ffmpeg_path: '',
  ffprobe_path: '',
  hw_encoder: '',
  // Output
  default_resolution_w: 1920,
  default_resolution_h: 1080,
  default_fps: 30,
  default_video_codec: 'libx264',
  default_audio_codec: 'aac',
  default_crf: 23,
  output_dir: '',
  // UI
  theme: 'auto',
  language: 'zh-CN',
})

function applyPreset(p: ApiPreset) {
  settings.llm_api_base = p.base
  settings.llm_model = p.model
}

async function autoDetect() {
  try {
    const { data } = await axios.post('/api/settings/auto-detect')
    if (data.found) {
      settings.ffmpeg_path = data.ffmpeg_path || ''
      settings.ffprobe_path = data.ffprobe_path || ''
      alert(`已自动检测到 FFmpeg:\n${data.ffmpeg_path}`)
    } else {
      alert('未找到 FFmpeg，请手动指定路径')
    }
  } catch {
    alert('检测失败')
  }
}

async function saveSettings() {
  try {
    await axios.put('/api/settings', { ...settings })
    saved.value = true
    setTimeout(() => { saved.value = false }, 2000)
  } catch {
    alert('保存失败')
  }
}

async function loadSettings() {
  try {
    const { data } = await axios.get('/api/settings')
    Object.keys(settings).forEach(k => {
      if (k in data) (settings as any)[k] = data[k]
    })
  } catch { /* use defaults */ }
}

onMounted(loadSettings)
</script>

<style scoped>
.settings { max-width: 760px; }

.page-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}

.page-section h3 {
  font-size: 16px;
  margin-bottom: 6px;
}

.section-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.api-presets {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 14px;
  align-items: center;
}

.preset-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.btn-preset {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 4px;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  gap: 12px;
}

.setting-row:last-child { border-bottom: none; }

.setting-row label {
  font-size: 13px;
  font-weight: 600;
  min-width: 140px;
  padding-top: 8px;
}

.setting-row input:not([type="checkbox"]):not([type="range"]),
.setting-row select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  width: 320px;
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
}

.setting-row textarea {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 12px;
  width: 320px;
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
  resize: vertical;
  font-family: inherit;
}

.setting-row input:focus, .setting-row select:focus, .setting-row textarea:focus {
  border-color: var(--accent);
}

.setting-row input.small { width: 80px; }

.setting-input-group {
  display: flex;
  gap: 8px;
  align-items: center;
}

.setting-inline {
  display: flex;
  gap: 8px;
  align-items: center;
}

.slider { width: 200px; accent-color: var(--accent); }
.slider-val { font-size: 13px; font-weight: 600; min-width: 28px; }

.btn {
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.btn:hover { background: var(--bg-primary); }

.btn-primary { background: var(--accent); color: white; border: none; }
.btn-primary:hover { background: var(--accent-hover); }

.btn-lg { padding: 12px 32px; font-size: 16px; }

.btn-sm { padding: 4px 10px; font-size: 12px; }

.saved-msg {
  margin-left: 12px;
  color: var(--success);
  font-size: 14px;
}
</style>
