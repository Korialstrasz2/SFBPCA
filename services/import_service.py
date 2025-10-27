"""Service responsible for importing Salesforce CSV files."""
from __future__ import annotations

import csv
import io
from typing import Dict, Iterable, List, Tuple

from storage.data_store import DataStore


class ImportService:
    """Import Salesforce data and populate the :class:`DataStore`."""

    REQUIRED_FILES: Tuple[str, ...] = (
        "account",
        "contact",
        "accountContactRelation",
        "individual",
        "contactPointPhone",
        "contactPointEmail",
    )

    def __init__(self, data_store: DataStore) -> None:
        self._data_store = data_store

    def import_data(self, files: Dict[str, Iterable[bytes]]) -> Dict[str, int]:
        """Import the provided CSV files into the data store.

        Parameters
        ----------
        files:
            Mapping of field name to a file-like object that yields bytes.

        Returns
        -------
        dict
            Counts of imported records per object type.

        Raises
        ------
        ValueError
            If any required file is missing or invalid.
        """

        missing = [name for name in self.REQUIRED_FILES if name not in files]
        if missing:
            raise ValueError(f"Missing required files: {', '.join(missing)}")

        self._data_store.reset()

        accounts = self._read_csv(files["account"])
        contacts = self._read_csv(files["contact"])
        relations = self._read_csv(files["accountContactRelation"])
        individuals = self._read_csv(files["individual"])
        phones = self._read_csv(files["contactPointPhone"])
        emails = self._read_csv(files["contactPointEmail"])

        self._data_store.accounts = self._index_by_id(accounts)
        self._data_store.contacts = self._index_by_id(contacts)
        self._data_store.individuals = self._index_by_id(individuals)
        self._data_store.account_contact_relations = relations
        self._data_store.contact_point_phone = phones
        self._data_store.contact_point_email = emails

        return {
            "accounts": len(accounts),
            "contacts": len(contacts),
            "account_contact_relations": len(relations),
            "individuals": len(individuals),
            "contact_point_phone": len(phones),
            "contact_point_email": len(emails),
        }

    @staticmethod
    def _read_csv(file_obj: Iterable[bytes]) -> List[dict]:
        try:
            raw = file_obj.read()
        except AttributeError as exc:  # pragma: no cover - defensive programming
            raise ValueError("Provided file object is not readable") from exc

        if isinstance(raw, bytes):
            text = raw.decode("utf-8-sig")
        else:
            text = raw

        if not text.strip():
            return []

        buffer = io.StringIO(text)
        reader = csv.DictReader(buffer)
        return [dict(row) for row in reader]

    @staticmethod
    def _index_by_id(records: List[dict]) -> Dict[str, dict]:
        indexed: Dict[str, dict] = {}
        for record in records:
            record_id = record.get("Id")
            if not record_id:
                continue
            indexed[record_id] = record
        return indexed


__all__ = ["ImportService"]
