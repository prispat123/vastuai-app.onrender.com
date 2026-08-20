from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_v601_cloud_history_switch_exists():
    text=(ROOT/"professional_app"/"services"/"history_service.py").read_text(encoding="utf-8")
    assert "cloud_repository.enabled()" in text
    assert "save_professional_analysis" in text
    assert "list_professional_analyses" in text

def test_v601_cloud_repository_is_defense_in_depth_user_scoped():
    text=(ROOT/"platform_core"/"cloud_repository.py").read_text(encoding="utf-8")
    assert '.eq("user_id", _uid())' in text
    assert '"user_id": _uid()' in text
    assert "legacy_analysis_id" in text

def test_v601_pdp_cloud_persistence():
    text=(ROOT/"professional_app"/"services"/"pdp_service.py").read_text(encoding="utf-8")
    assert "cloud_repository.create_pdp" in text
    assert "cloud_repository.list_pdps" in text

def test_v601_openai_env_does_not_override_host():
    for rel in ["platform_core/config.py","platform_core/openai_service.py"]:
        text=(ROOT/rel).read_text(encoding="utf-8")
        assert 'load_dotenv(ROOT_DIR / ".env", override=False)' in text
