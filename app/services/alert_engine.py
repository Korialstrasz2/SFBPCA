from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, List, Set
from uuid import uuid4

from app.data.data_store import DataStore


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


class AlertEngine:
    DEFAULT_CONFIG: List[Dict[str, Any]] = [
        {
            "id": "duplicate_role",
            "label": "Duplicate role",
            "description": "Highlight contacts with the same name and role on a single account.",
            "enabled": True,
            "kind": "system",
        },
        {
            "id": "missing_role",
            "label": "Missing role",
            "description": "Flag linked contacts that are missing a role assignment.",
            "enabled": True,
            "kind": "system",
        },
        {
            "id": "role_mismatch",
            "label": "Role mismatch",
            "description": "Spot contacts that appear with different roles on the same account.",
            "enabled": True,
            "kind": "system",
        },
        {
            "id": "duplicate_contact_points",
            "label": "Duplicate contact points",
            "description": "Detect duplicate phone numbers or email addresses for a single contact.",
            "enabled": True,
            "kind": "system",
        },
    ]

    def __init__(self, data_store: DataStore) -> None:
        self.data_store = data_store
        self._default_map = {entry["id"]: deepcopy(entry) for entry in self.DEFAULT_CONFIG}
        self._config: List[Dict[str, Any]] = [deepcopy(entry) for entry in self.DEFAULT_CONFIG]

    def get_config(self) -> List[Dict[str, Any]]:
        return [deepcopy(entry) for entry in self._config]

    def update_config(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalised: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        for entry in entries or []:
            entry_id_raw = entry.get("id")
            entry_id = self._clean_identifier(entry_id_raw)
            if not entry_id:
                entry_id = f"custom-{uuid4().hex}"
            if entry_id in seen:
                continue
            seen.add(entry_id)

            if entry_id in self._default_map:
                default_entry = self._default_map[entry_id]
                normalised.append(
                    {
                        **default_entry,
                        "label": self._clean_text(entry.get("label")) or default_entry["label"],
                        "description": self._clean_text(entry.get("description")) or default_entry["description"],
                        "enabled": bool(entry.get("enabled", True)),
                    }
                )
            else:
                normalised.append(
                    {
                        "id": entry_id,
                        "label": self._clean_text(entry.get("label")) or "Custom alert",
                        "description": self._clean_text(entry.get("description")),
                        "message": self._clean_text(entry.get("message"))
                        or self._clean_text(entry.get("description"))
                        or "Custom alert message",
                        "enabled": bool(entry.get("enabled", True)),
                        "kind": "custom",
                    }
                )

        normalised_map = {entry["id"]: entry for entry in normalised}
        ordered_config: List[Dict[str, Any]] = []

        for default in self.DEFAULT_CONFIG:
            stored = normalised_map.get(default["id"])
            if stored is None:
                previous = next((cfg for cfg in self._config if cfg["id"] == default["id"]), None)
                stored = deepcopy(previous or default)
            ordered_config.append(stored)

        for entry in normalised:
            if entry.get("kind") == "custom":
                ordered_config.append(entry)

        self._config = [deepcopy(entry) for entry in ordered_config]
        return self.get_config()

    def build_alerts(self) -> List[Dict[str, str]]:
        alerts: List[Dict[str, str]] = []
        handler_map = {
            "duplicate_role": self._duplicate_role_same_name_alert,
            "missing_role": self._missing_role_alert,
            "role_mismatch": self._same_name_different_role_alert,
            "duplicate_contact_points": self._duplicate_contact_points_alert,
        }

        for entry in self._config:
            if not entry.get("enabled", True):
                continue
            entry_id = entry.get("id")
            if entry.get("kind") == "custom":
                message = entry.get("message") or entry.get("description")
                if message:
                    alerts.append({"type": entry.get("label", "Custom alert"), "message": message})
                continue

            handler = handler_map.get(entry_id)
            if not handler:
                continue
            label = entry.get("label") or self._default_map.get(entry_id, {}).get("label", "Alert")
            for alert in handler():
                shaped = dict(alert)
                original_type = shaped.get("type")
                if label and original_type and original_type != label:
                    shaped["type"] = f"{label} — {original_type}"
                else:
                    shaped["type"] = label or original_type or "Alert"
                alerts.append(shaped)
        return alerts

    @staticmethod
    def _clean_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _clean_identifier(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _duplicate_role_same_name_alert(self) -> List[Dict[str, str]]:
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
                if len(contacts) > 1:
                    account_name = self.data_store.accounts.get(account_id, {}).get("Name", account_id)
                    alerts.append(
                        {
                            "type": "Duplicate role",
                            "message": f"Account '{account_name}' has {len(contacts)} contacts named {first.title()} {last.title()} with the role '{role}'.",
                        }
                    )
        return alerts

    def _missing_role_alert(self) -> List[Dict[str, str]]:
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
                        "type": "Missing role",
                        "message": f"Contact {contact_name} linked to account '{account_name}' has no assigned role.",
                    }
                )
        return alerts

    def _same_name_different_role_alert(self) -> List[Dict[str, str]]:
        alerts: List[Dict[str, str]] = []
        for account_id, relations in self.data_store.account_to_contact_relations.items():
            name_to_roles: Dict[tuple, set] = defaultdict(set)
            for relation in relations:
                contact = self.data_store.contacts.get(relation.get("ContactId"))
                if not contact:
                    continue
                name_key = (_normalize(contact.get("FirstName")), _normalize(contact.get("LastName")))
                role = _normalize(relation.get("Roles"))
                if role:
                    name_to_roles[name_key].add(role)
            for (first, last), roles in name_to_roles.items():
                if len(roles) > 1:
                    account_name = self.data_store.accounts.get(account_id, {}).get("Name", account_id)
                    formatted_name = f"{first.title()} {last.title()}".strip()
                    role_list = ", ".join(sorted(role.title() for role in roles))
                    alerts.append(
                        {
                            "type": "Role mismatch",
                            "message": f"Account '{account_name}' has contact {formatted_name} listed with multiple roles: {role_list}.",
                        }
                    )
        return alerts

    def _duplicate_contact_points_alert(self) -> List[Dict[str, str]]:
        alerts: List[Dict[str, str]] = []
        for contact_id, contact in self.data_store.contacts.items():
            phone_values = self._collect_values(
                self.data_store.get_phones_for_contact(contact_id),
                ["TelephoneNumber", "Phone"],
            )
            email_values = self._collect_values(self.data_store.get_emails_for_contact(contact_id), ["EmailAddress", "Email"])

            duplicate_phones = self._find_duplicates(phone_values)
            duplicate_emails = self._find_duplicates(email_values)

            if duplicate_phones:
                alerts.append(
                    {
                        "type": "Duplicate phone",
                        "message": f"Contact {self._format_contact_name(contact)} has duplicate phone numbers: {', '.join(sorted(duplicate_phones))}.",
                    }
                )
            if duplicate_emails:
                alerts.append(
                    {
                        "type": "Duplicate email",
                        "message": f"Contact {self._format_contact_name(contact)} has duplicate email addresses: {', '.join(sorted(duplicate_emails))}.",
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

    def _find_duplicates(self, values: List[str]) -> List[str]:
        seen: Dict[str, int] = defaultdict(int)
        original: Dict[str, str] = {}
        for value in values:
            normalized = value.lower()
            seen[normalized] += 1
            original.setdefault(normalized, value)
        duplicates = [original[value] for value, count in seen.items() if count > 1]
        return duplicates

    def _format_contact_name(self, contact: dict) -> str:
        if not contact:
            return "Unknown contact"
        first = contact.get("FirstName", "").strip()
        last = contact.get("LastName", "").strip()
        full_name = f"{first} {last}".strip()
        return full_name or contact.get("Id", "Unknown contact")
