"""Funzioni di supporto condivise dagli script di allerta."""

from __future__ import annotations

from typing import Dict, Iterable, Iterator, List, Sequence, Tuple

from ..data_store import AccountContext, DATA_STORE
from ..logbook import log_loop_event

# Costante per riconoscere il ruolo da escludere dai check standard.
REFERENTE_SOL_ROLE = "referente sol-app"


def normalise_text(value: str | None) -> str:
    """Normalizza una stringa per confronti case-insensitive."""

    return (value or "TOOL-VUOTO").strip().lower()


def normalise_name(contact: Dict[str, str]) -> str:
    """Restituisce nome e cognome normalizzati del contatto."""

    parts = [contact.get("FirstName"), contact.get("LastName")]
    return " ".join(part.strip() for part in parts if part and part.strip()).lower()


def normalise_phone(value: str | None) -> str:
    """Riduce un numero di telefono ai soli caratteri numerici per confronti."""

    digits = [ch for ch in (value or "") if ch.isdigit()]
    return "".join(digits)


def extract_roles(contact: Dict[str, str]) -> List[str]:
    """Estrae i ruoli associati al contatto dalla relazione AccountContact."""

    relation = contact.get("_relation") or {}
    raw_roles = relation.get("Roles") or ""
    roles = [role.strip() for role in raw_roles.split(";") if role.strip()]
    return roles


def has_referente_sol_role(roles: Sequence[str]) -> bool:
    """Indica se nei ruoli è presente il profilo Referente SOL-APP."""

    return any(normalise_text(role) == REFERENTE_SOL_ROLE for role in roles)


def iter_contacts(
    account_context: AccountContext,
    *,
    include_referente_sol: bool = False,
) -> Iterator[Tuple[Dict[str, str], List[str]]]:
    """Restituisce i contatti di un account filtrando eventuali Referenti SOL."""

    for contact in account_context.contacts:
        contact_id = contact.get("Id")
        if not contact_id:
            log_loop_event(
                f"Contatto senza Id in account {account_context.account_id}, ignorato."
            )
            continue

        roles = extract_roles(contact)
        if not include_referente_sol and has_referente_sol_role(roles):
            log_loop_event(
                f"Contatto {contact_id} ignorato per ruolo Referente SOL su account "
                f"{account_context.account_id}."
            )
            continue

        yield contact, roles


def resolve_contact_name(contact_id: str) -> str:
    """Ottiene il nome completo del contatto per i messaggi di sintesi."""

    return DATA_STORE.resolve_contact_name(contact_id)


def format_roles(roles: Iterable[str]) -> str:
    """Converte la lista ruoli in stringa leggibile."""

    unique: List[str] = []
    for role in roles:
        if role and role not in unique:
            unique.append(role)
    return ", ".join(unique)
