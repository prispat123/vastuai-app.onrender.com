from __future__ import annotations
import os
import platform
import sqlite3
import sys
from platform_core.config import CONFIG
from platform_core.openai_service import OPENAI

def diagnostics() -> dict:
    result = {
        "python_version": sys.version.split()[0],
        "operating_system": platform.platform(),
        "data_directory": str(CONFIG.data_dir),
        "database_path": str(CONFIG.db_path),
        "data_directory_writable": os.access(CONFIG.data_dir, os.W_OK),
        "database_exists": CONFIG.db_path.exists(),
        "openai": OPENAI.health(),
    }
    try:
        with sqlite3.connect(CONFIG.db_path) as connection:
            connection.execute("SELECT 1")
        result["database_connection"] = "Ready"
    except Exception as exc:
        result["database_connection"] = f"Error: {exc}"
    return result
