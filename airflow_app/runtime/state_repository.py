from __future__ import annotations

from pathlib import Path

from app.data.data_store import DataStore


class DataStateRepository:
    """Persistence wrapper around :class:`DataStore` for the Airflow runtime."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> DataStore:
        store = DataStore()
        store.import_from_path(self.path)
        return store

    def save(self, store: DataStore) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        store.export_to_path(tmp_path)
        tmp_path.replace(self.path)

    def exists(self) -> bool:
        return self.path.exists()


__all__ = ["DataStateRepository"]
