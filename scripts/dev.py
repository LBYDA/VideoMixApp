#!/usr/bin/env python3
"""开发环境启动脚本：同时启动后端和前端的dev server"""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent.parent


def main():
    print("=== 启动视频混剪工具开发环境 ===\n")

    # 1. 启动后端
    print("[1/2] 启动后端 FastAPI 服务...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "51234", "--reload"],
        cwd=str(ROOT / "backend"),
    )

    # 2. 启动前端
    print("[2/2] 启动前端 Vite dev server...")
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm, "run", "dev"],
        cwd=str(ROOT / "frontend"),
    )

    print(f"\n✓ 后端运行在: http://localhost:51234")
    print(f"✓ 前端运行在: http://localhost:5173")
    print("\n按 Ctrl+C 停止所有服务")

    # 打开浏览器
    time.sleep(2)
    webbrowser.open("http://localhost:5173")

    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        print("\n正在关闭...")
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(0)


if __name__ == "__main__":
    main()
