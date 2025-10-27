"""In-memory data store for imported Salesforce records."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DataStore:
    """Holds the imported Salesforce records in-memory."""

    accounts: Dict[str, dict] = field(default_factory=dict)
    contacts: Dict[str, dict] = field(default_factory=dict)
    individuals: Dict[str, dict] = field(default_factory=dict)
    account_contact_relations: List[dict] = field(default_factory=list)
    contact_point_phone: List[dict] = field(default_factory=list)
    contact_point_email: List[dict] = field(default_factory=list)

    def reset(self) -> None:
        """Remove all stored data."""

        self.accounts.clear()
        self.contacts.clear()
        self.individuals.clear()
        self.account_contact_relations.clear()
        self.contact_point_phone.clear()
        self.contact_point_email.clear()


__all__ = ["DataStore"]
