import asyncio
import os
import random
from pathlib import Path
from typing import Optional

from ..models.schemas import CategoryMixRequest, CategoryGroup, JobStatus, JobProgressResponse
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
        """启动分类混剪任务"""
        tracker = create_tracker(job_id, total_steps=4)
        tracker.set_status(JobStatus.SCANNING)

        # 保存任务记录
        store = get_job_store()
        groups_summary = ", ".join(g.name for g in req.groups)
        store.put(JobRecord.create(
            job_id=job_id, job_type="category_mix",
            input_summary=f"分类混剪: {len(req.groups)} 组 ({groups_summary})",
        ))

        try:
            # Step 1: 扫描文件
            await self._broadcast(job_id, "progress", tracker.to_dict())
            all_files = await self._scan_groups(req.groups, job_id)

            # Step 2: ffprobe 探针
            tracker.set_status(JobStatus.PROBING)
            tracker.set_step(1, "正在分析视频信息...")
            await self._broadcast(job_id, "progress", tracker.to_dict())

            probes = await self._probe_files(all_files, job_id, tracker)

            if not probes:
                tracker.set_error("没有找到有效的视频文件")
                self._save_job(store, job_id, JobStatus.FAILED, error="没有找到有效的视频文件")
                await self._broadcast(job_id, "error", tracker.to_dict())
                return job_id

            # Step 3: 规划片段
            tracker.set_status(JobStatus.PLANNING)
            tracker.set_step(2, "正在规划剪辑片段...")
            await self._broadcast(job_id, "progress", tracker.to_dict())

            clips = self._plan_clips(req, probes, all_files)
            if not clips:
                tracker.set_error("素材不足，无法达到目标时长")
                self._save_job(store, job_id, JobStatus.FAILED, error="素材不足")
                await self._broadcast(job_id, "error", tracker.to_dict())
                return job_id

            # Step 4: 渲染
            tracker.set_status(JobStatus.RENDERING)
            tracker.set_step(3, "正在编码输出...")
            await self._broadcast(job_id, "progress", tracker.to_dict())

            output = await self._render(clips, req, job_id, tracker)

            if output:
                tracker.set_output(output)
                self._save_job(store, job_id, JobStatus.COMPLETED, output_path=output)
                await self._broadcast(job_id, "completed", tracker.to_dict())
            else:
                tracker.set_error("渲染失败")
                self._save_job(store, job_id, JobStatus.FAILED, error="渲染失败")
                await self._broadcast(job_id, "error", tracker.to_dict())

        except asyncio.CancelledError:
            tracker.set_status(JobStatus.CANCELLED)
            self._save_job(store, job_id, JobStatus.CANCELLED)
            await self._broadcast(job_id, "progress", tracker.to_dict())

        except Exception as e:
            error_msg = str(e)
            tracker.set_error(error_msg)
            self._save_job(store, job_id, JobStatus.FAILED, error=error_msg)
            await self._broadcast(job_id, "error", tracker.to_dict())

        finally:
            remove_tracker(job_id)

        return job_id

    async def _scan_groups(self, groups: list[CategoryGroup], job_id: str) -> dict[str, list[str]]:
        """扫描每个分类组的视频文件"""
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
        """探针所有视频文件"""
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
                    "message": f"分析: {Path(fp).name} ({probe.duration:.1f}s)" if probe else f"跳过: {Path(fp).name} (无法解析)"
                })

        return results

    def _plan_clips(self, req: CategoryMixRequest, probes: list[tuple[str, VideoProbe]], all_files: dict[str, list[str]]) -> list[tuple[str, float, float]]:
        """规划片段选取"""
        random.seed(42)
        clips: list[tuple[str, float, float]] = []
        total_duration = 0.0

        # 按组组织
        by_group: dict[str, list[tuple[str, VideoProbe]]] = {}
        for group_name, probe in probes:
            by_group.setdefault(group_name, []).append((group_name, probe))

        group_names = list(by_group.keys())
        if not group_names:
            return []

        # 循环从每组选取片段
        used_times: dict[str, set[tuple[float, float]]] = {}
        cycle = 0
        max_cycles = 100

        while total_duration < req.target_duration and cycle < max_cycles:
            group_name = group_names[cycle % len(group_names)]
            group_probes = by_group.get(group_name, [])

            if not group_probes:
                cycle += 1
                continue

            # 随机选取一个视频
            _, probe = random.choice(group_probes)

            if probe.file_path not in used_times:
                used_times[probe.file_path] = set()

            # 找一个未使用的片段
            max_clip = 5.0
            min_clip = 2.0
            for g in req.groups:
                if g.name == group_name:
                    max_clip = g.max_clip_duration
                    min_clip = g.min_clip_duration
                    break

            clip_found = False
            attempts = 0
            while not clip_found and attempts < 20:
                clip_dur = random.uniform(min_clip, max_clip)
                clip_dur = min(clip_dur, req.target_duration - total_duration)
                max_start = max(0, probe.duration - clip_dur)
                start = random.uniform(0, max_start) if max_start > 0 else 0
                end = start + clip_dur

                # 检查是否与已选片段重叠
                overlap = False
                for used_start, used_end in used_times[probe.file_path]:
                    if not (end <= used_start or start >= used_end):
                        overlap = True
                        break

                if not overlap and clip_dur >= 0.5:
                    used_times[probe.file_path].add((start, end))
                    clips.append((probe.file_path, start, end))
                    total_duration += clip_dur
                    clip_found = True

                attempts += 1

            cycle += 1

        return clips

    async def _render(self, clips: list[tuple[str, float, float]], req: CategoryMixRequest, job_id: str, tracker: ProgressTracker) -> Optional[str]:
        """渲染最终视频"""
        if not clips:
            return None

        job_dir = self.temp.create_temp_dir(f"category_mix_{job_id}")
        clip_files = []

        # 逐片段裁剪
        total_clips = len(clips)
        for i, (src, start, end) in enumerate(clips):
            clip_path = os.path.join(job_dir, f"clip_{i:04d}.mp4")
            clip_files.append(clip_path)

            tracker.set_step(3, f"正在裁剪片段 {i+1}/{total_clips}...")
            tracker.set_current_file(os.path.basename(src))

            await broadcast_progress(job_id, "log", {
                "level": "info",
                "message": f"裁剪: {Path(src).name} [{start:.1f}s - {end:.1f}s]"
            })

            result = await self.executor.trim(src, clip_path, start, end, job_id)
            if result.returncode != 0:
                await broadcast_progress(job_id, "log", {
                    "level": "error",
                    "message": f"裁剪失败: {Path(src).name}"
                })

        valid_clips = [f for f in clip_files if os.path.exists(f) and os.path.getsize(f) > 0]
        if not valid_clips:
            return None

        # 拼接
        output = req.output_path
        os.makedirs(os.path.dirname(output) if os.path.dirname(output) else ".", exist_ok=True)

        codec = "libx264"
        crf = 23
        preset = "medium"
        if req.quality == "quality_priority":
            crf = 18
            preset = "slow"
        elif req.quality == "speed":
            crf = 28
            preset = "fast"

        if req.hw_encoder:
            codec = req.hw_encoder

        tracker.set_step(3, "正在拼接输出...")
        await broadcast_progress(job_id, "log", {"level": "info", "message": "开始拼接视频片段..."})

        async def on_progress(ffprog):
            tracker.on_ffmpeg_progress(ffprog)
            await broadcast_progress(job_id, "progress", tracker.to_dict())

        result = await self.executor.concat(
            valid_clips, output, job_id,
            codec=codec, crf=crf, preset=preset,
            progress_callback=on_progress,
        )

        if result.returncode != 0:
            return None

        self.temp.cleanup()
        return output

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

    def get_job_store(self):
        return get_job_store()


# 全局服务实例
_category_service: Optional[CategoryMixService] = None


def get_category_service() -> CategoryMixService:
    global _category_service
    if _category_service is None:
        _category_service = CategoryMixService()
    return _category_service
