import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def test_pwa_manifest_and_assets_exist():
    manifest_path = ROOT / 'static' / 'manifest.webmanifest'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert manifest['name'] == 'VastuAI'
    assert manifest['short_name'] == 'VastuAI'
    assert manifest['display'] == 'standalone'
    assert manifest['start_url'] == '/'
    assert manifest['scope'] == '/'
    assert manifest['theme_color'] == '#78B58F'
    assert len(manifest['icons']) >= 2
    for size in (192, 512):
        path = ROOT / 'static' / f'vastuai-{size}.png'
        assert path.exists()
        with Image.open(path) as image:
            assert image.size == (size, size)


def test_streamlit_static_serving_enabled_and_bootstrap_wired():
    cfg = (ROOT / '.streamlit' / 'config.toml').read_text(encoding='utf-8')
    app = (ROOT / 'app.py').read_text(encoding='utf-8')
    support = (ROOT / 'pwa_support.py').read_text(encoding='utf-8')
    assert 'enableStaticServing = true' in cfg
    assert 'install_pwa_metadata()' in app
    assert '/app/static/manifest.webmanifest' in support
    assert 'theme-color' in support
    assert 'serviceWorker' in support
