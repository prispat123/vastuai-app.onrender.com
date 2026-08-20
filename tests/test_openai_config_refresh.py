import os
from pathlib import Path

def test_root_env_is_authoritative():
    source = (
        Path(__file__).parents[1]
        / "platform_core"
        / "config.py"
    ).read_text(encoding="utf-8")
    assert 'load_dotenv(ROOT_DIR / ".env", override=False)' in source

def test_openai_service_refreshes_environment():
    source = (
        Path(__file__).parents[1]
        / "platform_core"
        / "openai_service.py"
    ).read_text(encoding="utf-8")
    assert "def refresh_environment" in source
    assert 'load_dotenv(ROOT_DIR / ".env", override=False)' in source
    assert "CONFIG.openai_api_key" not in source

def test_service_detects_runtime_key(monkeypatch):
    from platform_core.openai_service import OPENAI

    monkeypatch.setenv("OPENAI_API_KEY", "test-runtime-key")
    monkeypatch.setattr(
        OPENAI,
        "refresh_environment",
        lambda: None,
    )
    assert OPENAI.configured is True
