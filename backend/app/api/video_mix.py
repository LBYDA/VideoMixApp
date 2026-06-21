import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from ..models.schemas import VideoMixRequest, JobCreatedResponse, JobProgressResponse
from ..models.job import get_job_store
from ..core.progress import get_tracker
from ..api.ws_progress import broadcast_progress

router = APIRouter(prefix="/api/video-mix", tags=["video-mix"])


@router.post("/preview-graph")
async def preview_filter_graph(req: VideoMixRequest):
    """预览 FFmpeg filter_complex 命令"""
    from ..services.filter_graph import build_filter_complex

    filter_str = build_filter_complex(req)

    # 构建完整命令预览
    input_args = " ".join(f'-i "{t.file_path}"' for t in req.tracks)
    settings = req.output_settings

    cmd_parts = [
        "ffmpeg",
        input_args,
        filter_str,
        f'-c:v {settings.video_codec}',
        f'-c:a {settings.audio_codec}',
        f'-preset {settings.preset}',
        f'-crf {settings.crf}',
        f'-pix_fmt yuv420p',
        f'"{req.output_path}"',
    ]

    return {
        "filter_complex": filter_str,
        "command": " \\\n  ".join(cmd_parts),
    }


@router.post("/render", response_model=JobCreatedResponse)
async def render_video_mix(req: VideoMixRequest, background_tasks: BackgroundTasks):
    """开始视频混剪渲染"""
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_do_render, req, job_id)
    return JobCreatedResponse(job_id=job_id)


async def _do_render(req: VideoMixRequest, job_id: str):
    """执行视频混剪渲染"""
    from ..core.ffmpeg_executor import FFmpegExecutor
    from ..core.progress import create_tracker, remove_tracker
    from ..core.tempfile_manager import TempFileManager
    from ..config import get_config
    from ..services.filter_graph import build_filter_complex
    from ..models.schemas import JobStatus
    from ..models.job import JobRecord
    from datetime import datetime, timezone
    import os

    cfg = get_config()
    executor = FFmpegExecutor(
        ffmpeg_path=cfg.ffmpeg_path or "ffmpeg",
        ffprobe_path=cfg.ffprobe_path or "ffprobe",
    )

    tracker = create_tracker(job_id, total_steps=1)
    store = get_job_store()

    store.put(JobRecord.create(
        job_id=job_id, job_type="video_mix",
        input_summary=f"视频混剪: {len(req.tracks)} 个轨道",
    ))

    try:
        tracker.set_status(JobStatus.RENDERING)
        tracker.set_step(0, "正在渲染...")
        await broadcast_progress(job_id, "progress", tracker.to_dict())

        filter_str = build_filter_complex(req)
        settings = req.output_settings

        os.makedirs(os.path.dirname(req.output_path) if os.path.dirname(req.output_path) else ".", exist_ok=True)

        # 构建FFmpeg命令
        args = []
        for t in req.tracks:
            args.extend(["-i", t.file_path])

        # 解析 filter_complex
        if filter_str:
            parts = filter_str.split()
            for part in parts:
                args.append(part)

        args.extend([
            "-c:v", settings.video_codec,
            "-c:a", settings.audio_codec,
            "-preset", settings.preset,
            "-crf", str(settings.crf),
            "-pix_fmt", "yuv420p",
            req.output_path,
        ])

        # 计算总时长
        total_dur = 0.0
        for t in req.tracks:
            probe = await executor.probe(t.file_path)
            if probe:
                dur = (t.end or probe.duration) - (t.start or 0)
                if dur > total_dur:
                    total_dur = dur

        async def on_progress(ffprog):
            tracker.on_ffmpeg_progress(ffprog)
            await broadcast_progress(job_id, "progress", tracker.to_dict())

        result = await executor.run(args, job_id, total_dur, progress_callback=on_progress)

        if result.returncode == 0:
            tracker.set_output(req.output_path)
            rec = store.get(job_id)
            if rec:
                rec.status = JobStatus.COMPLETED
                rec.output_path = req.output_path
                rec.completed_at = datetime.now(timezone.utc).isoformat()
                store.put(rec)
            await broadcast_progress(job_id, "completed", tracker.to_dict())
        else:
            error = result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
            tracker.set_error(f"渲染失败: {error}")
            rec = store.get(job_id)
            if rec:
                rec.status = JobStatus.FAILED
                rec.error = error
                rec.completed_at = datetime.now(timezone.utc).isoformat()
                store.put(rec)
            await broadcast_progress(job_id, "error", tracker.to_dict())

    except Exception as e:
        tracker.set_error(str(e))
        await broadcast_progress(job_id, "error", tracker.to_dict())

    finally:
        remove_tracker(job_id)


@router.get("/job/{job_id}", response_model=JobProgressResponse)
async def get_job_status(job_id: str):
    """获取视频混剪任务状态"""
    tracker = get_tracker(job_id)
    if tracker:
        data = tracker.to_dict()
        return JobProgressResponse(**data, job_type="video_mix")

    store = get_job_store()
    rec = store.get(job_id)
    if rec:
        return JobProgressResponse(
            job_id=job_id, job_type="video_mix",
            status=rec.status, output_path=rec.output_path, error=rec.error,
        )

    raise HTTPException(status_code=404, detail="任务不存在")


@router.post("/job/{job_id}/cancel")
async def cancel_job(job_id: str):
    """取消渲染任务"""
    from ..config import get_config
    from ..core.ffmpeg_executor import FFmpegExecutor
    cfg = get_config()
    executor = FFmpegExecutor(
        ffmpeg_path=cfg.ffmpeg_path or "ffmpeg",
        ffprobe_path=cfg.ffprobe_path or "ffprobe",
    )
    executor.cancel(job_id)
    return {"ok": True}
