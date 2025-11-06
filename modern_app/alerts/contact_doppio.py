"""Alert logic for detecting duplicate contacts within an account."""

from __future__ import annotations

from typing import Dict, List, Set

from ..alert_summary import ALERT_SUMMARY
from ..data_store import AccountContext, DATA_STORE


_EMITTED_KEYS: Set[str] = set()
_IDENTIFIER_FIELDS = {
    "Codice fiscale": "FiscalCode__c",
    "Partita IVA": "VATNumber__c",
    "Email": "Email",
}


def _normalise(value: str | None) -> str:
    return (value or "").strip().lower()


def reset_state() -> None:
    """Clear memoised keys between alert runs."""

    _EMITTED_KEYS.clear()


def run(account_context: AccountContext) -> None:
    """Evaluate duplicate identifiers for all contacts in the account."""

    for contact in account_context.contacts:
        _inspect_contact(account_context, contact)


def _inspect_contact(account_context: AccountContext, contact: Dict[str, str]) -> None:
    contact_id = contact.get("Id")
    if not contact_id:
        return

    account_id = account_context.account_id
    collision_steps: List[str] = []
    detail_lines: List[str] = []

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
                detail += f" (contatti coinvolti: {', '.join(match_names)})"
            detail_lines.append(detail)

    if not detail_lines:
        return

    dedupe_key = f"contact_doppio::{account_id}::{contact_id}"
    if dedupe_key in _EMITTED_KEYS:
        return
    _EMITTED_KEYS.add(dedupe_key)

    account_name = DATA_STORE.resolve_account_name(account_id)
    contact_name = DATA_STORE.resolve_contact_name(contact_id)

    collision_steps.append("Passo 1: ho analizzato gli identificativi principali dei contatti dell'account.")
    collision_steps.append(
        "Passo 2: ho trovato corrispondenze duplicate per il contatto "
        f"{contact_name} sugli attributi:"
    )
    for line in detail_lines:
        collision_steps.append(f"  - {line}")
    collision_steps.append(
        "Commento: verifica i dati dei contatti indicati e aggiorna le informazioni in Salesforce."
    )

    ALERT_SUMMARY.record(
        {
            "alert_type": "Contatti potenzialmente duplicati",
            "account_id": account_id,
            "account_name": account_name,
            "contact_id": contact_id,
            "contact_name": contact_name,
            "details": "\n".join(collision_steps),
            "message": (
                "Sono state individuate possibili duplicazioni per "
                f"{contact_name} nell'account {account_name}."
            ),
            "steps": collision_steps,
        }
    )
