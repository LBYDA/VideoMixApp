import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional


class TempFileManager:
    """临时文件管理器"""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path(tempfile.gettempdir()) / "video-mix-app"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._files: list[str] = []
        self._dirs: list[str] = []

    def create_temp_dir(self, prefix: str = "job_") -> str:
        path = self.base_dir / f"{prefix}_{os.urandom(4).hex()}"
        path.mkdir(parents=True, exist_ok=True)
        self._dirs.append(str(path))
        return str(path)

    def get_temp_path(self, filename: str, parent_dir: Optional[str] = None) -> str:
        if parent_dir:
            p = Path(parent_dir) / filename
        else:
            p = self.base_dir / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        self._files.append(str(p))
        return str(p)

    def cleanup(self):
        """清理所有临时文件和目录"""
        for f in self._files:
            try:
                os.remove(f)
            except OSError:
                pass
        for d in self._dirs:
            try:
                shutil.rmtree(d, ignore_errors=True)
            except OSError:
                pass
        self._files.clear()
        self._dirs.clear()

    def cleanup_old(self, max_age_hours: int = 24):
        """清理超时的临时目录"""
        import time
        now = time.time()
        for item in self.base_dir.iterdir():
            try:
                if now - item.stat().st_mtime > max_age_hours * 3600:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink()
            except OSError:
                pass
