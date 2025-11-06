"""Controllo dei contatti con identificativi duplicati sullo stesso account."""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from ..alert_summary import AlertSummaryStore
from ..data_store import AccountContext, DATA_STORE

_IDENTIFIERS: Dict[str, str] = {
    "Codice fiscale": "FiscalCode__c",
    "Partita IVA": "VATNumber__c",
    "Email": "Email",
}

_EMITTED_KEYS: Set[Tuple[str, str, str]] = set()


def _normalise(value: str | None) -> str:
    return (value or "").strip().lower()


def reset_state() -> None:
    """Ripulisce la cache per evitare duplicati tra le esecuzioni."""

    _EMITTED_KEYS.clear()


def run(account_context: AccountContext, *, summary: AlertSummaryStore) -> None:
    account_id = account_context.account_id
    account_name = DATA_STORE.resolve_account_name(account_id)

    collisions: Dict[Tuple[str, str], List[str]] = {}
    for contact in account_context.contacts:
        contact_id = contact.get("Id")
        if not contact_id:
            continue
        for label, field in _IDENTIFIERS.items():
            token = _normalise(contact.get(field))
            if not token:
                continue
            key = (label, token)
            collisions.setdefault(key, []).append(contact_id)

    for (label, token), contact_ids in collisions.items():
        unique_ids = list(dict.fromkeys(contact_ids))
        if len(unique_ids) < 2:
            continue

        dedupe_key = (account_id, label, token)
        if dedupe_key in _EMITTED_KEYS:
            continue
        _EMITTED_KEYS.add(dedupe_key)

        contact_names = [DATA_STORE.resolve_contact_name(cid) for cid in unique_ids]
        details = (
            f"Identificativo '{token}' ({label}) ripetuto in {len(contact_names)} contatti: "
            f"{', '.join(contact_names)}"
        )
        message_lines = [
            "Passo 1 ➜ Ho recuperato tutti i contatti collegati all'account.",
            "Passo 2 ➜ Ho confrontato gli identificativi chiave (codice fiscale, partita IVA, email).",
            f"Passo 3 ➜ Ho trovato il valore '{token}' per {label.lower()} associato ai seguenti contatti:",
        ]
        message_lines.extend([f"    - {name}" for name in contact_names])
        message_lines.append("// Suggerimento: uniforma i dati duplicati direttamente in Salesforce.")
        message = "\n".join(message_lines)

        summary.record(
            {
                "alert_type": "Contatti con identificativi duplicati",
                "account_id": account_id,
                "account_name": account_name,
                "contact_id": ", ".join(unique_ids),
                "contact_name": ", ".join(contact_names),
                "details": details,
                "message": message,
            }
        )
