"""Allerta sulla coerenza dei numeri di telefono tra Contact e ContactPointPhone."""

from __future__ import annotations

from typing import List

from ..alert_summary import AlertSummaryStore
from ..data_store import AccountContext, DATA_STORE
from .common import iter_contacts, normalise_phone


def reset_state() -> None:  # pragma: no cover - nessuno stato globale necessario
    return None


def run(account_context: AccountContext, *, summary: AlertSummaryStore) -> None:
    """Confronta i numeri di telefono dei contatti con i ContactPointPhone collegati."""

    account_id = account_context.account_id
    account_name = DATA_STORE.resolve_account_name(account_id)

    for contact, roles in iter_contacts(account_context):
        contact_id = contact["Id"]
        contact_name = DATA_STORE.resolve_contact_name(contact_id)

        # Passo 1: normalizzo i numeri presenti sul contatto.
        numbers_on_contact = [
            ("Telefono fisso", contact.get("Phone")),
            ("Telefono mobile", contact.get("MobilePhone")),
        ]
        normalised_contact_numbers = {}
        for label, value in numbers_on_contact:
            normalised = normalise_phone(value)
            if normalised:
                normalised_contact_numbers[label] = normalised

        # Passo 2: recupero i ContactPointPhone associati via Individual.
        contact_points = DATA_STORE.get_contact_points_for_contact(contact_id)["phones"]
        normalised_point_numbers: List[str] = []
        for point in contact_points:
            normalised = normalise_phone(point.get("TelephoneNumber"))
            if normalised:
                normalised_point_numbers.append(normalised)

        contact_values: List[str] = [value for value in normalised_contact_numbers.values() if value]
        point_values: List[str] = [value for value in normalised_point_numbers if value]

        if not contact_values and not point_values:
            continue

        if contact_values and not point_values:
            details = "Numeri presenti sul contatto ma assenti su ContactPointPhone."
        elif point_values and not contact_values:
            details = "ContactPointPhone valorizzati ma nessun numero sul contatto."
        else:
            has_match = any(value in point_values for value in contact_values)
            if has_match:
                continue
            details = "Numeri presenti ma non coincidono tra Contact e ContactPointPhone."

        message_lines = []
        if normalised_contact_numbers:
            message_lines.append(
                "Numeri sul contatto: "
                + ", ".join(f"{label}={value}" for label, value in normalised_contact_numbers.items())
            )
        else:
            message_lines.append("Nessun numero memorizzato sul contatto.")
        if point_values:
            message_lines.append(
                "Numeri su ContactPointPhone: " + ", ".join(point_values)
            )
        else:
            message_lines.append("Nessun ContactPointPhone con numero valorizzato.")
        message = "\n".join(message_lines)

        summary.record(
            {
                "alert_type": "Telefono incoerente",
                "account_id": account_id,
                "account_name": account_name,
                "contact_id": contact_id,
                "contact_name": contact_name,
                "details": details,
                "message": message,
                "contact_roles": ", ".join(roles) or "Non indicato",
                "issue_category": "Coerenza",
                "data_focus": "Telefono",
            }
        )
