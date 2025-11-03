from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, List

from airflow_app.services.context import AirflowRuntimeContext

logger = logging.getLogger(__name__)


def load_alert_configuration(context: AirflowRuntimeContext) -> Dict[str, List[dict]]:
    engine = context.build_alert_engine(context.load_data_store())
    definitions = engine.get_definitions()
    logger.info("Loaded %d alert definitions", len(definitions))
    return {"alerts": definitions}


def persist_alert_configuration(context: AirflowRuntimeContext, definitions: List[dict]) -> Dict[str, int]:
    engine = context.build_alert_engine(context.load_data_store())
    engine.save_definitions(definitions)
    logger.info("Persisted %d alert definitions", len(definitions))
    return {"alerts_saved": len(definitions)}


def build_and_persist_alerts(context: AirflowRuntimeContext) -> Dict[str, object]:
    store = context.load_data_store()
    engine = context.build_alert_engine(store)
    alerts = engine.build_alerts()
    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "alert_count": len(alerts),
        "alerts": alerts,
    }
    path = context.config.alerts_output_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    context.save_data_store(store)
    logger.info("Generated %d alerts and wrote them to %s", len(alerts), path)
    return payload


__all__ = ["load_alert_configuration", "persist_alert_configuration", "build_and_persist_alerts"]
