from platform_core.config import CONFIG

def test_data_directories_exist():
    assert CONFIG.data_dir.exists()
    assert CONFIG.projects_dir.exists()
    assert CONFIG.cache_dir.exists()
