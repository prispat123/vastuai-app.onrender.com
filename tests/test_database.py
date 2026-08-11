from platform_core.database import initialize_database, connect

def test_database_initialization():
    initialize_database()
    with connect() as connection:
        row = connection.execute(
            "SELECT schema_version FROM schema_meta WHERE id=1"
        ).fetchone()
    assert row["schema_version"] == 3
