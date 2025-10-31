from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class AlertDefinitionStore:
    """Persistence layer for alert definitions stored in JSON."""

    def __init__(self, path: Optional[Path] = None) -> None:
        base_path = Path(__file__).resolve().parent.parent / "data" / "alert_definitions.json"
        self.path = path or base_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"alerts": []}, indent=2))

    def load_alerts(self) -> List[Dict[str, Any]]:
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        alerts = data.get("alerts", [])
        if not isinstance(alerts, list):
            raise ValueError("Alert definition store is corrupted: 'alerts' must be a list")
        return alerts

    def save_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        payload = {"alerts": alerts}
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

    def reload_path(self, path: Path) -> None:
        self.path = path
