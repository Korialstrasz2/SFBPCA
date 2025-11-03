from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

from airflow_app.services.context import AirflowRuntimeContext

logger = logging.getLogger(__name__)


def initialize_environment(context: AirflowRuntimeContext) -> Dict[str, str]:
    """Ensure runtime directories exist and stamp the initialization."""

    context.config.ensure_runtime_environment()
    timestamp = datetime.utcnow().isoformat()
    marker_path = context.config.base_dir / "artifacts" / "LAST_INITIALIZED.txt"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(f"Initialized at {timestamp} UTC\n", encoding="utf-8")
    logger.info("Airflow runtime initialized at %s", marker_path)
    return {
        "initialized_at": timestamp,
        "base_dir": str(context.config.base_dir),
        "dataset_manifest": str(context.config.dataset_manifest),
    }


def load_salesforce_dataset(context: AirflowRuntimeContext) -> Dict[str, Dict[str, int]]:
    """Import CSV extracts defined in the dataset manifest."""

    manifest = context.config.load_dataset_manifest()
    if not manifest:
        logger.warning("Dataset manifest is empty; skipping import")
        return {"imports": {}}

    missing: Dict[str, str] = {}
    for entity, path in manifest.items():
        if not Path(path).exists():
            missing[entity] = path
    if missing:
        raise FileNotFoundError(
            "Missing dataset files: "
            + ", ".join(f"{entity} -> {path}" for entity, path in sorted(missing.items()))
        )

    store = context.load_data_store()
    importer = context.build_importer(store)
    summary = importer.import_from_files(manifest)
    context.save_data_store(store)
    logger.info("Imported dataset with summary: %s", summary)
    return {"imports": summary}


def snapshot_state(context: AirflowRuntimeContext) -> Dict[str, int]:
    """Return a lightweight summary of the stored data for use in reports."""

    store = context.load_data_store()
    summary = {
        "accounts": len(store.accounts),
        "contacts": len(store.contacts),
        "individuals": len(store.individuals),
        "account_contact_relations": len(store.account_contact_relations),
        "contact_point_phones": len(store.contact_point_phones),
        "contact_point_emails": len(store.contact_point_emails),
    }
    logger.info("Data snapshot: %s", summary)
    return summary


__all__ = ["initialize_environment", "load_salesforce_dataset", "snapshot_state"]
