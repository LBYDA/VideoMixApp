export interface JobProgress {
  job_id: string
  job_type: string
  status: string
  current_step: string
  step_index: number
  total_steps: number
  percent: number
  estimated_remaining: number | null
  current_file: string | null
  output_path: string | null
  error: string | null
}

export interface VideoProbe {
  file_path: string
  duration: number
  width: number
  height: number
  fps: number
  video_codec: string
  audio_codec: string
  has_audio: boolean
  has_video: boolean
  file_size: number
}

export interface FileTreeItem {
  path: string
  name: string
  is_dir: boolean
  children: FileTreeItem[] | null
  size: number
}

export interface CategoryGroup {
  name: string
  source_dir: string
  max_clip_duration: number
  min_clip_duration: number
  scene_threshold: number
  priority: number
}

export interface CategoryMixRequest {
  groups: CategoryGroup[]
  target_duration: number
  quality: string
  output_path: string
  resolution_w: number
  resolution_h: number
  fps: number
  transition: string
  transition_duration: number
  scene_detection: boolean
  hw_encoder: string | null
}

export interface ClipSegment {
  source_file: string
  start_time: number
  end_time: number
  text_overlay: string | null
  transition: string
}

export interface AiClipPlan {
  segments: ClipSegment[]
  total_duration: number
}

export interface AiMixInput {
  copy_text: string
  video_paths: string[]
  target_duration: number
  style: string
}

export interface AiMixExecuteRequest {
  clip_plan: AiClipPlan
  output_path: string
  tts_enabled: boolean
  tts_voice: string
  tts_speed: number
  subtitle_enabled: boolean
  subtitle_style: Record<string, any>
  resolution_w: number
  resolution_h: number
  fps: number
  hw_encoder: string | null
}

export interface VideoTrack {
  file_path: string
  start: number
  end: number
  layer: number
  position_x: number | null
  position_y: number | null
  scale: number
  volume: number
  speed: number
}

export interface OutputSettings {
  resolution_w: number
  resolution_h: number
  fps: number
  video_codec: string
  audio_codec: string
  crf: number
  preset: string
}

export interface VideoMixRequest {
  tracks: VideoTrack[]
  filter_graph: any[]
  output_path: string
  output_settings: OutputSettings
}

export interface AppSettings {
  ffmpeg_path: string | null
  ffprobe_path: string | null
  workspace_dir: string
  output_dir: string
  llm_api_base: string
  llm_api_key: string
  llm_model: string
  llm_max_tokens: number
  asr_engine: string
  asr_model_size: string
  asr_language: string
  scene_detection_enabled: boolean
  default_resolution_w: number
  default_resolution_h: number
  default_fps: number
  default_video_codec: string
  default_audio_codec: string
  default_crf: number
  hw_encoder: string | null
  language: string
  theme: string
}
