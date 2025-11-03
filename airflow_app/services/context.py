from __future__ import annotations

from dataclasses import dataclass

from app.services.alert_definition_store import AlertDefinitionStore
from app.services.alert_engine import AlertEngine
from app.services.importer import CSVImporter

from airflow_app.config import AirflowAppConfig
from airflow_app.runtime.state_repository import DataStateRepository


@dataclass
class AirflowRuntimeContext:
    """Convenience accessor bundling configuration and state helpers."""

    config: AirflowAppConfig

    def __post_init__(self) -> None:
        self.state_repository = DataStateRepository(self.config.state_path)

    def load_data_store(self):
        return self.state_repository.load()

    def save_data_store(self, store) -> None:
        self.state_repository.save(store)

    def build_importer(self, store) -> CSVImporter:
        return CSVImporter(store)

    def build_alert_engine(self, store) -> AlertEngine:
        definitions = AlertDefinitionStore(self.config.alert_definitions_path)
        return AlertEngine(store, definitions)


__all__ = ["AirflowRuntimeContext"]
