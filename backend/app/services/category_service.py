import asyncio
import os
import random
from pathlib import Path
from typing import Optional

from ..models.schemas import CategoryMixRequest, CategoryGroup, JobStatus
from ..models.job import JobRecord, get_job_store
from ..core.ffmpeg_executor import FFmpegExecutor, VideoProbe
from ..core.progress import create_tracker, remove_tracker, ProgressTracker
from ..core.tempfile_manager import TempFileManager
from ..config import get_config
from ..api.ws_progress import broadcast_progress

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".webm", ".m4v", ".mpg", ".mpeg", ".ts"}


class CategoryMixService:
    """分类混剪服务"""

    def __init__(self):
        cfg = get_config()
        self.executor = FFmpegExecutor(
            ffmpeg_path=cfg.ffmpeg_path or "ffmpeg",
            ffprobe_path=cfg.ffprobe_path or "ffprobe",
        )
        self.temp = TempFileManager(cfg.workspace_dir)
        self.output_dir = cfg.output_dir

    async def start(self, req: CategoryMixRequest, job_id: str) -> str:
        tracker = create_tracker(job_id, total_steps=3)
        tracker.set_status(JobStatus.SCANNING)

        store = get_job_store()
        groups_summary = ", ".join(g.name for g in req.groups)
        store.put(JobRecord.create(
            job_id=job_id, job_type="category_mix",
            input_summary=f"分类混剪: {len(req.groups)} 组 ({groups_summary})",
        ))

        try:
            # Step 1: 扫描 + 探针
            await self._broadcast(job_id, "progress", tracker.to_dict())
            all_files = await self._scan_groups(req.groups, job_id)
            probes = await self._probe_files(all_files, job_id, tracker)

            if not probes:
                tracker.set_error("没有找到有效的视频文件")
                self._save_job(store, job_id, JobStatus.FAILED, error="没有找到有效的视频文件")
                await self._broadcast(job_id, "error", tracker.to_dict())
                return job_id

            # Step 2: 规划片段（用 -ss -to 直接指定时间范围，不生成临时文件）
            tracker.set_status(JobStatus.PLANNING)
            tracker.set_step(1, "正在规划剪辑片段...")
            await self._broadcast(job_id, "progress", tracker.to_dict())

            clips = self._plan_clips(req, probes, all_files)
            if not clips:
                tracker.set_error("素材不足，无法达到目标时长")
                self._save_job(store, job_id, JobStatus.FAILED, error="素材不足")
                await self._broadcast(job_id, "error", tracker.to_dict())
                return job_id

            # Step 3: 渲染 — 一条命令搞定所有的切和拼
            tracker.set_status(JobStatus.RENDERING)
            tracker.set_step(2, "正在编码输出...")
            await self._broadcast(job_id, "progress", tracker.to_dict())

            output = await self._render_one_pass(clips, req, job_id, tracker)

            if output:
                tracker.set_output(output)
                self._save_job(store, job_id, JobStatus.COMPLETED, output_path=output)
                await self._broadcast(job_id, "completed", tracker.to_dict())
            else:
                tracker.set_error("渲染失败")
                self._save_job(store, job_id, JobStatus.FAILED, error="渲染失败")
                await self._broadcast(job_id, "error", tracker.to_dict())

        except Exception as e:
            error_msg = str(e)
            tracker.set_error(error_msg)
            self._save_job(store, job_id, JobStatus.FAILED, error=error_msg)
            await self._broadcast(job_id, "error", tracker.to_dict())

        finally:
            remove_tracker(job_id)

        return job_id

    async def _scan_groups(self, groups: list[CategoryGroup], job_id: str) -> dict[str, list[str]]:
        all_files: dict[str, list[str]] = {}
        for group in groups:
            files = []
            src = Path(group.source_dir)
            if src.is_dir():
                for item in sorted(src.iterdir()):
                    if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS:
                        files.append(str(item))
            all_files[group.name] = files
            await broadcast_progress(job_id, "log", {
                "level": "info",
                "message": f"分类组 [{group.name}]: 找到 {len(files)} 个视频文件"
            })
        return all_files

    async def _probe_files(self, all_files: dict[str, list[str]], job_id: str, tracker: ProgressTracker) -> list[tuple[str, VideoProbe]]:
        results: list[tuple[str, VideoProbe]] = []
        total = sum(len(v) for v in all_files.values())
        done = 0
        for group_name, files in all_files.items():
            for fp in files:
                probe = await self.executor.probe(fp)
                if probe and probe.duration > 0.5:
                    results.append((group_name, probe))
                done += 1
                tracker.ffmpeg_percent = (done / total) * 100
                await broadcast_progress(job_id, "log", {
                    "level": "info",
                    "message": f"分析: {Path(fp).name} ({probe.duration:.1f}s)" if probe else f"跳过: {Path(fp).name}"
                })
        return results

    def _plan_clips(self, req: CategoryMixRequest, probes: list[tuple[str, VideoProbe]], all_files: dict[str, list[str]]) -> list[tuple[str, float, float]]:
        """规划片段：简单策略 — 均匀切分每个视频"""
        target = req.target_duration
        total_source_dur = sum(p.duration for _, p in probes)
        if total_source_dur == 0:
            return []

        clips = []

        for group_name, probe in probes:
            # 按比例分配该视频需要贡献的时长
            ratio = probe.duration / total_source_dur
            want = target * ratio

            # 从该视频均匀取片段
            clip_dur = 5.0
            num_clips = max(1, int(want / clip_dur))

            step = max(clip_dur + 1, (probe.duration - 1) / num_clips)
            for i in range(num_clips):
                start = i * step
                end = min(start + clip_dur, probe.duration - 0.1)
                if end - start >= 1.0:
                    clips.append((probe.file_path, start, end))

        return clips

    async def _render_one_pass(self, clips: list[tuple[str, float, float]], req: CategoryMixRequest, job_id: str, tracker: ProgressTracker) -> Optional[str]:
        """一条 FFmpeg 命令完成所有裁剪和拼接，零临时文件"""
        output = req.output_path
        os.makedirs(os.path.dirname(output) if os.path.dirname(output) else ".", exist_ok=True)

        # 计算总时长
        total_dur = sum(end - start for _, start, end in clips)

        # 速度参数
        if req.quality == "quality_priority":
            crf, preset = "18", "slow"
        elif req.quality == "speed":
            crf, preset = "28", "fast"
        else:
            crf, preset = "23", "medium"

        codec = req.hw_encoder or "libx264"

        # 构建 filter_complex：每个片段 trim + setpts → concat
        filters = []
        labels = []
        for i, (src, start, end) in enumerate(clips):
            dur = end - start
            labels.append(f"[v{i}]")
            filters.append(f"[{i}:v]trim=start={start}:duration={dur:.2f},setpts=PTS-STARTPTS[v{i}]")

        concat_inputs = "".join(labels)
        filters.append(f"{concat_inputs}concat=n={len(clips)}:v=1:a=0[vout]")
        filter_str = ";".join(filters)

        args = []
        for src, _, _ in clips:
            args.extend(["-i", src])

        args.extend([
            "-filter_complex", filter_str,
            "-map", "[vout]",
            "-c:v", codec,
            "-preset", preset,
            "-crf", crf,
            "-pix_fmt", "yuv420p",
            "-an",  # 无音频，避免音频流问题
            output,
        ])

        await broadcast_progress(job_id, "log", {
            "level": "info",
            "message": f"开始渲染: {len(clips)} 个片段, 总时长 {total_dur:.1f}s"
        })

        async def on_progress(ffprog):
            tracker.on_ffmpeg_progress(ffprog)
            await broadcast_progress(job_id, "progress", tracker.to_dict())

        result = await self.executor.run(args, job_id, total_dur, progress_callback=on_progress)

        if result.returncode == 0 and os.path.exists(output) and os.path.getsize(output) > 0:
            return output
        return None

    def _save_job(self, store, job_id: str, status: JobStatus, output_path: str = "", error: str = ""):
        from datetime import datetime, timezone
        rec = store.get(job_id)
        if rec:
            rec.status = status
            if output_path:
                rec.output_path = output_path
            if error:
                rec.error = error
            if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                rec.completed_at = datetime.now(timezone.utc).isoformat()
            store.put(rec)

    async def _broadcast(self, job_id: str, event: str, data: dict):
        await broadcast_progress(job_id, event, data)


_category_service: Optional[CategoryMixService] = None


def get_category_service() -> CategoryMixService:
    global _category_service
    if _category_service is None:
        _category_service = CategoryMixService()
    return _category_service
