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

    def build_alerts(self) -> List[Dict[str, str]]:
        alerts: List[Dict[str, str]] = []
        definitions = self.definition_store.load_alerts()
        for definition in definitions:
            try:
                run = self._compile_logic(definition)
                result = run(self.data_store, AlertHelpers(), definition)
                if not isinstance(result, list):
                    raise TypeError("Alert logic must return a list of alert dictionaries")
                alerts.extend(result)
            except Exception as exc:  # pragma: no cover - surfaced to the UI
                label = definition.get("label") or definition.get("id") or "Unknown alert"
                alerts.append(
                    {
                        "type": f"{label} (error)",
                        "message": f"Alert logic error: {exc}",
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
