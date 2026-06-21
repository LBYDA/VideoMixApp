import os
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
from ..models.schemas import FileTreeResponse, VideoProbeResponse
from ..core.ffmpeg_executor import FFmpegExecutor
from ..config import get_config

router = APIRouter(prefix="/api/files", tags=["files"])

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".webm", ".m4v", ".mpg", ".mpeg", ".ts"}


def _get_executor() -> FFmpegExecutor:
    cfg = get_config()
    return FFmpegExecutor(
        ffmpeg_path=cfg.ffmpeg_path or "ffmpeg",
        ffprobe_path=cfg.ffprobe_path or "ffprobe",
    )


@router.get("/tree", response_model=list[FileTreeResponse])
async def get_file_tree(path: str = Query(default="")):
    """获取目录树"""
    if not path:
        # 默认返回桌面和文档
        import os.path
        desktop = Path.home() / "Desktop"
        documents = Path.home() / "Documents"
        result = []
        for p in [desktop, documents]:
            if p.exists():
                result.append(FileTreeResponse(
                    path=str(p), name=p.name, is_dir=True
                ))
        return result

    target = Path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="路径不存在")

    result = []
    try:
        items = sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        for item in items:
            if item.name.startswith(".") or item.name.startswith("$"):
                continue
            if item.is_dir() or item.suffix.lower() in VIDEO_EXTENSIONS:
                result.append(FileTreeResponse(
                    path=str(item),
                    name=item.name,
                    is_dir=item.is_dir(),
                    size=item.stat().st_size if item.is_file() else 0,
                ))
    except PermissionError:
        raise HTTPException(status_code=403, detail="没有访问权限")

    return result


@router.get("/probe", response_model=VideoProbeResponse)
async def probe_video(path: str = Query(...)):
    """获取视频元数据"""
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="文件不存在")

    executor = _get_executor()
    probe = await executor.probe(path)
    if probe is None:
        raise HTTPException(status_code=400, detail="无法解析该视频文件")

    return VideoProbeResponse(
        file_path=probe.file_path,
        duration=probe.duration,
        width=probe.width,
        height=probe.height,
        fps=probe.fps,
        video_codec=probe.video_codec,
        audio_codec=probe.audio_codec,
        has_audio=probe.has_audio,
        has_video=probe.has_video,
        file_size=probe.file_size,
    )


@router.get("/scan")
async def scan_videos(path: str = Query(...)):
    """快速扫描文件夹中所有视频文件（递归）"""
    target = Path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="路径不存在")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="不是有效文件夹")

    videos = []
    try:
        for item in target.rglob("*"):
            if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS and not item.name.startswith("."):
                try:
                    stat = item.stat()
                    videos.append({
                        "path": str(item),
                        "name": item.name,
                        "size": stat.st_size,
                        "parent": str(item.parent),
                    })
                except OSError:
                    pass
    except PermissionError:
        raise HTTPException(status_code=403, detail="没有访问权限")

    # 按路径排序
    videos.sort(key=lambda v: v["path"].lower())
    return {"videos": videos, "count": len(videos)}


@router.get("/thumbnail")
async def get_thumbnail(path: str = Query(...), time: float = Query(default=0)):
    """获取视频缩略图"""
    import io
    from fastapi.responses import StreamingResponse

    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="文件不存在")

    executor = _get_executor()
    import tempfile
    tmp = tempfile.mktemp(suffix=".jpg")
    try:
        ok = await executor.get_thumbnail(path, time, tmp)
        if not ok:
            raise HTTPException(status_code=400, detail="无法生成缩略图")
        with open(tmp, "rb") as f:
            data = f.read()
        return StreamingResponse(io.BytesIO(data), media_type="image/jpeg")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
