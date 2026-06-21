<template>
  <div class="settings">
    <div class="page-section">
      <h3>FFmpeg 设置</h3>
      <div class="setting-row">
        <label>FFmpeg 路径</label>
        <div class="setting-input-group">
          <input v-model="settings.ffmpeg_path" placeholder="自动检测或手动指定" />
          <button class="btn" @click="autoDetect">自动检测</button>
        </div>
      </div>
      <div class="setting-row">
        <label>FFprobe 路径</label>
        <input v-model="settings.ffprobe_path" placeholder="自动检测或手动指定" />
      </div>
    </div>

    <div class="page-section">
      <h3>LLM API 设置（AI智能混剪用）</h3>
      <div class="setting-row">
        <label>API 地址</label>
        <input v-model="settings.llm_api_base" placeholder="https://api.openai.com/v1" />
      </div>
      <div class="setting-row">
        <label>API Key</label>
        <input v-model="settings.llm_api_key" type="password" placeholder="sk-..." />
      </div>
      <div class="setting-row">
        <label>模型</label>
        <input v-model="settings.llm_model" placeholder="gpt-4o" />
      </div>
      <div class="setting-row">
        <label>最大 Token</label>
        <input v-model.number="settings.llm_max_tokens" type="number" />
      </div>
    </div>

    <div class="page-section">
      <h3>ASR 设置</h3>
      <div class="setting-row">
        <label>引擎</label>
        <select v-model="settings.asr_engine">
          <option value="local">本地 (faster-whisper)</option>
          <option value="api">API</option>
        </select>
      </div>
      <div class="setting-row">
        <label>模型大小</label>
        <select v-model="settings.asr_model_size">
          <option value="tiny">tiny</option>
          <option value="base">base</option>
          <option value="small">small</option>
          <option value="medium">medium</option>
          <option value="large-v3">large-v3</option>
        </select>
      </div>
    </div>

    <div class="page-section">
      <h3>默认输出设置</h3>
      <div class="setting-row">
        <label>默认分辨率</label>
        <div class="setting-inline">
          <input v-model.number="settings.default_resolution_w" type="number" class="small" />
          <span>x</span>
          <input v-model.number="settings.default_resolution_h" type="number" class="small" />
        </div>
      </div>
      <div class="setting-row">
        <label>默认帧率</label>
        <input v-model.number="settings.default_fps" type="number" />
      </div>
      <div class="setting-row">
        <label>默认视频编码</label>
        <select v-model="settings.default_video_codec">
          <option value="libx264">H.264</option>
          <option value="libx265">H.265</option>
          <option value="h264_nvenc">H.264 NVENC</option>
          <option value="h264_amf">H.264 AMF</option>
        </select>
      </div>
      <div class="setting-row">
        <label>默认 CRF</label>
        <input v-model.number="settings.default_crf" type="number" min="0" max="51" />
      </div>
    </div>

    <button class="btn btn-primary btn-lg" @click="saveSettings">保存设置</button>
    <span v-if="saved" class="saved-msg">保存成功</span>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()
const saved = ref(false)

async function autoDetect() {
  const result = await settings.autoDetect()
  if (result.found) {
    alert(`已自动检测到 FFmpeg:\n${result.ffmpeg_path}`)
  } else {
    alert('未找到 FFmpeg，请手动指定路径')
  }
}

async function saveSettings() {
  try {
    await settings.save()
    saved.value = true
    setTimeout(() => { saved.value = false }, 2000)
  } catch (e) {
    alert('保存设置失败')
  }
}

onMounted(() => {
  settings.load()
})
</script>

<style scoped>
.settings { max-width: 700px; }

.page-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}

.page-section h3 {
  font-size: 16px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}

.setting-row:last-child { border-bottom: none; }

.setting-row label {
  font-size: 13px;
  font-weight: 600;
  min-width: 120px;
}

.setting-row input, .setting-row select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  width: 320px;
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
}

.setting-row input:focus, .setting-row select:focus {
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

.saved-msg {
  margin-left: 12px;
  color: var(--success);
  font-size: 14px;
}
</style>
