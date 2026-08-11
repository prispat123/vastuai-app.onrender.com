from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class JsonKnowledgeSource:
    def __init__(self, root: str | Path | None = None):
        self.root = (
            Path(root)
            if root is not None
            else Path(__file__).resolve().parents[1] / "knowledge"
        )

    def manifest(self) -> dict[str, Any]:
        return json.loads(
            (self.root / "manifest.json").read_text(encoding="utf-8")
        )

    def rules(self) -> list[dict]:
        rows: list[dict] = []
        for path in sorted((self.root / "rules").glob("*.json")):
            rows.extend(
                json.loads(path.read_text(encoding="utf-8")).get(
                    "rules",
                    [],
                )
            )
        return rows

    def recommendations(self) -> list[dict]:
        path = self.root / "recommendations" / "recommendations.json"
        return json.loads(path.read_text(encoding="utf-8")).get(
            "recommendations",
            [],
        )

    def profiles(self) -> dict[str, dict]:
        path = self.root / "profiles" / "profiles.json"
        return json.loads(path.read_text(encoding="utf-8")).get(
            "profiles",
            {},
        )

    def links(self) -> list[dict]:
        path = self.root / "links" / "links.json"
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8")).get(
            "links",
            [],
        )

    def source_hash(self) -> str:
        digest = hashlib.sha256()
        paths = [self.root / "manifest.json"]
        paths.extend(sorted((self.root / "rules").glob("*.json")))
        paths.append(
            self.root / "recommendations" / "recommendations.json"
        )
        paths.append(self.root / "profiles" / "profiles.json")
        links = self.root / "links" / "links.json"
        if links.exists():
            paths.append(links)

        for path in paths:
            digest.update(path.relative_to(self.root).as_posix().encode())
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def bundle(self) -> dict:
        return {
            "manifest": self.manifest(),
            "rules": self.rules(),
            "recommendations": self.recommendations(),
            "profiles": self.profiles(),
            "links": self.links(),
        }
