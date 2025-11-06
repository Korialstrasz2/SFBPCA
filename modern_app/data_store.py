"""Data structure and access layer for the modern alert workspace."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence


@dataclass
class AccountContext:
    """Aggregated view over an account and its related records."""

    account_id: str
    account: Dict[str, str]
    relations: List[Dict[str, str]]
    contacts: List[Dict[str, str]]
    contact_index: Dict[str, Dict[str, str]]
    contact_to_individual: Dict[str, Optional[str]]
    individual_to_contacts: Dict[str, List[str]]


class SalesforceRelationshipStore:
    """Stores imported Salesforce data and keeps relationship indexes in sync."""

    ENTITY_KEYS = (
        "accounts",
        "contacts",
        "individuals",
        "account_contact_relations",
        "contact_point_phones",
        "contact_point_emails",
    )

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.accounts: Dict[str, Dict[str, str]] = {}
        self.contacts: Dict[str, Dict[str, str]] = {}
        self.individuals: Dict[str, Dict[str, str]] = {}
        self.account_contact_relations: List[Dict[str, str]] = []
        self.contact_point_phones: List[Dict[str, str]] = []
        self.contact_point_emails: List[Dict[str, str]] = []

        self.account_to_relations: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self.contact_to_individual: Dict[str, Optional[str]] = {}
        self.individual_to_contacts: Dict[str, List[str]] = defaultdict(list)
        self.individual_to_phones: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self.individual_to_emails: Dict[str, List[Dict[str, str]]] = defaultdict(list)

        print("[store] Reset dei dati in memoria")

    # ------------------------------------------------------------------
    # Data ingestion helpers
    # ------------------------------------------------------------------
    def replace_entity(self, entity: str, records: Sequence[Dict[str, str]]) -> None:
        if entity not in self.ENTITY_KEYS:
            raise ValueError(
                f"Unsupported entity '{entity}'. Expected one of {', '.join(self.ENTITY_KEYS)}"
            )

        if entity == "accounts":
            self.accounts = {record.get("Id", ""): record for record in records if record.get("Id")}
        elif entity == "contacts":
            self.contacts = {record.get("Id", ""): record for record in records if record.get("Id")}
        elif entity == "individuals":
            self.individuals = {record.get("Id", ""): record for record in records if record.get("Id")}
        elif entity == "account_contact_relations":
            self.account_contact_relations = list(records)
        elif entity == "contact_point_phones":
            self.contact_point_phones = list(records)
        elif entity == "contact_point_emails":
            self.contact_point_emails = list(records)
        else:  # pragma: no cover - defensive branch
            raise ValueError(f"Unknown entity: {entity}")

        print(f"[import] Caricati {len(records)} record per '{entity}'")
        self._rebuild_indexes()

    def bulk_replace(self, payload: Dict[str, Sequence[Dict[str, str]]]) -> None:
        for entity in self.ENTITY_KEYS:
            records = payload.get(entity)
            if records is not None:
                self.replace_entity(entity, records)

    # ------------------------------------------------------------------
    # Relationship rebuilders
    # ------------------------------------------------------------------
    def _rebuild_indexes(self) -> None:
        self.account_to_relations = defaultdict(list)
        for relation in self.account_contact_relations:
            account_id = relation.get("AccountId")
            contact_id = relation.get("ContactId")
            if account_id and contact_id:
                self.account_to_relations[account_id].append(relation)

        self.contact_to_individual = {}
        self.individual_to_contacts = defaultdict(list)
        for contact_id, contact in self.contacts.items():
            individual_id = contact.get("IndividualId")
            if individual_id:
                self.contact_to_individual[contact_id] = individual_id
                self.individual_to_contacts[individual_id].append(contact_id)
            else:
                self.contact_to_individual[contact_id] = None

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

        print("[store] Ricostruzione degli indici completata")

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------
    def iter_account_ids(self) -> Iterable[str]:
        return self.accounts.keys()

    def get_account(self, account_id: str) -> Optional[Dict[str, str]]:
        return self.accounts.get(account_id)

    def get_contacts_for_account(self, account_id: str) -> List[Dict[str, str]]:
        contacts: List[Dict[str, str]] = []
        for relation in self.account_to_relations.get(account_id, []):
            contact_id = relation.get("ContactId")
            if not contact_id:
                continue
            contact = self.contacts.get(contact_id)
            if not contact:
                continue
            enriched = dict(contact)
            enriched["_relation"] = relation
            contacts.append(enriched)
        return contacts

    def get_individual_for_contact(self, contact_id: str) -> Optional[Dict[str, str]]:
        individual_id = self.contact_to_individual.get(contact_id)
        if not individual_id:
            return None
        return self.individuals.get(individual_id)

    def get_contact_points_for_contact(self, contact_id: str) -> Dict[str, List[Dict[str, str]]]:
        individual_id = self.contact_to_individual.get(contact_id)
        if not individual_id:
            return {"phones": [], "emails": []}
        return {
            "phones": list(self.individual_to_phones.get(individual_id, [])),
            "emails": list(self.individual_to_emails.get(individual_id, [])),
        }

    def describe_account(self, account_id: str) -> AccountContext:
        account = self.accounts.get(account_id, {})
        relations = list(self.account_to_relations.get(account_id, []))
        contacts = self.get_contacts_for_account(account_id)
        contact_index = {contact.get("Id", ""): contact for contact in contacts if contact.get("Id")}
        contact_to_individual = {
            contact_id: self.contact_to_individual.get(contact_id)
            for contact_id in contact_index
        }
        individual_to_contacts = defaultdict(list)
        for contact_id, individual_id in contact_to_individual.items():
            if individual_id:
                individual_to_contacts[individual_id].append(contact_id)

        return AccountContext(
            account_id=account_id,
            account=account,
            relations=relations,
            contacts=contacts,
            contact_index=contact_index,
            contact_to_individual=dict(contact_to_individual),
            individual_to_contacts=dict(individual_to_contacts),
        )

    def resolve_account_name(self, account_id: str) -> str:
        account = self.get_account(account_id) or {}
        return account.get("Name") or account_id

    def resolve_contact_name(self, contact_id: str) -> str:
        contact = self.contacts.get(contact_id) or {}
        first = contact.get("FirstName")
        last = contact.get("LastName")
        if first or last:
            return " ".join(part for part in (first, last) if part).strip()
        return contact.get("Id") or contact_id

    def timestamp(self) -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"


DATA_STORE = SalesforceRelationshipStore()
"""Singleton instance used throughout the modern application."""
