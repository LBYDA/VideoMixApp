import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from ..models.schemas import AiMixInput, AiClipPlan, AiMixExecuteRequest, JobCreatedResponse, JobProgressResponse
from ..models.job import get_job_store
from ..services.ai_service import get_ai_service
from ..core.progress import get_tracker

router = APIRouter(prefix="/api/ai-mix", tags=["ai-mix"])


@router.post("/asr")
async def run_asr(input_data: AiMixInput):
    """对视频执行ASR，获取字幕"""
    job_id = str(uuid.uuid4())[:8]
    service = get_ai_service()
    results = await service.run_asr(input_data.video_paths, job_id)
    return {"videos": results}


@router.post("/generate-plan")
async def generate_plan(input_data: AiMixInput):
    """LLM生成混剪方案"""
    job_id = str(uuid.uuid4())[:8]
    service = get_ai_service()

    # 首先获取字幕
    subtitles = await service.run_asr(input_data.video_paths, job_id)

    # 调用LLM生成方案
    plan = await service.generate_plan(input_data, subtitles, job_id)
    if plan is None:
        raise HTTPException(status_code=500, detail="生成混剪方案失败")

    return plan.model_dump()


@router.post("/execute", response_model=JobCreatedResponse)
async def execute_ai_mix(req: AiMixExecuteRequest, background_tasks: BackgroundTasks):
    """执行AI混剪方案"""
    job_id = str(uuid.uuid4())[:8]
    service = get_ai_service()
    background_tasks.add_task(service.execute, req, job_id)
    return JobCreatedResponse(job_id=job_id)


@router.get("/job/{job_id}", response_model=JobProgressResponse)
async def get_job_status(job_id: str):
    """获取AI混剪任务状态"""
    tracker = get_tracker(job_id)
    if tracker:
        data = tracker.to_dict()
        return JobProgressResponse(**data, job_type="ai_mix")

    store = get_job_store()
    rec = store.get(job_id)
    if rec:
        return JobProgressResponse(
            job_id=job_id, job_type="ai_mix",
            status=rec.status, output_path=rec.output_path, error=rec.error,
        )

    raise HTTPException(status_code=404, detail="任务不存在")


@router.post("/job/{job_id}/cancel")
async def cancel_job(job_id: str):
    """取消任务"""
    service = get_ai_service()
    service.executor.cancel(job_id)
    return {"ok": True}
