import uuid
from typing import Optional, Callable, Awaitable
from .ffmpeg_executor import FFmpegProgress


class ProgressTracker:
    """进度追踪器"""

    def __init__(self, job_id: str, total_steps: int = 1):
        self.job_id = job_id
        self.total_steps = total_steps
        self.current_step = 0
        self.step_name = ""
        self.ffmpeg_percent = 0.0
        self.callbacks: list[Callable[[dict], Awaitable[None]]] = []

        self._status = "pending"
        self._current_file = ""
        self._error = None
        self._output_path = None

    @property
    def status(self) -> str:
        return self._status

    @property
    def overall_percent(self) -> float:
        """总体百分比，考虑当前步骤和FFmpeg子进度"""
        if self.total_steps == 0:
            return 0
        base = (self.current_step / self.total_steps) * 100
        step_weight = 100.0 / self.total_steps
        return min(100, base + (self.ffmpeg_percent / 100) * step_weight)

    def set_status(self, status: str):
        self._status = status
        self._notify()

    def set_step(self, index: int, name: str):
        self.current_step = index
        self.step_name = name
        self.ffmpeg_percent = 0.0
        self._notify()

    def set_current_file(self, path: str):
        self._current_file = path
        self._notify()

    def set_error(self, error: str):
        self._error = error
        self._status = "failed"
        self._notify()

    def set_output(self, path: str):
        self._output_path = path
        self._status = "completed"
        self._notify()

    def on_ffmpeg_progress(self, progress: FFmpegProgress):
        self.ffmpeg_percent = progress.percent
        self._notify()

    def on_register_callback(self, cb: Callable[[dict], Awaitable[None]]):
        self.callbacks.append(cb)

    def _notify(self):
        """异步通知所有回调；由外部事件循环驱动"""
        pass

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self._status,
            "current_step": self.step_name,
            "step_index": self.current_step,
            "total_steps": self.total_steps,
            "percent": self.overall_percent,
            "current_file": self._current_file,
            "output_path": self._output_path,
            "error": self._error,
        }


# 全局进度追踪器注册表
_progress_trackers: dict[str, ProgressTracker] = {}


def get_tracker(job_id: str) -> Optional[ProgressTracker]:
    return _progress_trackers.get(job_id)


def create_tracker(job_id: str = "", total_steps: int = 1) -> ProgressTracker:
    job_id = job_id or str(uuid.uuid4())[:8]
    tracker = ProgressTracker(job_id, total_steps)
    _progress_trackers[job_id] = tracker
    return tracker


def remove_tracker(job_id: str):
    _progress_trackers.pop(job_id, None)
