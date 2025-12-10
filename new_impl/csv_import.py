"""Coordinatore di import dei CSV per la nuova applicazione."""

from __future__ import annotations

import csv
import io
from typing import Dict, Iterable, List, Optional

from werkzeug.datastructures import FileStorage

from .data_store import DATA_STORE, SalesforceRelationshipStore
from .run_log import RUN_LOG


class CSVImportCoordinator:
    """Legge i file CSV caricati e aggiorna l'archivio relazionale."""

    EXPECTED_COLUMNS: Dict[str, Iterable[str]] = {
        "accounts": ("Id", "Name"),
        "contacts": (
            "Id",
            "FirstName",
            "LastName",
            "IndividualId",
            "FiscalCode__c",
            "VATNumber__c",
            "MobilePhone",
            "Phone",
            "Email",
        ),
        "individuals": ("Id", "FirstName", "LastName"),
        "account_contact_relations": ("Id", "AccountId", "ContactId", "Roles"),
        "contact_point_phones": ("Id", "ParentId", "TelephoneNumber"),
        "contact_point_emails": ("Id", "ParentId", "EmailAddress", "Type__c"),
    }

    def __init__(self, store: SalesforceRelationshipStore | None = None) -> None:
        self.store = store or DATA_STORE

    def import_payload(self, payload: Dict[str, Optional[FileStorage]]) -> Dict[str, int]:
        """Analizza i file caricati e popola l'archivio."""

        summary: Dict[str, int] = {}
        for entity, required_columns in self.EXPECTED_COLUMNS.items():
            file_storage = payload.get(entity)
            if not file_storage:
                RUN_LOG.debug("File mancante per entità", entity=entity)
                continue

            RUN_LOG.info("Elaborazione CSV", entity=entity)
            records = self._read_csv(file_storage, required_columns)
            if not records:
                RUN_LOG.warning("Nessun record trovato", entity=entity)
                continue

            self.store.replace_entity(entity, records)
            summary[entity] = len(records)
            RUN_LOG.info("Caricamento completato per entità", entity=entity, count=len(records))
        return summary

    def _read_csv(self, file_storage, required_columns: Iterable[str]) -> List[Dict[str, str]]:
        raw = getattr(file_storage, "read", lambda: file_storage)()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8-sig")
        else:
            text = raw

        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            raise ValueError("Il file CSV non contiene l'intestazione.")

        missing = [column for column in required_columns if column not in reader.fieldnames]
        if missing:
            raise ValueError(f"Colonne mancanti: {', '.join(missing)}")

        rows: List[Dict[str, str]] = []
        for row in reader:
            cleaned = {
                key.strip(): (value.strip() if isinstance(value, str) else value)
                for key, value in row.items()
            }
            rows.append(cleaned)
        return rows


IMPORT_COORDINATOR = CSVImportCoordinator()
