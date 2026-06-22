from fastapi import APIRouter
from ..config import AppConfig, get_config, reload_config
from ..models.schemas import AutoDetectResult

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings() -> dict:
    cfg = get_config()
    return cfg.model_dump()


@router.put("")
async def update_settings(data: dict):
    cfg = get_config()
    # 只更新允许的字段
    allowed = {
        "ffmpeg_path", "ffprobe_path", "workspace_dir", "output_dir",
        "llm_api_base", "llm_api_key", "llm_model", "llm_max_tokens", "llm_temperature",
        "tts_enabled", "tts_api_base", "tts_api_key", "tts_voice",
        "custom_prompt_marketing", "custom_prompt_vlog", "custom_prompt_general", "custom_prompt_rewrite",
        "asr_engine", "asr_model_size", "asr_language",
        "scene_detection_enabled", "scene_model_path",
        "default_resolution_w", "default_resolution_h", "default_fps",
        "default_video_codec", "default_audio_codec", "default_crf",
        "hw_encoder", "language", "theme",
    }
    for k, v in data.items():
        if k in allowed and hasattr(cfg, k):
            setattr(cfg, k, v)

    cfg.save()
    return {"ok": True}


@router.post("/auto-detect")
async def auto_detect() -> AutoDetectResult:
    ffmpeg, ffprobe = AppConfig._auto_detect_ffmpeg()
    return AutoDetectResult(
        ffmpeg_path=ffmpeg,
        ffprobe_path=ffprobe,
        found=ffmpeg is not None,
    )
