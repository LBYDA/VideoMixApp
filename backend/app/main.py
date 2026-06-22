import sys
import os
import threading
import time
from pathlib import Path
from typing import Optional

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


def _get_static_dir() -> Optional[Path]:
    """获取静态文件目录，优先 PyInstaller 打包路径"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包模式
        pkgs = [
            Path(sys._MEIPASS) / "app" / "static",
            Path(sys._MEIPASS) / "static",
        ]
        for p in pkgs:
            if p.exists() and (p / "index.html").exists():
                return p

    # 开发模式
    dev_static = Path(__file__).parent / "static"
    if dev_static.exists() and (dev_static / "index.html").exists():
        return dev_static

    # 开发模式：从 frontend/dist 同步
    project_root = Path(_backend_dir)
    frontend_dist = project_root / "frontend" / "dist"
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        import shutil
        shutil.rmtree(dev_static, ignore_errors=True)
        shutil.copytree(frontend_dist, dev_static)
        if (dev_static / "index.html").exists():
            return dev_static

    return None

static_dir = _get_static_dir()
if static_dir:
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


def _run_uvicorn(port: int):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


def main():
    port = 51234

    t = threading.Thread(target=_run_uvicorn, args=(port,), daemon=True)
    t.start()

    # 等待端口就绪
    import socket
    for _ in range(30):
        time.sleep(0.5)
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=1)
            s.close()
            break
        except (ConnectionRefusedError, OSError):
            pass

    # 优先 pywebview 原生窗口，回退浏览器
    url = f"http://127.0.0.1:{port}"
    try:
        import webview
        webview.create_window("视频混剪工具", url, width=1280, height=800, min_size=(900, 600))
        webview.start()
        os._exit(0)
    except Exception:
        pass

    import webbrowser
    webbrowser.open(url)
    t.join()


if __name__ == "__main__":
    main()
