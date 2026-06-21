import asyncio
import os
import re
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)


@dataclass
class FFmpegProgress:
    frame: int = 0
    fps: float = 0.0
    time_str: str = "00:00:00.00"
    time_seconds: float = 0.0
    speed: float = 0.0
    bitrate: str = ""
    percent: float = 0.0
    raw_line: str = ""


@dataclass
class FFmpegResult:
    returncode: int
    stdout: str
    stderr: str
    output_file: str
    duration: float = 0.0


@dataclass
class VideoProbe:
    file_path: str
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    video_codec: str = ""
    audio_codec: str = ""
    bitrate: int = 0
    has_audio: bool = False
    has_video: bool = False
    file_size: int = 0
    raw: dict = field(default_factory=dict)


class FFmpegExecutor:
    """FFmpeg 子进程管理器"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._processes: dict[str, asyncio.subprocess.Process] = {}

    def _get_cancel_event(self, job_id: str) -> asyncio.Event:
        if job_id not in self._cancel_events:
            self._cancel_events[job_id] = asyncio.Event()
        return self._cancel_events[job_id]

    def cancel(self, job_id: str):
        """取消指定任务"""
        event = self._cancel_events.get(job_id)
        if event:
            event.set()
        proc = self._processes.get(job_id)
        if proc and proc.returncode is None:
            try:
                # 发送 'q' 让 FFmpeg 优雅退出
                if proc.stdin:
                    proc.stdin.write(b"q")
                    proc.stdin.close()
            except Exception:
                pass
            try:
                proc.terminate()
            except Exception:
                pass

    def cleanup(self, job_id: str):
        self._cancel_events.pop(job_id, None)
        self._processes.pop(job_id, None)

    async def run(
        self,
        args: list[str],
        job_id: str = "",
        total_duration: float = 0.0,
        progress_callback: Optional[Callable[[FFmpegProgress], Awaitable[None]]] = None,
    ) -> FFmpegResult:
        """执行 FFmpeg 命令"""
        cmd = [self.ffmpeg_path, "-y", "-hide_banner", "-progress", "pipe:1"] + args

        cancel_event = self._get_cancel_event(job_id)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[job_id] = proc

            stdout_data = []
            stderr_data = []

            async def read_stderr():
                while True:
                    line = await proc.stderr.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace").rstrip()
                    stderr_data.append(decoded)

            async def read_stdout():
                last_progress = FFmpegProgress()
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace").rstrip()
                    stdout_data.append(decoded)

                    # 检查取消
                    if cancel_event.is_set():
                        if proc.stdin:
                            proc.stdin.write(b"q")
                            proc.stdin.close()
                        break

                    # 解析进度行
                    progress = self._parse_progress_line(decoded, last_progress, total_duration)
                    if progress:
                        last_progress = progress
                        if progress_callback:
                            await progress_callback(progress)

            # 并行读取 stdout 和 stderr
            await asyncio.gather(read_stdout(), read_stderr())

            # 等待进程结束
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.terminate()
                await proc.wait()

            result = FFmpegResult(
                returncode=proc.returncode or 0,
                stdout="\n".join(stdout_data),
                stderr="\n".join(stderr_data),
                output_file=args[-1] if args else "",
            )

            return result

        except Exception as e:
            logger.exception(f"FFmpeg error: {e}")
            return FFmpegResult(
                returncode=-1,
                stdout="",
                stderr=str(e),
                output_file=args[-1] if args else "",
            )
        finally:
            self.cleanup(job_id)

    @staticmethod
    def _parse_progress_line(line: str, last: FFmpegProgress, total_duration: float) -> Optional[FFmpegProgress]:
        """解析 FFmpeg progress 输出行"""
        p = FFmpegProgress()
        changed = False

        for part in line.split():
            if "=" in part:
                key, val = part.split("=", 1)
                if key == "frame":
                    p.frame = int(val)
                    changed = True
                elif key == "fps":
                    try:
                        p.fps = float(val)
                    except ValueError:
                        pass
                    changed = True
                elif key == "out_time_us":
                    try:
                        p.time_seconds = int(val) / 1_000_000
                        changed = True
                    except ValueError:
                        pass
                elif key == "out_time":
                    p.time_str = val
                    try:
                        h, m, s = val.split(":")
                        p.time_seconds = float(h) * 3600 + float(m) * 60 + float(s)
                        changed = True
                    except (ValueError, AttributeError):
                        pass
                elif key == "speed":
                    try:
                        val_clean = val.replace("x", "")
                        p.speed = float(val_clean)
                    except ValueError:
                        pass
                    changed = True

        if changed and total_duration > 0:
            p.percent = min(100.0, (p.time_seconds / total_duration) * 100)
        p.raw_line = line
        return p if changed else None

    async def probe(self, file_path: str) -> Optional[VideoProbe]:
        """获取视频元数据"""
        if not os.path.exists(file_path):
            return None

        cmd = [
            self.ffprobe_path, "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            file_path
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return None

            import json
            data = json.loads(stdout.decode("utf-8"))

            probe = VideoProbe(file_path=file_path, raw=data)
            fmt = data.get("format", {})

            probe.duration = float(fmt.get("duration", 0))
            probe.bitrate = int(fmt.get("bit_rate", 0))
            probe.file_size = int(fmt.get("size", 0))

            for stream in data.get("streams", []):
                if stream["codec_type"] == "video":
                    probe.has_video = True
                    probe.width = stream.get("width", 0)
                    probe.height = stream.get("height", 0)
                    probe.video_codec = stream.get("codec_name", "")

                    # 解析帧率
                    fps_str = stream.get("r_frame_rate", "0/1")
                    if "/" in fps_str:
                        num, den = fps_str.split("/")
                        try:
                            probe.fps = float(num) / float(den)
                        except (ValueError, ZeroDivisionError):
                            probe.fps = float(stream.get("avg_frame_rate", "0").split("/")[0])
                    else:
                        try:
                            probe.fps = float(fps_str)
                        except ValueError:
                            pass

                elif stream["codec_type"] == "audio":
                    probe.has_audio = True
                    probe.audio_codec = stream.get("codec_name", "")

            return probe

        except Exception as e:
            logger.exception(f"Probe error for {file_path}: {e}")
            return None

    async def trim(
        self,
        input_path: str,
        output_path: str,
        start: float,
        end: float,
        job_id: str = "",
        codec: str = "copy",
        progress_callback=None,
    ) -> FFmpegResult:
        """快速裁剪片段"""
        duration = end - start
        args = ["-ss", str(start), "-i", input_path, "-to", str(end), "-c", codec, output_path]
        return await self.run(args, job_id, duration, progress_callback)

    async def concat(
        self,
        input_files: list[str],
        output_path: str,
        job_id: str = "",
        codec: str = "libx264",
        crf: int = 23,
        preset: str = "medium",
        progress_callback=None,
    ) -> FFmpegResult:
        """拼接多个视频文件"""
        # 写入concat列表文件
        list_file = output_path + ".txt"
        try:
            with open(list_file, "w", encoding="utf-8") as f:
                for fp in input_files:
                    fp_escaped = fp.replace("\\", "/")
                    f.write(f"file '{fp_escaped}'\n")

            # 计算总时长
            total_dur = 0.0
            for fp in input_files:
                probe = await self.probe(fp)
                if probe:
                    total_dur += probe.duration

            args = [
                "-f", "concat", "-safe", "0", "-i", list_file,
                "-c:v", codec, "-preset", preset, "-crf", str(crf),
                "-c:a", "aac", "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                output_path
            ]
            return await self.run(args, job_id, total_dur, progress_callback)
        finally:
            # 清理临时文件
            try:
                os.remove(list_file)
            except OSError:
                pass

    async def extract_audio(self, input_path: str, output_path: str, job_id: str = "") -> FFmpegResult:
        """提取音频为 WAV"""
        args = ["-i", input_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", output_path]
        return await self.run(args, job_id)

    async def get_thumbnail(self, file_path: str, time_sec: float, output_path: str) -> bool:
        """截取缩略图"""
        args = ["-ss", str(time_sec), "-i", file_path, "-vframes", "1", "-q:v", "2", output_path]
        result = await self.run(args)
        return result.returncode == 0 and os.path.exists(output_path)
