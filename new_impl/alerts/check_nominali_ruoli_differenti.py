"""Allerta sui contatti con stesso nominativo ma ruoli differenti."""

from __future__ import annotations

from typing import Dict, List, Tuple

from ..alert_summary import AlertSummaryStore
from ..data_store import AccountContext, DATA_STORE
from ..logbook import log_loop_event
from .common import iter_contacts, normalise_name

# Nessuno stato persistente necessario, ma manteniamo la firma coerente

def reset_state() -> None:  # pragma: no cover - funzione intenzionalmente vuota
    return None


def run(account_context: AccountContext, *, summary: AlertSummaryStore) -> None:
    """Cerca omonimie con ruoli discordanti sullo stesso account."""

    account_id = account_context.account_id
    account_name = DATA_STORE.resolve_account_name(account_id)

    # Passo 1: costruisco un indice per nome normalizzato.
    buckets: Dict[str, List[Tuple[str, List[str]]]] = {}
    for contact, roles in iter_contacts(account_context):
        name_token = normalise_name(contact)
        if not name_token:
            log_loop_event(
                f"[{account_id}] Contatto {contact.get('Id', 'sconosciuto')} senza nominativo, escluso dal controllo ruoli."
            )
            continue
        buckets.setdefault(name_token, []).append((contact["Id"], roles))

    # Passo 2: analizzo ogni gruppo alla ricerca di ruoli incoerenti.
    for name_token, entries in buckets.items():
        if len(entries) < 2:
            log_loop_event(
                f"[{account_id}] Solo un contatto con nominativo '{name_token}', nessun confronto necessario."
            )
            continue

        normalised_role_sets = {tuple(sorted(role.lower() for role in roles)) for _cid, roles in entries}
        if len(normalised_role_sets) <= 1:
            log_loop_event(
                f"[{account_id}] Nominativo '{name_token}' con ruoli omogenei, nessuna allerta."
            )
            continue

        contact_ids = [cid for cid, _ in entries]
        contact_names = [DATA_STORE.resolve_contact_name(cid) for cid in contact_ids]
        roles_by_contact = [", ".join(roles) or "Nessun ruolo" for _, roles in entries]

        details = "; ".join(
            f"{name} ➜ {roles}" for name, roles in zip(contact_names, roles_by_contact, strict=False)
        )
        message_lines = []
        for name, roles in zip(contact_names, roles_by_contact, strict=False):
            message_lines.append(f"    - {name}: {roles}")
        message = "\n".join(message_lines)

        summary.record(
            {
                "alert_type": "Omonimia con ruoli differenti",
                "account_id": account_id,
                "account_name": account_name,
                "contact_id": ", ".join(contact_ids),
                "contact_name": ", ".join(contact_names),
                "details": details,
                "message": message,
                "contact_roles": "; ".join(roles_by_contact),
                "issue_category": "Coerenza",
                "data_focus": "Ruoli",
            }
        )
