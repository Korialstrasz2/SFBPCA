from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional


class DataStore:
    """In-memory container for Salesforce data imported from CSV files.

    The implementation remains lightweight so it can be reused by the legacy
    Flask application and the Airflow orchestration runtime. In addition to the
    relationship builders used by the original application, the store now
    exposes helpers for serialization and targeted lookups that power the
    orchestration, reporting, and data-change planning workflows.
    """

    def __init__(self) -> None:
        self.reset()

    # ------------------------------------------------------------------
    # Core lifecycle helpers
    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.accounts: Dict[str, dict] = {}
        self.contacts: Dict[str, dict] = {}
        self.individuals: Dict[str, dict] = {}
        self.account_contact_relations: List[dict] = []
        self.contact_point_phones: List[dict] = []
        self.contact_point_emails: List[dict] = []

        self.account_to_contact_relations: Dict[str, List[dict]] = defaultdict(list)
        self.contact_to_individual_id: Dict[str, str] = {}
        self.individual_to_contact_ids: Dict[str, List[str]] = defaultdict(list)
        self.individual_to_phones: Dict[str, List[dict]] = defaultdict(list)
        self.individual_to_emails: Dict[str, List[dict]] = defaultdict(list)

    def update_records(self, entity: str, records: List[dict]) -> None:
        if entity == "accounts":
            self.accounts = {record.get("Id"): record for record in records if record.get("Id")}
        elif entity == "contacts":
            self.contacts = {record.get("Id"): record for record in records if record.get("Id")}
        elif entity == "individuals":
            self.individuals = {record.get("Id"): record for record in records if record.get("Id")}
        elif entity == "account_contact_relations":
            self.account_contact_relations = list(records)
        elif entity == "contact_point_phones":
            self.contact_point_phones = list(records)
        elif entity == "contact_point_emails":
            self.contact_point_emails = list(records)
        else:
            raise ValueError(f"Unknown entity: {entity}")

        self._build_relationships()

    def bulk_update(self, payload: Dict[str, Iterable[dict]]) -> None:
        for entity, records in payload.items():
            self.update_records(entity, list(records))

    def _build_relationships(self) -> None:
        self.account_to_contact_relations = defaultdict(list)
        for relation in self.account_contact_relations:
            account_id = relation.get("AccountId")
            contact_id = relation.get("ContactId")
            if account_id and contact_id:
                self.account_to_contact_relations[account_id].append(relation)

        self.contact_to_individual_id = {}
        self.individual_to_contact_ids = defaultdict(list)
        for contact_id, contact in self.contacts.items():
            individual_id = contact.get("IndividualId")
            if individual_id:
                self.contact_to_individual_id[contact_id] = individual_id
                self.individual_to_contact_ids[individual_id].append(contact_id)

        self.individual_to_phones = defaultdict(list)
        for phone in self.contact_point_phones:
            parent_id = phone.get("ParentId")
            if parent_id:
                self.individual_to_phones[parent_id].append(phone)

        self.individual_to_emails = defaultdict(list)
        for email in self.contact_point_emails:
            parent_id = email.get("ParentId")
            if parent_id:
                self.individual_to_emails[parent_id].append(email)

    # ------------------------------------------------------------------
    # Lookups used by alerts and reporting
    # ------------------------------------------------------------------
    def get_contacts_for_account(self, account_id: str) -> List[dict]:
        relations = self.account_to_contact_relations.get(account_id, [])
        contacts: List[dict] = []
        for relation in relations:
            contact_id = relation.get("ContactId")
            if not contact_id:
                continue
            contact = self.contacts.get(contact_id, {}).copy()
            contact["_relation"] = relation
            contacts.append(contact)
        return contacts

    def get_individual_for_contact(self, contact_id: str) -> Optional[dict]:
        individual_id = self.contact_to_individual_id.get(contact_id)
        if not individual_id:
            return None
        return self.individuals.get(individual_id)

    def get_phones_for_contact(self, contact_id: str) -> List[dict]:
        individual_id = self.contact_to_individual_id.get(contact_id)
        if not individual_id:
            return []
        return list(self.individual_to_phones.get(individual_id, []))

    def get_emails_for_contact(self, contact_id: str) -> List[dict]:
        individual_id = self.contact_to_individual_id.get(contact_id)
        if not individual_id:
            return []
        return list(self.individual_to_emails.get(individual_id, []))

    def get_contacts_with_role(self, role: str) -> List[dict]:
        normalized = (role or "").strip().lower()
        results: List[dict] = []
        for relation in self.account_contact_relations:
            roles = relation.get("Roles") or ""
            role_tokens = [token.strip().lower() for token in roles.split(";") if token.strip()]
            if normalized in role_tokens:
                contact_id = relation.get("ContactId")
                if not contact_id:
                    continue
                contact = self.contacts.get(contact_id, {}).copy()
                contact["_relation"] = relation
                results.append(contact)
        return results

    def find_accounts_with_customer_marking(self, value: str) -> List[dict]:
        normalized = (value or "").strip().lower()
        return [
            account
            for account in self.accounts.values()
            if (account.get("CustomerMarking__c") or "").strip().lower() == normalized
        ]

    def find_matching_accounts_for_contact(self, contact: dict, *, required_marking: str) -> List[dict]:
        first_name = (contact.get("FirstName") or "").strip().lower()
        last_name = (contact.get("LastName") or "").strip().lower()
        candidates: List[dict] = []
        for account in self.accounts.values():
            if (account.get("CustomerMarking__c") or "").strip().lower() != required_marking.strip().lower():
                continue
            account_contacts = self.get_contacts_for_account(account.get("Id", ""))
            for account_contact in account_contacts:
                if (
                    (account_contact.get("FirstName") or "").strip().lower() == first_name
                    and (account_contact.get("LastName") or "").strip().lower() == last_name
                ):
                    candidates.append(account)
                    break
        return candidates

    # ------------------------------------------------------------------
    # Serialization helpers used by the Airflow runtime
    # ------------------------------------------------------------------
    def export_state(self) -> dict:
        return {
            "accounts": list(self.accounts.values()),
            "contacts": list(self.contacts.values()),
            "individuals": list(self.individuals.values()),
            "account_contact_relations": list(self.account_contact_relations),
            "contact_point_phones": list(self.contact_point_phones),
            "contact_point_emails": list(self.contact_point_emails),
        }

    def import_state(self, state: dict) -> None:
        self.reset()
        for entity, records in state.items():
            if isinstance(records, list):
                self.update_records(entity, list(records))

    def export_to_path(self, path: Path) -> None:
        payload = self.export_state()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

    def import_from_path(self, path: Path) -> None:
        if not path.exists():
            self.reset()
            return
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError("Serialized data store must be a JSON object")
        self.import_state(payload)


DATA_STORE = DataStore()
