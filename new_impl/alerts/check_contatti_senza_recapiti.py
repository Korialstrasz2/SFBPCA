"""Allerta sui contatti senza recapiti telefonici o email."""

from __future__ import annotations

from ..alert_summary import AlertSummaryStore
from ..data_store import AccountContext, DATA_STORE
from ..logbook import log_loop_event
from .common import iter_contacts


def reset_state() -> None:  # pragma: no cover - nessuno stato da ripulire
    """Compatibilità con l'interfaccia richiesta dall'orchestratore."""

    return None


def run(account_context: AccountContext, *, summary: AlertSummaryStore) -> None:
    """Assicura che ogni contatto abbia almeno un recapito utilizzabile."""

    account_id = account_context.account_id
    account_name = DATA_STORE.resolve_account_name(account_id)

    for contact, _roles in iter_contacts(account_context):
        contact_id = contact["Id"]
        has_phone_general = bool((contact.get("Phone") or "").strip())
        has_mobile = bool((contact.get("MobilePhone") or "").strip())
        has_email = bool((contact.get("Email") or "").strip())

        if has_mobile or has_email or has_phone_general:
            log_loop_event(
                f"[{account_id}] Contatto {contact_id} ha almeno un recapito, nessuna allerta recapiti."
            )
            continue

        contact_name = DATA_STORE.resolve_contact_name(contact_id)
        details = "Contatto privo di recapiti (telefono o email) compilati."
        message = "\n".join(
            [
                f"Il contatto {contact_name} non ha alcun recapito disponibile.",
            ]
        )

        summary.record(
            {
                "alert_type": "Contatto senza recapiti",
                "account_id": account_id,
                "account_name": account_name,
                "contact_id": contact_id,
                "contact_name": contact_name,
                "details": details,
                "message": message,
                "contact_roles": ", ".join(_roles) or "Non indicato",
                "issue_category": "Completezza",
                "data_focus": "Recapiti",
            }
        )
