from platform_core.cache import JsonCache
from platform_core.openai_service import OPENAI
from platform_core.storage import StorageService

def test_storage_hash():
    assert StorageService.sha256_bytes(b"vastuai") == "91a2e76f481aa848d46b2755298dd7af008130b04d4709e7c24ca7c6dcd415f1"

def test_cache_roundtrip(tmp_path):
    cache = JsonCache("Test", root=tmp_path)
    cache.set("sample", {"ok": True})
    assert cache.get("sample") == {"ok": True}

def test_openai_health_contract():
    health = OPENAI.health()
    assert "configured" in health
    assert "default_model" in health
    assert "vision_model" in health
