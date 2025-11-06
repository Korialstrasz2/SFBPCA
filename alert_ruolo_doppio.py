"""Alert logic for duplicate roles within the same account."""

from __future__ import annotations

from typing import Dict, List, Set

from new_alert_summary import ALERT_SUMMARY
from new_data_structure_and_store import AccountContext, DATA_STORE


_EMITTED_KEYS: Set[str] = set()


def _normalise(value: str | None) -> str:
    return (value or "").strip().lower()


def reset_state() -> None:
    _EMITTED_KEYS.clear()


def inspect_contact(account_context: AccountContext, contact: Dict[str, str]) -> None:
    relation = contact.get("_relation") or {}
    role_label = relation.get("Roles")
    role_key = _normalise(role_label)
    if not role_key:
        return

    account_id = account_context.account_id
    peers = [
        other
        for other in account_context.contacts
        if other.get("Id") != contact.get("Id") and _normalise((other.get("_relation") or {}).get("Roles")) == role_key
    ]
    if not peers:
        return

    dedupe_key = f"role_doppio::{account_id}::{role_key}"
    if dedupe_key in _EMITTED_KEYS:
        return
    _EMITTED_KEYS.add(dedupe_key)

    account_name = DATA_STORE.resolve_account_name(account_id)
    involved_contacts: List[str] = [DATA_STORE.resolve_contact_name(contact.get("Id"))]
    for peer in peers:
        involved_contacts.append(DATA_STORE.resolve_contact_name(peer.get("Id")))

    message = (
        f"Role '{role_label}' appears multiple times in account {account_name}: "
        + ", ".join(sorted(set(involved_contacts)))
    )

    ALERT_SUMMARY.record(
        {
            "alert_type": "Duplicate account role",
            "account_id": account_id,
            "account_name": account_name,
            "contact_id": contact.get("Id"),
            "contact_name": DATA_STORE.resolve_contact_name(contact.get("Id")),
            "details": message,
            "triggered_at": DATA_STORE.timestamp(),
            "message": message,
        }
    )
