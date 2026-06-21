import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from .schemas import JobStatus


class JobRecord(BaseModel):
    job_id: str
    job_type: str  # "category_mix", "ai_mix", "video_mix"
    status: JobStatus = JobStatus.PENDING
    input_summary: str = ""
    output_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str = ""
    completed_at: Optional[str] = None
    metadata: dict = {}

    @classmethod
    def create(cls, job_id: str, job_type: str, input_summary: str = "", metadata: dict = None) -> "JobRecord":
        return cls(
            job_id=job_id,
            job_type=job_type,
            input_summary=input_summary,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )


class JobStore:
    """任务持久化存储（JSON文件）"""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._file = self.base_dir / "jobs.json"
        self._jobs: dict[str, JobRecord] = {}
        self._load()

    def _load(self):
        if self._file.exists():
            try:
                with open(self._file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    rec = JobRecord(**item)
                    self._jobs[rec.job_id] = rec
            except (json.JSONDecodeError, IOError):
                pass

    def _save(self):
        data = [rec.model_dump() for rec in self._jobs.values()]
        with open(self._file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def put(self, record: JobRecord):
        self._jobs[record.job_id] = record
        self._save()

    def get(self, job_id: str) -> Optional[JobRecord]:
        return self._jobs.get(job_id)

    def list_recent(self, limit: int = 50, status: Optional[str] = None) -> list[JobRecord]:
        records = list(self._jobs.values())
        if status:
            records = [r for r in records if r.status.value == status]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    def delete(self, job_id: str):
        self._jobs.pop(job_id, None)
        self._save()

    def clear_completed(self):
        self._jobs = {k: v for k, v in self._jobs.items() if v.status not in (JobStatus.COMPLETED, JobStatus.CANCELLED)}
        self._save()


# 全局单例
_job_store: Optional[JobStore] = None


def get_job_store() -> JobStore:
    global _job_store
    if _job_store is None:
        from ..config import get_config
        cfg = get_config()
        _job_store = JobStore(os.path.join(cfg.workspace_dir, "job_history"))
    return _job_store
