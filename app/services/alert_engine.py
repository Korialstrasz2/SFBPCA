from collections import defaultdict
from typing import Dict, List

from app.data.data_store import DataStore


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


class AlertEngine:
    def __init__(self, data_store: DataStore) -> None:
        self.data_store = data_store

    def build_alerts(self) -> List[Dict[str, str]]:
        alerts: List[Dict[str, str]] = []
        alerts.extend(self._duplicate_role_same_name_alert())
        alerts.extend(self._missing_role_alert())
        alerts.extend(self._same_name_different_role_alert())
        alerts.extend(self._duplicate_contact_points_alert())
        return alerts

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
