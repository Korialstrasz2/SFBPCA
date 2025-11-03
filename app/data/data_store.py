from collections import defaultdict
from typing import Dict, List, Optional


class DataStore:
    """In-memory container for Salesforce data imported from CSV files."""

    def __init__(self) -> None:
        self.reset()

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
            self.account_contact_relations = records
        elif entity == "contact_point_phones":
            self.contact_point_phones = records
        elif entity == "contact_point_emails":
            self.contact_point_emails = records
        else:
            raise ValueError(f"Unknown entity: {entity}")

        self._build_relationships()

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


DATA_STORE = DataStore()
