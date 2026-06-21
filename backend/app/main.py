import sys
import os
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import files, category_mix, ai_mix, video_mix, settings, ws_progress, jobs
from .config import get_config
from .models.schemas import HealthResponse

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
    """将前端构建产物复制到 backend 的 static 目录"""
    # PyInstaller 打包时静态文件通过 --add-data 注入
    if getattr(sys, 'frozen', False):
        return

    project_root = Path(__file__).parent.parent.parent  # backend/.. → video-mix-app/
    frontend_dist = project_root / "frontend" / "dist"
    target = Path(__file__).parent / "static"

    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        if not target.exists() or not (target / "index.html").exists():
            import shutil
            print(f"[sync] 同步前端构建文件: {frontend_dist} → {target}")
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(frontend_dist, target)


# 挂载前端静态文件
_copy_frontend_dist_if_needed()
static_dir = Path(__file__).parent / "static"
HAS_STATIC = static_dir.exists() and (static_dir / "index.html").exists()
if HAS_STATIC:
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


def _run_uvicorn(port: int):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


def main():
    """入口：pywebview 原生窗口 > 浏览器回退"""
    port = 51234
    url = f"http://127.0.0.1:{port}"

    # 启动 FastAPI 后台
    t = threading.Thread(target=_run_uvicorn, args=(port,), daemon=True)
    t.start()

    # 尝试 pywebview 原生窗口
    if _try_pywebview(url):
        return

    # 回退：浏览器
    print("[info] pywebview 不可用，打开浏览器...")
    import webbrowser
    time.sleep(1)
    webbrowser.open(url)
    t.join()


def _try_pywebview(url: str) -> bool:
    try:
        import webview

        # 等 FastAPI 就绪
        time.sleep(1.5)

        webview.create_window(
            "视频混剪工具",
            url,
            width=1280,
            height=800,
            min_size=(900, 600),
            resizable=True,
        )
        webview.start()

        os._exit(0)
        return True

    except ImportError:
        return False
    except Exception as e:
        print(f"[warn] pywebview 启动失败: {e}")
        return False


if __name__ == "__main__":
    main()
