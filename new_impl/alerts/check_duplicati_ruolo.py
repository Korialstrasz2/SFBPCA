"""Allerta sui contatti duplicati con stesso ruolo e identificativo."""

from __future__ import annotations

from typing import Dict, List, Tuple

from ..alert_summary import AlertSummaryStore
from ..data_store import AccountContext, DATA_STORE
from .common import iter_contacts, normalise_name, normalise_text

# Cache per evitare di emettere la stessa allerta più volte
_EMITTED: set[Tuple[str, str, str, str]] = set()
# Mappa di supporto per ricordare la forma originale dei ruoli
_ROLE_LABELS: Dict[str, str] = {}


def reset_state() -> None:
    """Ripulisce lo stato condiviso tra le esecuzioni."""

    _EMITTED.clear()
    _ROLE_LABELS.clear()


def run(account_context: AccountContext, *, summary: AlertSummaryStore) -> None:
    """Cerca contatti con lo stesso ruolo, nome e identificativo."""

    account_id = account_context.account_id
    account_name = DATA_STORE.resolve_account_name(account_id)

    # Passo 1: raggruppo i contatti per ruolo, nome e identificativi fiscali.
    buckets: Dict[Tuple[str, str, str, str], List[str]] = {}
    for contact, roles in iter_contacts(account_context):
        contact_id = contact["Id"]
        name_token = normalise_name(contact)
        if not name_token:
            continue

        identifiers = [
            ("Codice fiscale", normalise_text(contact.get("FiscalCode__c"))),
            ("Partita IVA", normalise_text(contact.get("VATNumber__c"))),
        ]
        for role in roles:
            role_token = normalise_text(role)
            if not role_token:
                continue
            _ROLE_LABELS.setdefault(role_token, role)
            for label, token in identifiers:
                if not token:
                    continue
                key = (role_token, label, token, name_token)
                buckets.setdefault(key, []).append(contact_id)

    # Passo 2: individuo i gruppi con più di un contatto.
    for (role_token, label, token, name_token), contact_ids in buckets.items():
        unique_ids = list(dict.fromkeys(contact_ids))
        if len(unique_ids) < 2:
            continue

        cache_key = (account_id, role_token, label, token)
        if cache_key in _EMITTED:
            continue
        _EMITTED.add(cache_key)

        role_label = _ROLE_LABELS.get(role_token, role_token)
        contact_names = [DATA_STORE.resolve_contact_name(cid) for cid in unique_ids]

        # Passo 3: costruisco messaggi di dettaglio in italiano.
        details = (
            f"Ruolo '{role_label}' con {label.lower()} '{token}' associato a {len(contact_names)} contatti "
            f"con stesso nominativo."
        )
        message_lines = [
        ]
        message_lines.extend([f"    - {name}" for name in contact_names])
        message = ""

        summary.record(
            {
                "alert_type": "Duplicati per ruolo e identificativo",
                "account_id": account_id,
                "account_name": account_name,
                "contact_id": ", ".join(unique_ids),
                "contact_name": ", ".join(contact_names),
                "details": details,
                "message": message,
                "contact_roles": role_label,
                "issue_category": "Duplicati",
                "data_focus": label,
            }
        )
