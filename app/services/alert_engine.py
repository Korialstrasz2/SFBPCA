from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.data.alert_config_store import AlertConfigStore
from app.data.data_store import DataStore


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


class AlertEngine:
    """Build alerts based on configured logic definitions."""

    LOGIC_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "alert_logic_catalog.json"

    def __init__(self, data_store: DataStore, config_store: AlertConfigStore) -> None:
        self.data_store = data_store
        self.config_store = config_store
        self._logic_catalog = self._load_logic_catalog()

    def _load_logic_catalog(self) -> Dict[str, Dict[str, Any]]:
        if not self.LOGIC_CATALOG_PATH.exists():
            return {}
        with self.LOGIC_CATALOG_PATH.open("r", encoding="utf-8") as handle:
            entries = json.load(handle)
        catalog: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            logic_id = entry.get("id")
            if logic_id:
                catalog[logic_id] = entry
        return catalog

    def list_available_logic(self) -> List[Dict[str, Any]]:
        return list(self._logic_catalog.values())

    def get_logic_metadata(self, logic_id: str) -> Dict[str, Any]:
        return dict(self._logic_catalog.get(logic_id, {}))

    def is_valid_logic(self, logic_id: str) -> bool:
        return logic_id in self._logic_catalog

    def build_alerts(self) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        configs = self.config_store.list_configs()
        for config in configs:
            if not config.get("enabled", True):
                continue
            logic_id = config.get("logic_id")
            if not logic_id or not self.is_valid_logic(logic_id):
                continue
            parameters = config.get("parameters") or {}
            contexts = self._execute_logic(logic_id, parameters)
            logic_metadata = self._logic_catalog.get(logic_id, {})
            type_template = config.get("type_template") or logic_metadata.get("type_template") or config.get("name", "Alert")
            message_template = config.get("message_template") or logic_metadata.get("message_template") or logic_metadata.get("description", "")
            for context in contexts:
                alert_type = self._render_template(type_template, context)
                message = self._render_template(message_template, context)
                alerts.append(
                    {
                        "type": alert_type,
                        "message": message,
                        "logic_id": logic_id,
                        "config_id": config.get("id"),
                        "name": config.get("name"),
                        "context": context,
                    }
                )
        return alerts

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        if not template:
            return ""
        try:
            return template.format(**context)
        except KeyError:
            return template

    def _execute_logic(self, logic_id: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        handlers = {
            "duplicate_role_same_name": self._logic_duplicate_role_same_name,
            "missing_role": self._logic_missing_role,
            "same_name_different_role": self._logic_same_name_different_role,
            "duplicate_contact_points": self._logic_duplicate_contact_points,
        }
        handler = handlers.get(logic_id)
        if not handler:
            return []
        return handler(parameters or {})

    def _logic_duplicate_role_same_name(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        contexts: List[Dict[str, Any]] = []
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
            for (first, last, role_value), contacts in bucket.items():
                if not role_value:
                    continue
                if len(contacts) > 1:
                    account_name = self.data_store.accounts.get(account_id, {}).get("Name", account_id)
                    formatted_name = f"{first.title()} {last.title()}".strip()
                    representative_contact = contacts[0] if contacts else None
                    display_name = formatted_name or self._format_contact_name(representative_contact)
                    contexts.append(
                        {
                            "account_id": account_id,
                            "account_name": account_name,
                            "contact_name": display_name,
                            "role": role_value,
                            "role_title": role_value.title(),
                            "duplicate_count": len(contacts),
                            "contact_ids": [contact.get("Id") for contact in contacts if contact.get("Id")],
                        }
                    )
        return contexts

    def _logic_missing_role(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        contexts: List[Dict[str, Any]] = []
        for account_id, relations in self.data_store.account_to_contact_relations.items():
            account_name = self.data_store.accounts.get(account_id, {}).get("Name", account_id)
            for relation in relations:
                role = _normalize(relation.get("Roles"))
                if role:
                    continue
                contact_id = relation.get("ContactId")
                contact = self.data_store.contacts.get(contact_id)
                contact_name = self._format_contact_name(contact)
                contexts.append(
                    {
                        "account_id": account_id,
                        "account_name": account_name,
                        "contact_id": contact_id,
                        "contact_name": contact_name,
                    }
                )
        return contexts

    def _logic_same_name_different_role(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        contexts: List[Dict[str, Any]] = []
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
                    formatted_name = f"{first.title()} {last.title()}".strip() or account_id
                    sorted_roles = sorted(roles)
                    role_list = ", ".join(role.title() for role in sorted_roles)
                    contexts.append(
                        {
                            "account_id": account_id,
                            "account_name": account_name,
                            "contact_name": formatted_name,
                            "roles": sorted_roles,
                            "roles_display": [role.title() for role in sorted_roles],
                            "role_list": role_list,
                            "role_count": len(roles),
                        }
                    )
        return contexts

    def _logic_duplicate_contact_points(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        contexts: List[Dict[str, Any]] = []
        allowed_kind = parameters.get("value_kind")
        if isinstance(allowed_kind, str):
            allowed_kind = allowed_kind.lower()
        for contact_id, contact in self.data_store.contacts.items():
            phone_values = self._collect_values(
                self.data_store.get_phones_for_contact(contact_id),
                ["TelephoneNumber", "Phone"],
            )
            email_values = self._collect_values(
                self.data_store.get_emails_for_contact(contact_id),
                ["EmailAddress", "Email"],
            )
            contexts.extend(
                self._build_contact_point_contexts(
                    contact_id,
                    contact,
                    "phone",
                    "phone numbers",
                    phone_values,
                    allowed_kind,
                )
            )
            contexts.extend(
                self._build_contact_point_contexts(
                    contact_id,
                    contact,
                    "email",
                    "email addresses",
                    email_values,
                    allowed_kind,
                )
            )
        return contexts

    def _build_contact_point_contexts(
        self,
        contact_id: str,
        contact: dict,
        value_kind: str,
        value_label: str,
        values: Iterable[str],
        allowed_kind: str | None,
    ) -> List[Dict[str, Any]]:
        duplicates = self._find_duplicates(values)
        if not duplicates:
            return []
        if allowed_kind and value_kind != allowed_kind:
            return []
        duplicate_value_list = ", ".join(sorted(duplicates))
        context = {
            "contact_id": contact_id,
            "contact_name": self._format_contact_name(contact),
            "value_kind": value_kind,
            "value_kind_title": value_kind.title(),
            "value_label": value_label,
            "duplicate_values": sorted(duplicates),
            "duplicate_value_list": duplicate_value_list,
            "duplicate_count": len(duplicates),
            "source_counts": self._count_sources(values),
        }
        return [context]

    def _collect_values(self, records: Iterable[dict], candidate_keys: List[str]) -> List[str]:
        values: List[str] = []
        for record in records:
            for key in candidate_keys:
                value = record.get(key)
                if value:
                    values.append(value.strip())
                    break
        return values

    def _find_duplicates(self, values: Iterable[str]) -> List[str]:
        seen: Dict[str, int] = defaultdict(int)
        originals: Dict[str, str] = {}
        for value in values:
            normalized = value.lower()
            seen[normalized] += 1
            originals.setdefault(normalized, value)
        duplicates = [originals[value] for value, count in seen.items() if count > 1]
        return duplicates

    def _count_sources(self, values: Iterable[str]) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for value in values:
            counts[value.lower()] += 1
        return dict(counts)

    def _format_contact_name(self, contact: dict | None) -> str:
        if not contact:
            return "Unknown contact"
        first = (contact.get("FirstName") or "").strip()
        last = (contact.get("LastName") or "").strip()
        full_name = f"{first} {last}".strip()
        return full_name or contact.get("Id", "Unknown contact")
