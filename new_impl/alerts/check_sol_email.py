"""Allerta sui Referenti SOL-APP senza email SOL correttamente valorizzata."""

from __future__ import annotations

from typing import List

from ..alert_summary import AlertSummaryStore
from ..data_store import AccountContext, DATA_STORE
from .common import has_referente_sol_role, iter_contacts, normalise_text

TARGET_TYPE = normalise_text("E-mail SOL")


def reset_state() -> None:  # pragma: no cover - nessun dato persistente
    return None


def run(account_context: AccountContext, *, summary: AlertSummaryStore) -> None:
    """Verifica che i Referenti SOL dispongano di un ContactPointEmail dedicato."""

    account_id = account_context.account_id
    account_name = DATA_STORE.resolve_account_name(account_id)

    for contact, roles in iter_contacts(account_context, include_referente_sol=True):
        if not has_referente_sol_role(roles):
            continue

        contact_id = contact["Id"]
        contact_name = DATA_STORE.resolve_contact_name(contact_id)
        contact_points = DATA_STORE.get_contact_points_for_contact(contact_id)["emails"]

        sol_candidates: List[dict] = [
            point for point in contact_points if normalise_text(point.get("Type__c")) == TARGET_TYPE
        ]
        valid_points = [point for point in sol_candidates if (point.get("EmailAddress") or "").strip()]

        if valid_points:
            continue

        types_found = [normalise_text(point.get("Type__c")) or "(vuoto)" for point in contact_points]
        details = (
            "ContactPointEmail assente o senza tipo 'E-mail SOL' con indirizzo valorizzato. "
            f"Tipologie trovate: {', '.join(types_found) if types_found else 'nessuna'}."
        )

        message_lines = [
            "Passo 1 ➜ Ho isolato i contatti con ruolo Referente SOL-APP sull'account.",
            "Passo 2 ➜ Ho letto tutti i ContactPointEmail collegati all'Individual associato.",
            "Passo 3 ➜ Nessun record di tipo 'E-mail SOL' presenta un indirizzo compilato.",
            "Suggerimento: crea o completa il ContactPointEmail con tipo 'E-mail SOL' per il referente.",
        ]
        message = "\n".join(message_lines)

        summary.record(
            {
                "alert_type": "Referente SOL senza email SOL",
                "account_id": account_id,
                "account_name": account_name,
                "contact_id": contact_id,
                "contact_name": contact_name,
                "details": details,
                "message": message,
                "contact_roles": ", ".join(roles) or "Referente SOL-APP",
                "issue_category": "Compliance",
                "data_focus": "Email SOL",
            }
        )
