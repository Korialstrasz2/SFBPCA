"""Allerta sui contatti privi di ruoli attivi nella relazione account."""

from __future__ import annotations

from ..alert_summary import AlertSummaryStore
from ..data_store import AccountContext, DATA_STORE
from .common import iter_contacts

# Non serve stato condiviso, ma manteniamo l'interfaccia coerente

def reset_state() -> None:  # pragma: no cover - funzione vuota
    """Funzione presente per compatibilità con il ciclo delle allerte."""

    return None


def run(account_context: AccountContext, *, summary: AlertSummaryStore) -> None:
    """Verifica che ogni contatto abbia almeno un ruolo valorizzato."""

    account_id = account_context.account_id
    account_name = DATA_STORE.resolve_account_name(account_id)

    for contact, roles in iter_contacts(account_context):
        contact_id = contact["Id"]
        if roles:
            continue

        contact_name = DATA_STORE.resolve_contact_name(contact_id)
        # Passo 1: descrivo il problema per il riepilogo.
        details = "Contatto senza ruoli assegnati nella relazione AccountContact."
        message = "\n".join(
            [
                f"Il contatto {contact_name} non presenta ruoli associati.",
            ]
        )

        summary.record(
            {
                "alert_type": "Contatto senza ruolo",
                "account_id": account_id,
                "account_name": account_name,
                "contact_id": contact_id,
                "contact_name": contact_name,
                "details": details,
                "message": message,
                "contact_roles": "Nessuno",
                "issue_category": "Completezza",
                "data_focus": "Ruoli",
            }
        )
