from collections import defaultdict
from typing import Any, Dict, Iterable, List

from app.data.data_store import DataStore


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


class AlertEngine:
    RULE_DEFINITIONS: Iterable[Dict[str, str]] = (
        {
            "id": "duplicate_role_same_name",
            "label": "Duplicate role assignments",
            "description": (
                "Flags accounts where multiple contacts share the same role and the same name."
            ),
            "handler": "_duplicate_role_same_name_alert",
            "default_enabled": True,
        },
        {
            "id": "missing_role",
            "label": "Missing role assignments",
            "description": "Highlights contacts linked to an account without an assigned role.",
            "handler": "_missing_role_alert",
            "default_enabled": True,
        },
        {
            "id": "same_name_different_role",
            "label": "Role mismatches for the same contact name",
            "description": (
                "Detects contacts that appear with multiple roles under the same account."
            ),
            "handler": "_same_name_different_role_alert",
            "default_enabled": True,
        },
        {
            "id": "duplicate_contact_points",
            "label": "Duplicate contact points",
            "description": "Finds duplicate phone numbers or email addresses for a single contact.",
            "handler": "_duplicate_contact_points_alert",
            "default_enabled": True,
        },
    )

    def __init__(self, data_store: DataStore) -> None:
        self.data_store = data_store
        self._default_rule_config = {
            rule["id"]: bool(rule.get("default_enabled", True))
            for rule in self.RULE_DEFINITIONS
        }
        self._rule_config = dict(self._default_rule_config)

    def build_alerts(self) -> List[Dict[str, str]]:
        alerts: List[Dict[str, str]] = []
        for rule in self.RULE_DEFINITIONS:
            rule_id = rule["id"]
            if not self._rule_config.get(rule_id, True):
                continue
            handler_name = rule["handler"]
            handler = getattr(self, handler_name, None)
            if not handler:
                continue
            alerts.extend(handler())
        return alerts

    def get_rule_configuration(self) -> List[Dict[str, Any]]:
        configuration: List[Dict[str, Any]] = []
        for rule in self.RULE_DEFINITIONS:
            rule_id = rule["id"]
            configuration.append(
                {
                    "id": rule_id,
                    "label": rule["label"],
                    "description": rule["description"],
                    "enabled": self._rule_config.get(rule_id, True),
                    "default_enabled": self._default_rule_config.get(rule_id, True),
                }
            )
        return configuration

    def update_rule_configuration(self, updates: Dict[str, bool]) -> None:
        unknown_rules = [rule_id for rule_id in updates if rule_id not in self._rule_config]
        if unknown_rules:
            raise ValueError(f"Unknown rule identifiers: {', '.join(sorted(unknown_rules))}")

        for rule_id, enabled in updates.items():
            self._rule_config[rule_id] = bool(enabled)

    def reset_rule_configuration(self) -> None:
        self._rule_config = dict(self._default_rule_config)

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
