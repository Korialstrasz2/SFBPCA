# importer.py
import csv
import io
from typing import Dict, List, Optional

from app.data.data_store import DataStore


class CSVImporter:
    """Handles CSV ingestion and normalization for Salesforce entities."""

    ENTITY_FIELDS = {
        "accounts": ["Id", "Name"],
        "contacts": [
            "Id",
            "FirstName",
            "LastName",
            "IndividualId",
            "FiscalCode__c",
            "VATNumber__c",
            "MobilePhone",
            "HomePhone",
            "Email",
        ],
        "individuals": ["Id", "FirstName", "LastName"],
        "account_contact_relations": ["Id", "AccountId", "ContactId", "Roles"],
        "contact_point_phones": ["Id", "ParentId", "TelephoneNumber"],
        "contact_point_emails": ["Id", "ParentId", "EmailAddress", "Type__c"],
    }

    def __init__(self, data_store: DataStore) -> None:
        self.data_store = data_store

    def import_payload(self, payload: Dict[str, Optional[bytes]]) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for entity_key in self.ENTITY_FIELDS:
            file_storage = payload.get(entity_key)
            if not file_storage or not getattr(file_storage, "filename", ""):
                continue
            records = self._parse_csv(file_storage)
            self.data_store.update_records(entity_key, records)
            summary[entity_key] = len(records)
        return summary

    def _parse_csv(self, file_storage) -> List[dict]:
        raw = file_storage.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8-sig")
        else:
            text = raw
        reader = csv.DictReader(io.StringIO(text))
        records: List[dict] = []
        for row in reader:
            normalized = {key.strip(): (value.strip() if isinstance(value, str) else value) for key, value in row.items()}
            records.append(normalized)
        return records
