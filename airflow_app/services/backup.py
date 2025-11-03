from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict
from zipfile import ZipFile, ZIP_DEFLATED

from airflow_app.services.context import AirflowRuntimeContext

logger = logging.getLogger(__name__)


def create_backup_archive(context: AirflowRuntimeContext) -> Dict[str, str]:
    store = context.load_data_store()
    generated_at = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_path = context.config.backup_dir / f"backup_{generated_at}.zip"
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_path = context.config.dataset_manifest
    alerts_path = context.config.alert_definitions_path
    alert_output_path = context.config.alerts_output_path
    report_path = context.config.reports_index_path

    with ZipFile(backup_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("state/data_store.json", json.dumps(store.export_state(), indent=2))
        if manifest_path.exists():
            archive.write(manifest_path, arcname="config/dataset_manifest.yml")
        if alerts_path.exists():
            archive.write(alerts_path, arcname="config/alert_definitions.json")
        if alert_output_path.exists():
            archive.write(alert_output_path, arcname="artifacts/alerts.json")
        if report_path.exists():
            archive.write(report_path, arcname="artifacts/latest_report.json")

    context.save_data_store(store)
    logger.info("Created backup archive at %s", backup_path)
    return {"backup_path": str(backup_path)}


__all__ = ["create_backup_archive"]
