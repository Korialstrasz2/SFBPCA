"""Alert evaluation service."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Sequence

from storage.data_store import DataStore


class AlertService:
    """Evaluate configurable alerts over the imported data."""

    DEFAULT_ALERTS = {
        "duplicate_role_same_name": "Contacts with the same role and matching name within an account",
        "missing_role": "Contacts without a role on an account",
        "conflicting_roles_same_name": "Contacts with the same name but different roles",
        "contact_point_mismatch": "Contacts whose phone or email do not match their contact points",
    }

    def __init__(self, data_store: DataStore) -> None:
        self._data_store = data_store

    def evaluate(self, requested_alerts: Sequence[str] | None = None) -> List[dict]:
        if requested_alerts:
            selected = [alert for alert in requested_alerts if alert in self.DEFAULT_ALERTS]
        else:
            selected = list(self.DEFAULT_ALERTS.keys())

        results: List[dict] = []
        for alert_id in selected:
            method = getattr(self, f"_run_{alert_id}", None)
            if not method:
                continue
            matches = method()
            results.append({
                "id": alert_id,
                "description": self.DEFAULT_ALERTS[alert_id],
                "matches": matches,
            })
        return results

    # --- Alert implementations -------------------------------------------------

    def _run_duplicate_role_same_name(self) -> List[dict]:
        grouped: Dict[str, Dict[tuple, List[dict]]] = defaultdict(lambda: defaultdict(list))

        for relation in self._data_store.account_contact_relations:
            account_id = relation.get("AccountId")
            contact_id = relation.get("ContactId")
            role = (relation.get("Role") or "").strip()
            if not account_id or not contact_id or not role:
                continue

            contact = self._data_store.contacts.get(contact_id)
            if not contact:
                continue

            key = (
                role.lower(),
                (contact.get("FirstName") or "").strip().lower(),
                (contact.get("LastName") or "").strip().lower(),
            )
            grouped[account_id][key].append(contact)

        alerts: List[dict] = []
        for account_id, duplicates in grouped.items():
            account = self._data_store.accounts.get(account_id, {})
            account_name = account.get("Name", account_id)
            for key, contacts in duplicates.items():
                if len(contacts) < 2:
                    continue
                role, first_name, last_name = key
                alerts.append({
                    "account": account_name,
                    "role": role,
                    "first_name": first_name,
                    "last_name": last_name,
                    "contact_ids": [contact.get("Id") for contact in contacts],
                })
        return alerts

    def _run_missing_role(self) -> List[dict]:
        missing_by_account: Dict[str, List[dict]] = defaultdict(list)

        for relation in self._data_store.account_contact_relations:
            account_id = relation.get("AccountId")
            contact_id = relation.get("ContactId")
            role = (relation.get("Role") or "").strip()
            if not account_id or not contact_id:
                continue
            if role:
                continue

            contact = self._data_store.contacts.get(contact_id)
            if not contact:
                continue
            missing_by_account[account_id].append(contact)

        alerts: List[dict] = []
        for account_id, contacts in missing_by_account.items():
            account = self._data_store.accounts.get(account_id, {})
            account_name = account.get("Name", account_id)
            alerts.append({
                "account": account_name,
                "contacts": [
                    {
                        "id": contact.get("Id"),
                        "first_name": (contact.get("FirstName") or "").strip(),
                        "last_name": (contact.get("LastName") or "").strip(),
                    }
                    for contact in contacts
                ],
            })
        return alerts

    def _run_conflicting_roles_same_name(self) -> List[dict]:
        name_roles_by_account: Dict[str, Dict[tuple, set]] = defaultdict(lambda: defaultdict(set))
        contacts_by_key: Dict[str, Dict[tuple, List[str]]] = defaultdict(lambda: defaultdict(list))

        for relation in self._data_store.account_contact_relations:
            account_id = relation.get("AccountId")
            contact_id = relation.get("ContactId")
            if not account_id or not contact_id:
                continue

            contact = self._data_store.contacts.get(contact_id)
            if not contact:
                continue

            first = (contact.get("FirstName") or "").strip().lower()
            last = (contact.get("LastName") or "").strip().lower()
            if not first and not last:
                continue

            role = (relation.get("Role") or "").strip().lower() or "(none)"
            key = (first, last)
            name_roles_by_account[account_id][key].add(role)
            contacts_by_key[account_id][key].append(contact_id)

        alerts: List[dict] = []
        for account_id, names in name_roles_by_account.items():
            account = self._data_store.accounts.get(account_id, {})
            account_name = account.get("Name", account_id)
            for key, roles in names.items():
                if len(roles) < 2:
                    continue
                contacts = contacts_by_key[account_id][key]
                alerts.append({
                    "account": account_name,
                    "first_name": key[0],
                    "last_name": key[1],
                    "roles": sorted(roles),
                    "contact_ids": contacts,
                })
        return alerts

    def _run_contact_point_mismatch(self) -> List[dict]:
        alerts: List[dict] = []
        phone_by_parent = defaultdict(list)
        for record in self._data_store.contact_point_phone:
            parent_id = record.get("ParentId")
            if not parent_id:
                continue
            phone = (record.get("PhoneNumber") or record.get("Value") or "").strip()
            if phone:
                phone_by_parent[parent_id].append(phone)

        email_by_parent = defaultdict(list)
        for record in self._data_store.contact_point_email:
            parent_id = record.get("ParentId")
            if not parent_id:
                continue
            email = (record.get("EmailAddress") or record.get("Value") or "").strip().lower()
            if email:
                email_by_parent[parent_id].append(email)

        for contact in self._data_store.contacts.values():
            individual_id = (contact.get("IndividualId") or "").strip()
            if not individual_id:
                continue

            phone = (contact.get("Phone") or "").strip()
            email = (contact.get("Email") or "").strip().lower()

            mismatches: Dict[str, str] = {}
            if phone:
                phones = phone_by_parent.get(individual_id, [])
                normalized_phone = phone
                if normalized_phone not in phones:
                    mismatches["phone"] = phone

            if email:
                emails = email_by_parent.get(individual_id, [])
                normalized_email = email
                if normalized_email not in emails:
                    mismatches["email"] = email

            if mismatches:
                alerts.append({
                    "contact_id": contact.get("Id"),
                    "first_name": (contact.get("FirstName") or "").strip(),
                    "last_name": (contact.get("LastName") or "").strip(),
                    "issues": mismatches,
                })
        return alerts


__all__ = ["AlertService"]
