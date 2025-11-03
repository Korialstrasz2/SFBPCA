"""Configuration utilities for the Airflow SFBPCA application."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "sfbpca_config.json"


@dataclass
class AirflowAppConfig:
    """Configuration values used by the Airflow pipeline and helper scripts."""

    airflow_home: Path
    source_dir: Path
    working_dir: Path
    alert_definition_path: Path
    reports_dir: Path
    backup_dir: Path
    data_snapshot_path: Path

    @classmethod
    def load(cls, override_path: str | os.PathLike[str] | None = None) -> "AirflowAppConfig":
        """Load configuration from JSON and expand any user variables."""

        config_path = Path(
            override_path
            or os.environ.get("SFBPCA_CONFIG")
            or DEFAULT_CONFIG_PATH
        ).expanduser().resolve()
        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found at {config_path}. "
                "Create it or set the SFBPCA_CONFIG environment variable."
            )

        with config_path.open("r", encoding="utf-8") as handle:
            raw: Dict[str, Any] = json.load(handle)

        def normalise(path_value: str, *, default: Path) -> Path:
            if not path_value:
                return default
            path = Path(path_value).expanduser()
            if not path.is_absolute():
                path = config_path.parent / path
            return path.resolve()

        airflow_home = normalise(raw.get("airflow_home", ""), default=config_path.parent / "airflow_home")
        working_dir = normalise(raw.get("working_dir", ""), default=config_path.parent / "runtime")
        source_dir = normalise(raw.get("source_dir", ""), default=config_path.parent / "samples")
        reports_dir = normalise(raw.get("reports_dir", ""), default=working_dir / "reports")
        backup_dir = normalise(raw.get("backup_dir", ""), default=working_dir / "backups")
        alert_definition_path = normalise(
            raw.get("alert_definition_path", ""),
            default=config_path.parent.parent.parent / "app" / "data" / "alert_definitions.json",
        )
        data_snapshot_path = normalise(
            raw.get("data_snapshot_path", ""),
            default=working_dir / "data_snapshot.json",
        )

        instance = cls(
            airflow_home=airflow_home,
            source_dir=source_dir,
            working_dir=working_dir,
            alert_definition_path=alert_definition_path,
            reports_dir=reports_dir,
            backup_dir=backup_dir,
            data_snapshot_path=data_snapshot_path,
        )
        instance.ensure_directories()
        return instance

    def ensure_directories(self) -> None:
        """Create the required directories if they do not already exist."""

        self.airflow_home.mkdir(parents=True, exist_ok=True)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def as_dict(self) -> Dict[str, str]:
        return {
            "airflow_home": str(self.airflow_home),
            "source_dir": str(self.source_dir),
            "working_dir": str(self.working_dir),
            "alert_definition_path": str(self.alert_definition_path),
            "reports_dir": str(self.reports_dir),
            "backup_dir": str(self.backup_dir),
            "data_snapshot_path": str(self.data_snapshot_path),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, str]) -> "AirflowAppConfig":
        instance = cls(
            airflow_home=Path(payload["airflow_home"]),
            source_dir=Path(payload["source_dir"]),
            working_dir=Path(payload["working_dir"]),
            alert_definition_path=Path(payload["alert_definition_path"]),
            reports_dir=Path(payload["reports_dir"]),
            backup_dir=Path(payload["backup_dir"]),
            data_snapshot_path=Path(payload["data_snapshot_path"]),
        )
        instance.ensure_directories()
        return instance
