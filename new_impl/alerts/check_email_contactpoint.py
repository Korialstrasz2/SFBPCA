"""Allerta sulla coerenza delle email tra Contact e ContactPointEmail."""

from __future__ import annotations

from typing import List

from ..alert_summary import AlertSummaryStore
from ..data_store import AccountContext, DATA_STORE
from ..logbook import log_loop_event
from .common import iter_contacts, normalise_text


def _normalise_email(value: str | None) -> str:
    return normalise_text(value)


def reset_state() -> None:  # pragma: no cover - nessuno stato condiviso
    return None


def run(account_context: AccountContext, *, summary: AlertSummaryStore) -> None:
    """Allinea l'indirizzo email del contatto con i ContactPointEmail."""

    account_id = account_context.account_id
    account_name = DATA_STORE.resolve_account_name(account_id)

    for contact, roles in iter_contacts(account_context):
        contact_id = contact["Id"]
        contact_name = DATA_STORE.resolve_contact_name(contact_id)

        email_on_contact = _normalise_email(contact.get("Email"))
        email_on_contact = '' if email_on_contact.lower() == 'TOOL-VUOTO'.lower() else email_on_contact
        contact_points = DATA_STORE.get_contact_points_for_contact(contact_id)["emails"]
        emails_on_points: List[str] = [
            _normalise_email(point.get("EmailAddress"))
            for point in contact_points
            if _normalise_email(point.get("EmailAddress"))
        ]

        if not email_on_contact and not emails_on_points:
            log_loop_event(
                f"[{account_id}] Nessuna email trovata per contatto {contact_id}, salto controllo."
            )
            continue

        if email_on_contact and not emails_on_points:
            details = "Email presente sul contatto ma non sui ContactPointEmail."
        elif emails_on_points and not email_on_contact:
            details = "ContactPointEmail valorizzati ma il campo Email del contatto è vuoto."
        else:
            if email_on_contact in emails_on_points:
                log_loop_event(
                    f"[{account_id}] Email coincidenti per contatto {contact_id}, nessuna allerta."
                )
                continue
            details = "Email presenti ma non coincidono tra Contact e ContactPointEmail."

        message_lines = [
            f"Email sul contatto: {email_on_contact or 'assenza'}.",
        ]
        if emails_on_points:
            message_lines.append(
                "Email su ContactPointEmail: " + ", ".join(emails_on_points)
            )
        else:
            message_lines.append("Nessun ContactPointEmail valorizzato.")
        message = "\n".join(message_lines)

        summary.record(
            {
                "alert_type": "Email incoerente",
                "account_id": account_id,
                "account_name": account_name,
                "contact_id": contact_id,
                "contact_name": contact_name,
                "details": details,
                "message": message,
                "contact_roles": ", ".join(roles) or "Non indicato",
                "issue_category": "Coerenza",
                "data_focus": "Email",
            }
        )
