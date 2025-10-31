from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional


class AlertDefinitionStore:
    """Simple JSON-backed store for alert definitions."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._definitions: List[Dict] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._definitions = []
            return
        content = self.path.read_text(encoding="utf-8")
        if not content.strip():
            self._definitions = []
            return
        try:
            data = json.loads(content)
            if isinstance(data, list):
                self._definitions = data
            else:
                raise ValueError("Alert definition file must contain a list")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse alert definitions: {exc}") from exc

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self._definitions, handle, indent=2)
            handle.write("\n")

    def list_definitions(self) -> List[Dict]:
        return deepcopy(self._definitions)

    def get_definition(self, definition_id: str) -> Optional[Dict]:
        for definition in self._definitions:
            if definition.get("id") == definition_id:
                return deepcopy(definition)
        return None

    def upsert_definition(self, definition: Dict) -> Dict:
        definition_id = definition.get("id")
        if not definition_id:
            raise ValueError("Definition requires an 'id'")
        for index, existing in enumerate(self._definitions):
            if existing.get("id") == definition_id:
                self._definitions[index] = definition
                self._save()
                return deepcopy(definition)
        self._definitions.append(definition)
        self._save()
        return deepcopy(definition)

    def delete_definition(self, definition_id: str) -> None:
        original_length = len(self._definitions)
        self._definitions = [d for d in self._definitions if d.get("id") != definition_id]
        if len(self._definitions) == original_length:
            raise KeyError(f"Alert definition '{definition_id}' was not found")
        self._save()

    def replace_all(self, definitions: List[Dict]) -> List[Dict]:
        self._definitions = definitions
        self._save()
        return deepcopy(self._definitions)
