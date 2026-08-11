from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path
from platform_core.logging_service import LOGGER

class StorageService:
    def ensure_project_structure(self, project_folder: str | Path) -> dict[str, Path]:
        root = Path(project_folder)
        paths = {
            "root": root,
            "uploads": root / "uploads",
            "layouts": root / "layouts",
            "analysis": root / "analysis",
            "reports": root / "reports",
            "exports": root / "exports",
        }
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
        return paths

    def save_bytes(self, destination: str | Path, data: bytes, *, overwrite: bool = False) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {destination}")
        destination.write_bytes(data)
        LOGGER.info("Saved file: %s", destination)
        return destination

    def save_uploaded_file(self, project_folder: str | Path, uploaded_file, *, subfolder: str = "uploads") -> Path:
        paths = self.ensure_project_structure(project_folder)
        destination = paths[subfolder] / Path(uploaded_file.name).name
        return self.save_bytes(destination, uploaded_file.getvalue(), overwrite=True)

    def write_json(self, destination: str | Path, payload, *, overwrite: bool = True) -> Path:
        data = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
        return self.save_bytes(destination, data.encode("utf-8"), overwrite=overwrite)

    def read_json(self, source: str | Path):
        return json.loads(Path(source).read_text(encoding="utf-8"))

    def copy_file(self, source: str | Path, destination: str | Path, *, overwrite: bool = False) -> Path:
        source = Path(source)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {destination}")
        shutil.copy2(source, destination)
        LOGGER.info("Copied file: %s -> %s", source, destination)
        return destination

    @staticmethod
    def sha256_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def sha256_file(path: str | Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

STORAGE = StorageService()
