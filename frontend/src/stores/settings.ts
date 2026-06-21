import { defineStore } from 'pinia'
import axios from 'axios'
import type { AppSettings } from '@/types/api'

export const useSettingsStore = defineStore('settings', {
  state: (): AppSettings & { loaded: boolean } => ({
    loaded: false,
    ffmpeg_path: null,
    ffprobe_path: null,
    workspace_dir: '',
    output_dir: '',
    llm_api_base: 'https://api.openai.com/v1',
    llm_api_key: '',
    llm_model: 'gpt-4o',
    llm_max_tokens: 4096,
    asr_engine: 'local',
    asr_model_size: 'medium',
    asr_language: 'zh',
    scene_detection_enabled: false,
    default_resolution_w: 1920,
    default_resolution_h: 1080,
    default_fps: 30,
    default_video_codec: 'libx264',
    default_audio_codec: 'aac',
    default_crf: 23,
    hw_encoder: null,
    language: 'zh-CN',
    theme: 'auto',
  }),

  actions: {
    async load() {
      try {
        const { data } = await axios.get('/api/settings')
        Object.assign(this, data)
        this.loaded = true
      } catch (e) {
        console.error('Failed to load settings:', e)
      }
    },

    async save() {
      const payload = { ...this }
      delete (payload as any).loaded
      await axios.put('/api/settings', payload)
    },

    async autoDetect() {
      const { data } = await axios.post('/api/settings/auto-detect')
      if (data.found) {
        this.ffmpeg_path = data.ffmpeg_path
        this.ffprobe_path = data.ffprobe_path
        await this.save()
      }
      return data
    },
  },
})
