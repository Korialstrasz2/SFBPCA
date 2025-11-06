"""Avviso per il rilevamento di contatti con identificativi duplicati."""

from __future__ import annotations

from typing import List, Set

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
    """Analizza i contatti dell'account e registra eventuali duplicati."""

    account_id = account_context.account_id
    account_name = DATA_STORE.resolve_account_name(account_id)

    collision_blocks: List[str] = []
    for contact in account_context.contacts:
        contact_id = contact.get("Id")
        if not contact_id:
            continue

        dedupe_key = f"contact_doppio::{account_id}::{contact_id}"
        if dedupe_key in _EMITTED_KEYS:
            continue

        collision_details: List[str] = []
        for label, field in _IDENTIFIER_FIELDS.items():
            token = _normalise(contact.get(field))
            if not token:
                continue

            matches = [
                other
                for other in account_context.contacts
                if other.get("Id") != contact_id and _normalise(other.get(field)) == token
            ]
            if not matches:
                continue

            match_names = sorted(
                {
                    DATA_STORE.resolve_contact_name(other.get("Id"))
                    for other in matches
                    if other.get("Id")
                }
            )
            collision_details.append(f"# {label}: {token}")
            if match_names:
                collision_details.append(f"# Coincide con: {', '.join(match_names)}")

        if not collision_details:
            continue

        _EMITTED_KEYS.add(dedupe_key)
        contact_name = DATA_STORE.resolve_contact_name(contact_id)
        block = "\n".join(
            [f"- {contact_name} ({contact_id})"]
            + [f"    {line}" for line in collision_details]
        )
        collision_blocks.append(block)

    if not collision_blocks:
        return

    steps = [
        f"Passo 1 — Ho analizzato l'account {account_name} ({account_id}).",
        "Passo 2 — Ho confrontato gli identificativi principali dei contatti.",
        "Passo 3 — Possibili duplicati trovati:",
        *collision_blocks,
    ]

    ALERT_SUMMARY.record(
        {
            "alert_type": "Identificativi contatto duplicati",
            "account_id": account_id,
            "account_name": account_name,
            "contact_id": "",
            "contact_name": "",
            "details": "\n".join(steps),
            "message": (
                "Sono stati rilevati contatti con identificativi coincidenti nello stesso account."
            ),
        }
    )
