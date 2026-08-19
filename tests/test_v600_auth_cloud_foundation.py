from pathlib import Path

def test_v600_auth_files_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "platform_core" / "auth.py").exists()
    assert (root / "platform_core" / "cloud_repository.py").exists()

def test_v600_requirements_include_supabase():
    root = Path(__file__).resolve().parents[1]
    text = (root / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "supabase" in text

def test_v600_app_has_auth_gate():
    root = Path(__file__).resolve().parents[1]
    text = (root / "app.py").read_text(encoding="utf-8")
    assert "auth.render_login_gate()" in text
    assert "auth.sign_out()" in text

def test_v600_cloud_repository_is_user_scoped():
    root = Path(__file__).resolve().parents[1]
    text = (root / "platform_core" / "cloud_repository.py").read_text(encoding="utf-8")
    assert '.eq("user_id", uid)' in text
    assert '"user_id": uid' in text
