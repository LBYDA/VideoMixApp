import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from ..models.schemas import CategoryMixRequest, JobCreatedResponse, JobProgressResponse
from ..models.job import get_job_store, JobRecord
from ..services.category_service import get_category_service
from ..core.progress import get_tracker
from .ws_progress import broadcast_progress

router = APIRouter(prefix="/api/category-mix", tags=["category-mix"])


@router.post("/start", response_model=JobCreatedResponse)
async def start_category_mix(req: CategoryMixRequest, background_tasks: BackgroundTasks):
    """开始分类混剪"""
    import uuid
    job_id = str(uuid.uuid4())[:8]

    service = get_category_service()
    background_tasks.add_task(service.start, req, job_id)

    return JobCreatedResponse(job_id=job_id)


@router.get("/job/{job_id}", response_model=JobProgressResponse)
async def get_job_status(job_id: str):
    """获取任务状态"""
    tracker = get_tracker(job_id)
    if tracker:
        data = tracker.to_dict()
        return JobProgressResponse(**data, job_type="category_mix")

    # 尝试从持久化存储获取
    store = get_job_store()
    rec = store.get(job_id)
    if rec:
        return JobProgressResponse(
            job_id=job_id,
            job_type="category_mix",
            status=rec.status,
            output_path=rec.output_path,
            error=rec.error,
        )

    raise HTTPException(status_code=404, detail="任务不存在")


@router.post("/job/{job_id}/cancel")
async def cancel_job(job_id: str):
    """取消任务"""
    from ..services.category_service import get_category_service
    service = get_category_service()
    service.executor.cancel(job_id)
    await broadcast_progress(job_id, "progress", {"job_id": job_id, "status": "cancelled"})
    return {"ok": True}
