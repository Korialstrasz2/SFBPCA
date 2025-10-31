from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from app.data.data_store import DataStore
from app.services.alert_definition_store import AlertDefinitionStore


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


class AlertEngine:
    def __init__(self, data_store: DataStore, definition_store: AlertDefinitionStore) -> None:
        self.data_store = data_store
        self.definition_store = definition_store
        self._handlers = {
            "duplicate_role_same_name": self._duplicate_role_same_name_alert,
            "missing_role": self._missing_role_alert,
            "same_name_different_role": self._same_name_different_role_alert,
            "duplicate_contact_point": self._duplicate_contact_points_alert,
        }

    def build_alerts(self) -> List[Dict[str, str]]:
        alerts: List[Dict[str, str]] = []
        for definition in self.definition_store.list_definitions():
            if not definition.get("enabled", True):
                continue
            logic = definition.get("logic", {})
            handler = self._handlers.get(logic.get("type"))
            if not handler:
                continue
            alerts.extend(handler(definition))
        return alerts

    def definition_blueprints(self) -> Dict[str, Dict]:
        return {
            "duplicate_role_same_name": {
                "label": "Duplicate role for contact name",
                "description": "Flags accounts with multiple contacts that share both name and role.",
                "parameters": {
                    "min_count": {
                        "label": "Minimum matching contacts",
                        "type": "number",
                        "min": 2,
                        "default": 2,
                        "help": "Alert when at least this many contacts share the same name and role for an account.",
                    }
                },
            },
            "missing_role": {
                "label": "Missing contact role",
                "description": "Detects account-contact relations that do not specify a role.",
                "parameters": {},
            },
            "same_name_different_role": {
                "label": "Same contact name with different roles",
                "description": "Highlights contacts that have more than one role on the same account.",
                "parameters": {
                    "min_unique_roles": {
                        "label": "Minimum unique roles",
                        "type": "number",
                        "min": 2,
                        "default": 2,
                        "help": "Alert when a contact name is associated with at least this many distinct roles.",
                    }
                },
            },
            "duplicate_contact_point": {
                "label": "Duplicate contact point",
                "description": "Finds duplicate emails or phone numbers stored for a contact.",
                "parameters": {
                    "channel": {
                        "label": "Contact point type",
                        "type": "select",
                        "options": [
                            {"value": "phone", "label": "Phone"},
                            {"value": "email", "label": "Email"},
                        ],
                        "default": "phone",
                        "help": "Choose which contact point to inspect for duplicates.",
                    },
                    "min_count": {
                        "label": "Minimum duplicates",
                        "type": "number",
                        "min": 2,
                        "default": 2,
                        "help": "Alert when at least this many identical values exist for the chosen contact point.",
                    },
                },
            },
        }

    def _duplicate_role_same_name_alert(self, definition: Dict) -> List[Dict[str, str]]:
        logic = definition.get("logic", {})
        parameters = logic.get("parameters", {})
        try:
            min_count = int(parameters.get("min_count", 2))
        except (ValueError, TypeError):
            min_count = 2
        min_count = max(min_count, 2)

        alerts: List[Dict[str, str]] = []
        for account_id, relations in self.data_store.account_to_contact_relations.items():
            bucket: Dict[tuple, List[dict]] = defaultdict(list)
            for relation in relations:
                contact = self.data_store.contacts.get(relation.get("ContactId"))
                if not contact:
                    continue
                key = (
                    _normalize(contact.get("FirstName")),
                    _normalize(contact.get("LastName")),
                    _normalize(relation.get("Roles")),
                )
                bucket[key].append(contact)
            for (first, last, role), contacts in bucket.items():
                if not role:
                    continue
                if len(contacts) >= min_count:
                    account_name = self.data_store.accounts.get(account_id, {}).get("Name", account_id)
                    alerts.append(
                        {
                            "type": definition.get("name", "Duplicate role"),
                            "message": (
                                f"Account '{account_name}' has {len(contacts)} contacts named {first.title()} {last.title()} "
                                f"with the role '{role}'. Threshold: {min_count}."
                            ),
                            "definitionId": definition.get("id"),
                            "logic": definition.get("logic", {}),
                        }
                    )
        return alerts

    def _missing_role_alert(self, definition: Dict) -> List[Dict[str, str]]:
        alerts: List[Dict[str, str]] = []
        for account_id, relations in self.data_store.account_to_contact_relations.items():
            for relation in relations:
                role = _normalize(relation.get("Roles"))
                if role:
                    continue
                contact = self.data_store.contacts.get(relation.get("ContactId"))
                contact_name = self._format_contact_name(contact)
                account_name = self.data_store.accounts.get(account_id, {}).get("Name", account_id)
                alerts.append(
                    {
                        "type": definition.get("name", "Missing role"),
                        "message": f"Contact {contact_name} linked to account '{account_name}' has no assigned role.",
                        "definitionId": definition.get("id"),
                        "logic": definition.get("logic", {}),
                    }
                )
        return alerts

    def _same_name_different_role_alert(self, definition: Dict) -> List[Dict[str, str]]:
        logic = definition.get("logic", {})
        parameters = logic.get("parameters", {})
        try:
            min_unique_roles = int(parameters.get("min_unique_roles", 2))
        except (TypeError, ValueError):
            min_unique_roles = 2
        min_unique_roles = max(min_unique_roles, 2)

        alerts: List[Dict[str, str]] = []
        for account_id, relations in self.data_store.account_to_contact_relations.items():
            name_to_roles: Dict[tuple, set] = defaultdict(set)
            for relation in relations:
                contact = self.data_store.contacts.get(relation.get("ContactId"))
                if not contact:
                    continue
                name_key = (
                    _normalize(contact.get("FirstName")),
                    _normalize(contact.get("LastName")),
                )
                role = _normalize(relation.get("Roles"))
                if role:
                    name_to_roles[name_key].add(role)
            for (first, last), roles in name_to_roles.items():
                if len(roles) >= min_unique_roles:
                    account_name = self.data_store.accounts.get(account_id, {}).get("Name", account_id)
                    formatted_name = f"{first.title()} {last.title()}".strip()
                    role_list = ", ".join(sorted(role.title() for role in roles))
                    alerts.append(
                        {
                            "type": definition.get("name", "Role mismatch"),
                            "message": (
                                f"Account '{account_name}' has contact {formatted_name} listed with multiple roles: {role_list}. "
                                f"Threshold: {min_unique_roles} unique roles."
                            ),
                            "definitionId": definition.get("id"),
                            "logic": definition.get("logic", {}),
                        }
                    )
        return alerts

    def _duplicate_contact_points_alert(self, definition: Dict) -> List[Dict[str, str]]:
        logic = definition.get("logic", {})
        parameters = logic.get("parameters", {})
        channel = str(parameters.get("channel", "")).strip().lower()
        try:
            min_count = int(parameters.get("min_count", 2))
        except (TypeError, ValueError):
            min_count = 2
        min_count = max(min_count, 2)

        candidate_keys = []
        if channel == "phone":
            candidate_keys = ["TelephoneNumber", "Phone"]
        elif channel == "email":
            candidate_keys = ["EmailAddress", "Email"]
        else:
            return []

        alerts: List[Dict[str, str]] = []
        for contact_id, contact in self.data_store.contacts.items():
            if channel == "phone":
                values = self._collect_values(
                    self.data_store.get_phones_for_contact(contact_id),
                    candidate_keys,
                )
            else:
                values = self._collect_values(
                    self.data_store.get_emails_for_contact(contact_id),
                    candidate_keys,
                )

            duplicates = self._find_duplicates(values, min_count)

            if duplicates:
                readable_values = ", ".join(sorted(duplicates))
                message = (
                    f"Contact {self._format_contact_name(contact)} has duplicate {channel} values: {readable_values}. "
                    f"Threshold: {min_count}."
                )
                alerts.append(
                    {
                        "type": definition.get("name", f"Duplicate {channel}"),
                        "message": message,
                        "definitionId": definition.get("id"),
                        "logic": definition.get("logic", {}),
                    }
                )
        return alerts

    def _collect_values(self, records: List[dict], candidate_keys: List[str]) -> List[str]:
        values: List[str] = []
        for record in records:
            for key in candidate_keys:
                value = record.get(key)
                if value:
                    values.append(value.strip())
                    break
        return values

    def _find_duplicates(self, values: List[str], min_count: int) -> List[str]:
        seen: Dict[str, int] = defaultdict(int)
        original: Dict[str, str] = {}
        for value in values:
            normalized = value.lower()
            seen[normalized] += 1
            original.setdefault(normalized, value)
        duplicates = [original[value] for value, count in seen.items() if count >= min_count]
        return duplicates

    def _format_contact_name(self, contact: dict) -> str:
        if not contact:
            return "Unknown contact"
        first = contact.get("FirstName", "").strip()
        last = contact.get("LastName", "").strip()
        full_name = f"{first} {last}".strip()
        return full_name or contact.get("Id", "Unknown contact")
