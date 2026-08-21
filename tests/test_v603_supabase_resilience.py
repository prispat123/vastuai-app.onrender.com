
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_cloud_repository_has_transient_retry():
    text=(ROOT/"platform_core"/"cloud_repository.py").read_text(encoding="utf-8")
    assert "_TRANSIENT_HTTP_ERRORS" in text
    assert "RemoteProtocolError" in text
    assert "def _execute(" in text
    assert "time.sleep" in text

def test_v603_version():
    assert "6.0.3" in (ROOT/"professional_app"/"version.py").read_text(encoding="utf-8")
