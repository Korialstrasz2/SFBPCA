"""Alert logic for detecting duplicate contacts within an account."""

from __future__ import annotations

from typing import Dict, List, Set

from new_alert_summary import ALERT_SUMMARY
from new_data_structure_and_store import AccountContext, DATA_STORE


_EMITTED_KEYS: Set[str] = set()
_IDENTIFIER_FIELDS = {
    "Fiscal code": "FiscalCode__c",
    "VAT number": "VATNumber__c",
    "Email": "Email",
}


def _normalise(value: str | None) -> str:
    return (value or "").strip().lower()


def reset_state() -> None:
    """Clear memoised keys between alert runs."""

    _EMITTED_KEYS.clear()


def inspect_contact(account_context: AccountContext, contact: Dict[str, str]) -> None:
    """Record an alert when a contact collides with another contact in the same account."""

    contact_id = contact.get("Id")
    if not contact_id:
        return

    account_id = account_context.account_id
    collision_keys: List[str] = []

    for label, field in _IDENTIFIER_FIELDS.items():
        token = _normalise(contact.get(field))
        if not token:
            continue
        matches = [
            other
            for other in account_context.contacts
            if other.get("Id") != contact_id and _normalise(other.get(field)) == token
        ]
        if matches:
            match_names = sorted(
                {
                    DATA_STORE.resolve_contact_name(other.get("Id"))
                    for other in matches
                    if other.get("Id")
                }
            )
            detail = f"{label}: {token}"
            if match_names:
                detail += f" (matches: {', '.join(match_names)})"
            collision_keys.append(detail)

    if not collision_keys:
        return

    dedupe_key = f"contact_doppio::{account_id}::{contact_id}"
    if dedupe_key in _EMITTED_KEYS:
        return
    _EMITTED_KEYS.add(dedupe_key)

    account_name = DATA_STORE.resolve_account_name(account_id)
    contact_name = DATA_STORE.resolve_contact_name(contact_id)

    ALERT_SUMMARY.record(
        {
            "alert_type": "Duplicate contact identifiers",
            "account_id": account_id,
            "account_name": account_name,
            "contact_id": contact_id,
            "contact_name": contact_name,
            "details": "; ".join(sorted(set(collision_keys))),
            "triggered_at": DATA_STORE.timestamp(),
            "message": f"{contact_name} in account {account_name} shares identifiers with another contact.",
        }
    )
