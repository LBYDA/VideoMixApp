import sys
import os
import threading
import time
from pathlib import Path

# 确保 backend 目录在 sys.path
_backend_dir = str(Path(__file__).parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import files, category_mix, ai_mix, video_mix, settings, ws_progress, jobs
from app.config import get_config
from app.models.schemas import HealthResponse

app = FastAPI(
    title="VideoMixApp",
    version="0.1.0",
    description="",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router)
app.include_router(category_mix.router)
app.include_router(ai_mix.router)
app.include_router(video_mix.router)
app.include_router(settings.router)
app.include_router(ws_progress.router)
app.include_router(jobs.router)


@app.on_event("startup")
async def startup():
    get_config()


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", version="0.1.0")


def _copy_frontend_dist_if_needed():
    project_root = Path(_backend_dir)
    frontend_dist = project_root / "frontend" / "dist"
    target = Path(__file__).parent / "static"

    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        if not target.exists() or not (target / "index.html").exists():
            import shutil
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(frontend_dist, target)


_copy_frontend_dist_if_needed()
static_dir = Path(__file__).parent / "static"
if static_dir.exists() and (static_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


def _run_uvicorn(port: int):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


def main():
    port = 51234
    url = f"http://127.0.0.1:{port}"

    t = threading.Thread(target=_run_uvicorn, args=(port,), daemon=True)
    t.start()

    import webbrowser
    time.sleep(1)
    webbrowser.open(url)
    t.join()


if __name__ == "__main__":
    main()
