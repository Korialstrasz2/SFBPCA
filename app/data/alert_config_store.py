from __future__ import annotations

import json

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

DEFAULT_CONFIG_PATH = Path(__file__).resolve().with_name("default_alert_configs.json")
USER_CONFIG_PATH = Path(__file__).resolve().with_name("alert_configs.json")


class AlertConfigStore:
    """Persist and retrieve alert configuration definitions."""

    def __init__(self, file_path: Optional[Path] = None) -> None:
        self.file_path = Path(file_path) if file_path else USER_CONFIG_PATH
        self._configs: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.file_path.exists():
            with self.file_path.open("r", encoding="utf-8") as handle:
                self._configs = json.load(handle)
        elif DEFAULT_CONFIG_PATH.exists():
            with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as handle:
                self._configs = json.load(handle)
            self._save()
        else:
            self._configs = []

    def _save(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", encoding="utf-8") as handle:
            json.dump(self._configs, handle, indent=2, ensure_ascii=False)

    def list_configs(self) -> List[Dict[str, Any]]:
        return deepcopy(self._configs)

    def get_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        for config in self._configs:
            if config.get("id") == config_id:
                return deepcopy(config)
        return None

    def add_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        config = self._build_config(payload, is_new=True)
        self._configs.append(config)
        self._save()
        return deepcopy(config)

    def update_config(self, config_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        for index, existing in enumerate(self._configs):
            if existing.get("id") == config_id:
                updated = self._build_config({**existing, **payload}, is_new=False)
                self._configs[index] = updated
                self._save()
                return deepcopy(updated)
        raise KeyError(f"Unknown alert configuration: {config_id}")

    def delete_config(self, config_id: str) -> None:
        initial_count = len(self._configs)
        self._configs = [config for config in self._configs if config.get("id") != config_id]
        if len(self._configs) == initial_count:
            raise KeyError(f"Unknown alert configuration: {config_id}")
        self._save()

    def _build_config(self, payload: Dict[str, Any], *, is_new: bool) -> Dict[str, Any]:
        logic_id = payload.get("logic_id")
        if not logic_id:
            raise ValueError("logic_id is required for an alert configuration")

        config_id = payload.get("id")
        if is_new or not config_id:
            config_id = uuid4().hex

        name = (payload.get("name") or "").strip() or logic_id.replace("_", " ").title()
        description = (payload.get("description") or "").strip()

        type_template = payload.get("type_template")
        if isinstance(type_template, str):
            type_template = type_template.strip() or None

        message_template = payload.get("message_template")
        if isinstance(message_template, str):
            message_template = message_template.strip() or None

        enabled = payload.get("enabled")
        if isinstance(enabled, str):
            enabled = enabled.lower() not in {"", "false", "0", "no"}
        elif enabled is None:
            enabled = True
        else:
            enabled = bool(enabled)

        parameters = payload.get("parameters") or {}
        if not isinstance(parameters, dict):
            raise ValueError("parameters must be an object if provided")

        config: Dict[str, Any] = {
            "id": config_id,
            "name": name,
            "description": description,
            "logic_id": logic_id,
            "enabled": enabled,
            "type_template": type_template,
            "message_template": message_template,
            "parameters": parameters,
        }
        return config


CONFIG_STORE = AlertConfigStore()
