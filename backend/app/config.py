import os
import sys
import json
import shutil
import platform
import tempfile
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Literal


# 存放解压后 FFmpeg 的全局变量
_BUNDLED_FFMPEG_DIR: Optional[str] = None


def get_bundled_resource_dir() -> Path:
    """获取打包资源的解压目录"""
    global _BUNDLED_FFMPEG_DIR

    if getattr(sys, 'frozen', False):
        # PyInstaller 打包模式：资源在 _MEIPASS
        base = Path(sys._MEIPASS)
    else:
        # 开发模式：在 backend 目录下
        base = Path(__file__).parent.parent

    return base


def get_or_extract_ffmpeg() -> tuple[Optional[str], Optional[str]]:
    """获取bundled FFmpeg路径"""
    base = get_bundled_resource_dir()
    bundled_ffmpeg = base / "resources" / "ffmpeg" / "Windows" / "ffmpeg" / "bin" / "ffmpeg.exe"
    bundled_ffprobe = base / "resources" / "ffmpeg" / "Windows" / "ffmpeg" / "bin" / "ffprobe.exe"

    if bundled_ffmpeg.exists() and bundled_ffprobe.exists():
        return str(bundled_ffmpeg), str(bundled_ffprobe)

    return None, None


class AppConfig(BaseModel):
    """全局运行时配置，启动时从JSON加载"""

    # FFmpeg 路径
    ffmpeg_path: Optional[str] = None
    ffprobe_path: Optional[str] = None

    # 工作空间
    workspace_dir: str = ""
    output_dir: str = ""

    # LLM 配置
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.7

    # TTS 配置
    tts_enabled: bool = False
    tts_api_base: str = "https://openspeech.bytedance.com/api/v3/tts"
    tts_api_key: str = ""
    tts_voice: str = "zh-CN-XiaoxiaoNeural"

    # 自定义 Prompt
    custom_prompt_marketing: str = ""
    custom_prompt_vlog: str = ""
    custom_prompt_general: str = ""
    custom_prompt_rewrite: str = ""

    # ASR 配置
    asr_engine: Literal["local", "api"] = "local"
    asr_model_size: Literal["tiny", "base", "small", "medium", "large-v3"] = "medium"
    asr_language: str = "zh"

    # 场景检测
    scene_detection_enabled: bool = False
    scene_model_path: Optional[str] = None

    # 默认输出
    default_resolution_w: int = 1920
    default_resolution_h: int = 1080
    default_fps: int = 30
    default_video_codec: str = "libx264"
    default_audio_codec: str = "aac"
    default_crf: int = 23
    hw_encoder: Optional[str] = None

    # UI
    language: str = "zh-CN"
    theme: Literal["light", "dark", "auto"] = "auto"

    model_config = {"env_prefix": "VMA_"}

    @classmethod
    def _config_dir(cls) -> Path:
        if platform.system() == "Windows":
            base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
            return Path(base) / "video-mix-app"
        else:
            return Path.home() / ".config" / "video-mix-app"

    @classmethod
    def _auto_detect_ffmpeg(cls) -> tuple[Optional[str], Optional[str]]:
        """自动检测 FFmpeg 路径"""
        # 0. Bundled（最高优先级）
        bundled = get_or_extract_ffmpeg()
        if bundled[0] and bundled[1]:
            return bundled

        # 1. 系统 PATH
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if ffmpeg and ffprobe:
            return ffmpeg, ffprobe

        # 2. 常见安装位置
        candidates = [
            Path("D:/ECutauto/Resources/FFmpeg/Windows/ffmpeg/bin"),
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "FFmpeg/bin",
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "FFmpeg/bin",
            Path.home() / "ffmpeg/bin",
        ]
        for d in candidates:
            ffmpeg_exe = d / "ffmpeg.exe"
            ffprobe_exe = d / "ffprobe.exe"
            if ffmpeg_exe.exists() and ffprobe_exe.exists():
                return str(ffmpeg_exe), str(ffprobe_exe)

        return None, None

    @classmethod
    def load(cls) -> "AppConfig":
        config_dir = cls._config_dir()
        config_file = config_dir / "settings.json"
        config_dir.mkdir(parents=True, exist_ok=True)

        data = {}
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        cls._fill_defaults(data)

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return cls(**data)

    def save(self):
        config_dir = self._config_dir()
        config_file = config_dir / "settings.json"
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)

    @classmethod
    def _fill_defaults(cls, data: dict):
        defaults = {
            "workspace_dir": str(Path.home() / "Documents" / "VideoMixApp" / "workspace"),
            "output_dir": str(Path.home() / "Documents" / "VideoMixApp" / "output"),
            "language": "zh-CN",
            "theme": "auto",
        }
        for k, v in defaults.items():
            data.setdefault(k, v)

        if not data.get("ffmpeg_path"):
            ffmpeg, ffprobe = cls._auto_detect_ffmpeg()
            if ffmpeg:
                data["ffmpeg_path"] = ffmpeg
                data["ffprobe_path"] = ffprobe

        for key in ["workspace_dir", "output_dir"]:
            if data.get(key):
                Path(data[key]).mkdir(parents=True, exist_ok=True)


_config_instance: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig.load()
    return _config_instance


def reload_config() -> AppConfig:
    global _config_instance
    _config_instance = AppConfig.load()
    return _config_instance
