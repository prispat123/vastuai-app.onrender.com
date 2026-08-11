from __future__ import annotations

import json

from platform_core.database import initialize_database
from knowledge_engine.importer import import_json_master


if __name__ == "__main__":
    initialize_database()
    result = import_json_master()
    print(json.dumps(result, indent=2))
