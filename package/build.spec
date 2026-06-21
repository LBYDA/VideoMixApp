# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置"""
from pathlib import Path

block_cipher = None

ROOT = Path("D:/projects/video-mix-app")
BACKEND = ROOT / "backend"
FRONTEND_DIST = ROOT / "frontend" / "dist"

# 检查前端是否已构建
if not (FRONTEND_DIST / "index.html").exists():
    raise FileNotFoundError("frontend not built! Run: cd frontend && npm run build")

# 收集前端静态文件
static_files = []
for item in FRONTEND_DIST.rglob("*"):
    if item.is_file():
        rel = item.relative_to(FRONTEND_DIST)
        target_dir = str(Path("app") / "static" / rel.parent)
        static_files.append((str(item), target_dir))

# 收集 FFmpeg 二进制文件
FFMPEG_DIR = BACKEND / "resources" / "ffmpeg"
if (FFMPEG_DIR / "Windows" / "ffmpeg" / "bin" / "ffmpeg.exe").exists():
    for item in FFMPEG_DIR.rglob("*"):
        if item.is_file():
            rel = item.relative_to(BACKEND)
            target_dir = str(rel.parent)
            static_files.append((str(item), target_dir))
    print(f"[build] FFmpeg binaries included")
else:
    print("[build] WARNING: FFmpeg binaries not found - app will need system FFmpeg")

a = Analysis(
    [str(BACKEND / "app" / "main.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=static_files,
    hiddenimports=[
        'uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.protocols',
        'fastapi', 'pydantic', 'pydantic_settings',
        'aiofiles', 'httpx',
        'encodings.idna',
        'webview', 'clr_loader', 'bottle', 'proxy_tools',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'pandas', 'scipy',
        'PIL', 'IPython', 'jupyter', 'notebook',
        'numpy', 'cv2', 'onnxruntime',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VideoMixApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(FRONTEND_DIST / "favicon.ico"),
)

print(f"\n[build] frontend files: {len(static_files)}")
print(f"[build] output: dist/VideoMixApp.exe")
