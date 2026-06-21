from enum import Enum
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field


# ─── Enums ───

class JobStatus(str, Enum):
    PENDING = "pending"
    SCANNING = "scanning"
    PROBING = "probing"
    PLANNING = "planning"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransitionType(str, Enum):
    NONE = "none"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE = "wipe"
    SLIDE = "slide"


class QualityPreset(str, Enum):
    SPEED = "speed"
    BALANCED = "balanced"
    QUALITY = "quality_priority"


# ─── Category Mix ───

class CategoryGroup(BaseModel):
    name: str
    source_dir: str
    max_clip_duration: float = 5.0
    min_clip_duration: float = 2.0
    scene_threshold: float = 0.3
    priority: int = 0


class CategoryMixRequest(BaseModel):
    groups: list[CategoryGroup]
    target_duration: float
    quality: QualityPreset = QualityPreset.BALANCED
    output_path: str
    resolution_w: int = 1920
    resolution_h: int = 1080
    fps: int = 30
    transition: TransitionType = TransitionType.NONE
    transition_duration: float = 0.5
    scene_detection: bool = False
    hw_encoder: Optional[str] = None


# ─── AI Mix ───

class AiMixInput(BaseModel):
    copy_text: str
    video_paths: list[str]
    target_duration: float
    style: str = "marketing"


class ClipSegment(BaseModel):
    source_file: str
    start_time: float
    end_time: float
    text_overlay: Optional[str] = None
    transition: str = "none"


class AiClipPlan(BaseModel):
    segments: list[ClipSegment]
    total_duration: float = 0.0


class AiMixExecuteRequest(BaseModel):
    clip_plan: AiClipPlan
    output_path: str
    tts_enabled: bool = False
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_speed: float = 1.0
    subtitle_enabled: bool = False
    subtitle_style: dict[str, Any] = Field(default_factory=dict)
    resolution_w: int = 1920
    resolution_h: int = 1080
    fps: int = 30
    hw_encoder: Optional[str] = None


# ─── Video Mix ───

class FilterChainNode(BaseModel):
    type: str
    params: dict[str, Any] = Field(default_factory=dict)


class VideoTrack(BaseModel):
    file_path: str
    start: float = 0.0
    end: float = 0.0
    layer: int = 0
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    scale: float = 1.0
    volume: float = 1.0
    speed: float = 1.0


class OutputSettings(BaseModel):
    resolution_w: int = 1920
    resolution_h: int = 1080
    fps: int = 30
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    crf: int = 23
    preset: str = "medium"


class VideoMixRequest(BaseModel):
    tracks: list[VideoTrack]
    filter_graph: list[FilterChainNode] = Field(default_factory=list)
    output_path: str
    output_settings: OutputSettings = Field(default_factory=OutputSettings)


# ─── Common ───

class FileTreeResponse(BaseModel):
    path: str
    name: str
    is_dir: bool
    children: Optional[list["FileTreeResponse"]] = None
    size: int = 0


class VideoProbeResponse(BaseModel):
    file_path: str
    duration: float
    width: int
    height: int
    fps: float
    video_codec: str
    audio_codec: str
    has_audio: bool
    has_video: bool
    file_size: int


class JobProgressResponse(BaseModel):
    job_id: str
    job_type: str = ""
    status: JobStatus
    current_step: str = ""
    step_index: int = 0
    total_steps: int = 0
    percent: float = 0.0
    estimated_remaining: Optional[float] = None
    current_file: Optional[str] = None
    output_path: Optional[str] = None
    error: Optional[str] = None


class JobCreatedResponse(BaseModel):
    job_id: str


class AutoDetectResult(BaseModel):
    ffmpeg_path: Optional[str] = None
    ffprobe_path: Optional[str] = None
    found: bool = False


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


FileTreeResponse.model_rebuild()
