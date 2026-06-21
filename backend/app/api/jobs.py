from fastapi import APIRouter, Query
from ..models.job import get_job_store
from ..models.schemas import JobProgressResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobProgressResponse])
async def list_jobs(status: str = Query(default=None), limit: int = Query(default=50)):
    """获取任务历史列表"""
    store = get_job_store()
    records = store.list_recent(limit=limit, status=status)

    return [
        JobProgressResponse(
            job_id=r.job_id,
            job_type=r.job_type,
            status=r.status,
            output_path=r.output_path,
            error=r.error,
            current_step=r.input_summary,
        )
        for r in records
    ]


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """删除任务记录"""
    store = get_job_store()
    store.delete(job_id)
    return {"ok": True}
