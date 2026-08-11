from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any
from platform_core.config import CONFIG
from platform_core.logging_service import LOGGER

class JsonCache:
    def __init__(self, namespace: str, root: str | Path | None = None):
        base = Path(root) if root is not None else CONFIG.cache_dir
        self.root = base / namespace
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in key)
        return self.root / f"{safe}.json"

    def get(self, key: str, *, max_age_seconds: int | None = None) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        if max_age_seconds is not None and time.time() - path.stat().st_mtime > max_age_seconds:
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            LOGGER.info("Cache hit: %s", path)
            return value
        except Exception:
            LOGGER.exception("Could not read cache file: %s", path)
            return None

    def set(self, key: str, value: Any) -> Path:
        path = self._path(key)
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        LOGGER.info("Cache write: %s", path)
        return path

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def clear(self) -> int:
        count = 0
        for path in self.root.glob("*.json"):
            path.unlink()
            count += 1
        return count

VISION_CACHE = JsonCache("Vision")
ANALYSIS_CACHE = JsonCache("Analysis")
DOCUMENT_CACHE = JsonCache("Documents")
