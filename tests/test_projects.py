import tempfile
from pathlib import Path

def test_slugged_folder_contract():
    from platform_core.projects import _slug
    assert _slug("Avinya Enclave Phase 1") == "Avinya-Enclave-Phase-1"
    assert _slug("  ") == "project"
