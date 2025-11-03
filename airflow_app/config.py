from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class AirflowAppConfig:
    """Runtime configuration for the Airflow-based orchestration layer."""

    base_dir: Path
    dataset_manifest: Path
    uploads_dir: Path
    reports_dir: Path
    backup_dir: Path
    state_path: Path
    alert_definitions_path: Path
    alerts_output_path: Path
    reports_index_path: Path
    schedule_interval: str = "@daily"
    dag_id: str = "salesforce_relationship_inspector"

    @classmethod
    def load(cls) -> "AirflowAppConfig":
        """Load configuration from environment variables, falling back to defaults."""

        base_dir = Path(os.environ.get("AIRFLOW_APP_HOME", Path.cwd() / "airflow_runtime")).resolve()
        dataset_manifest = Path(
            os.environ.get("AIRFLOW_APP_DATASET_MANIFEST", base_dir / "config" / "dataset_manifest.yml")
        ).resolve()
        uploads_dir = Path(os.environ.get("AIRFLOW_APP_UPLOADS", base_dir / "uploads")).resolve()
        reports_dir = Path(os.environ.get("AIRFLOW_APP_REPORTS", base_dir / "reports")).resolve()
        backup_dir = Path(os.environ.get("AIRFLOW_APP_BACKUPS", base_dir / "backups")).resolve()
        state_path = Path(os.environ.get("AIRFLOW_APP_STATE", base_dir / "state" / "data_store.json")).resolve()
        alert_definitions_path = Path(
            os.environ.get("AIRFLOW_APP_ALERT_DEFINITIONS", base_dir / "config" / "alert_definitions.json")
        ).resolve()
        alerts_output_path = Path(
            os.environ.get("AIRFLOW_APP_ALERT_OUTPUT", base_dir / "artifacts" / "alerts.json")
        ).resolve()
        reports_index_path = Path(
            os.environ.get("AIRFLOW_APP_REPORT_INDEX", base_dir / "artifacts" / "latest_report.json")
        ).resolve()
        schedule_interval = os.environ.get("AIRFLOW_APP_SCHEDULE", "@daily")

        config = cls(
            base_dir=base_dir,
            dataset_manifest=dataset_manifest,
            uploads_dir=uploads_dir,
            reports_dir=reports_dir,
            backup_dir=backup_dir,
            state_path=state_path,
            alert_definitions_path=alert_definitions_path,
            alerts_output_path=alerts_output_path,
            reports_index_path=reports_index_path,
            schedule_interval=schedule_interval,
        )
        config.ensure_runtime_environment()
        return config

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def ensure_runtime_environment(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for path in [
            self.dataset_manifest.parent,
            self.uploads_dir,
            self.reports_dir,
            self.backup_dir,
            self.state_path.parent,
            self.alert_definitions_path.parent,
            self.alerts_output_path.parent,
            self.reports_index_path.parent,
        ]:
            path.mkdir(parents=True, exist_ok=True)

        template_manifest = Path(__file__).resolve().parent / "config" / "dataset_manifest.yml"
        if not self.dataset_manifest.exists() and template_manifest.exists():
            self.dataset_manifest.write_text(template_manifest.read_text(), encoding="utf-8")

        default_alerts = Path(__file__).resolve().parent.parent / "app" / "data" / "alert_definitions.json"
        if not self.alert_definitions_path.exists() and default_alerts.exists():
            self.alert_definitions_path.write_text(default_alerts.read_text(encoding="utf-8"), encoding="utf-8")

    def load_dataset_manifest(self) -> Dict[str, str]:
        if not self.dataset_manifest.exists():
            return {}
        with self.dataset_manifest.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError("Dataset manifest must be a mapping of entity keys to CSV paths")
        normalized: Dict[str, str] = {}
        for key, value in data.items():
            if not value:
                continue
            path = Path(value)
            if not path.is_absolute():
                path = (self.uploads_dir / path).resolve()
            normalized[key] = str(path)
        return normalized

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_dir": str(self.base_dir),
            "dataset_manifest": str(self.dataset_manifest),
            "uploads_dir": str(self.uploads_dir),
            "reports_dir": str(self.reports_dir),
            "backup_dir": str(self.backup_dir),
            "state_path": str(self.state_path),
            "alert_definitions_path": str(self.alert_definitions_path),
            "alerts_output_path": str(self.alerts_output_path),
            "reports_index_path": str(self.reports_index_path),
            "schedule_interval": self.schedule_interval,
            "dag_id": self.dag_id,
        }


__all__ = ["AirflowAppConfig"]
