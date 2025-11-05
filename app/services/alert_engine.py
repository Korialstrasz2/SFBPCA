# alert_engine.py


from __future__ import annotations

from typing import Any, Dict, List

from app.data.data_store import DataStore
from app.services.alert_definition_store import AlertDefinitionStore
from app.services.alert_helpers import AlertHelpers


class AlertEngine:
    def __init__(
        self,
        data_store: DataStore,
        definition_store: AlertDefinitionStore | None = None,
    ) -> None:
        self.data_store = data_store
        self.definition_store = definition_store or AlertDefinitionStore()

    def build_alerts(self) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        definitions = self.definition_store.load_alerts()
        for definition in definitions:
            try:
                run = self._compile_logic(definition)
                result = run(self.data_store, AlertHelpers(), definition)
                if not isinstance(result, list):
                    raise TypeError("Alert logic must return a list of alert dictionaries")
                for entry in result:
                    if not isinstance(entry, dict):
                        raise TypeError("Each alert returned by logic must be a dictionary")
                    alert = dict(entry)
                    label = definition.get("label") or definition.get("id") or "Alert"
                    alert.setdefault("type", label)
                    alert["definition_id"] = definition.get("id")
                    alert["description"] = definition.get("description", "")
                    if "summary" not in alert:
                        alert["summary"] = alert.get("message", "")
                    objects = alert.get("objects")
                    if not isinstance(objects, dict):
                        objects = {}
                    normalised_objects: Dict[str, List[str]] = {}
                    for key, value in objects.items():
                        if value is None:
                            continue
                        if isinstance(value, (list, tuple, set)):
                            items = [str(item) for item in value if item]
                        else:
                            items = [str(value)] if value else []
                        if items:
                            normalised_objects[str(key)] = sorted(dict.fromkeys(items))
                    alert["objects"] = normalised_objects
                    alerts.append(alert)
            except Exception as exc:  # pragma: no cover - surfaced to the UI
                label = definition.get("label") or definition.get("id") or "Unknown alert"
                alerts.append(
                    {
                        "type": f"{label} (error)",
                        "message": f"Alert logic error: {exc}",
                        "definition_id": definition.get("id"),
                        "description": definition.get("description", ""),
                        "summary": f"Alert logic error: {exc}",
                        "objects": {},
                    }
                )
        return alerts

    def get_definitions(self) -> List[Dict[str, Any]]:
        return self.definition_store.load_alerts()

    def save_definitions(self, definitions: List[Dict[str, Any]]) -> None:
        sanitized: List[Dict[str, Any]] = []
        for definition in definitions:
            self._validate_definition(definition)
            sanitized.append(definition)
        self.definition_store.save_alerts(sanitized)

    def _compile_logic(self, definition: Dict[str, Any]):
        logic = definition.get("logic")
        if not logic or not isinstance(logic, str):
            raise ValueError("Alert definition is missing a string 'logic' field")
        namespace: Dict[str, Any] = {}
        exec(logic, namespace)
        run = namespace.get("run")
        if not callable(run):
            raise ValueError("Alert logic must define a callable named 'run'")
        return run

    def _validate_definition(self, definition: Dict[str, Any]) -> None:
        if not isinstance(definition, dict):
            raise TypeError("Each alert definition must be a dictionary")
        if not definition.get("id"):
            raise ValueError("Alert definitions require an 'id' field")
        if not definition.get("label"):
            raise ValueError("Alert definitions require a 'label' field")
        self._compile_logic(definition)
