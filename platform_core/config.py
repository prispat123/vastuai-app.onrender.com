from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env", override=False)

def _streamlit_secret(name: str, default=None):
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception:
        return default

@dataclass(frozen=True)
class AppConfig:
    root_dir: Path
    data_dir: Path
    db_path: Path
    projects_dir: Path
    uploads_dir: Path
    cache_dir: Path
    reports_dir: Path
    exports_dir: Path
    logs_dir: Path
    openai_api_key: str
    openai_model: str
    vision_model: str

def load_config() -> AppConfig:
    raw_data_dir = (
        os.getenv("VASTUAI_DATA_DIR")
        or _streamlit_secret("VASTUAI_DATA_DIR")
        or str(Path.home() / "VastuAI_Data")
    )
    data_dir = Path(raw_data_dir).expanduser()
    if not data_dir.is_absolute():
        data_dir = ROOT_DIR / data_dir
    data_dir = data_dir.resolve()

    folders = {
        "projects_dir": data_dir / "Projects",
        "uploads_dir": data_dir / "Uploads",
        "cache_dir": data_dir / "SharedCache",
        "reports_dir": data_dir / "Reports",
        "exports_dir": data_dir / "Exports",
        "logs_dir": data_dir / "Logs",
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        root_dir=ROOT_DIR,
        data_dir=data_dir,
        db_path=data_dir / "vastuai_platform.db",
        openai_api_key=(
            os.getenv("OPENAI_API_KEY")
            or _streamlit_secret("OPENAI_API_KEY", "")
            or ""
        ),
        openai_model=(
            os.getenv("OPENAI_MODEL")
            or _streamlit_secret("OPENAI_MODEL", "gpt-5")
            or "gpt-5"
        ),
        vision_model=(
            os.getenv("OPENAI_VISION_MODEL")
            or _streamlit_secret("OPENAI_VISION_MODEL", "gpt-4.1-mini")
            or "gpt-4.1-mini"
        ),
        **folders,
    )

CONFIG = load_config()
