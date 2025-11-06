"""Alert logic for detecting duplicate role assignments within an account."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set

from ..alert_summary import ALERT_SUMMARY
from ..data_store import AccountContext, DATA_STORE


_EMITTED_KEYS: Set[str] = set()


def _normalise(value: str | None) -> str:
    return (value or "").strip().lower()


def reset_state() -> None:
    _EMITTED_KEYS.clear()


def run(account_context: AccountContext) -> None:
    """Evaluate duplicate role assignments for the account."""

    role_to_contacts: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for contact in account_context.contacts:
        relation = contact.get("_relation") or {}
        role_label = relation.get("Roles")
        if not role_label:
            continue
        role_key = _normalise(role_label)
        if not role_key:
            continue
        role_to_contacts[role_key].append(contact)

    for role_key, contacts in role_to_contacts.items():
        if len(contacts) < 2:
            continue
        _record_role_alert(account_context, role_key, contacts)


def _record_role_alert(
    account_context: AccountContext,
    role_key: str,
    contacts: List[Dict[str, str]],
) -> None:
    account_id = account_context.account_id
    dedupe_key = f"role_doppio::{account_id}::{role_key}"
    if dedupe_key in _EMITTED_KEYS:
        return
    _EMITTED_KEYS.add(dedupe_key)

    role_label = (contacts[0].get("_relation") or {}).get("Roles") or role_key
    account_name = DATA_STORE.resolve_account_name(account_id)
    involved_contacts = [DATA_STORE.resolve_contact_name(contact.get("Id")) for contact in contacts]

    steps = [
        "Passo 1: ho esaminato i ruoli assegnati ai contatti dell'account.",
        "Passo 2: ho riscontrato lo stesso ruolo assegnato a più contatti:",
    ]
    for name in sorted(set(involved_contacts)):
        steps.append(f"  - {name}")
    steps.append(
        "Commento: verifica se il ruolo '"
        + role_label
        + "' deve essere unico e allinea le assegnazioni in Salesforce."
    )

    ALERT_SUMMARY.record(
        {
            "alert_type": "Ruolo assegnato più volte",
            "account_id": account_id,
            "account_name": account_name,
            "contact_id": contacts[0].get("Id"),
            "contact_name": DATA_STORE.resolve_contact_name(contacts[0].get("Id")),
            "details": "\n".join(steps),
            "message": (
                f"Il ruolo '{role_label}' è presente più volte per l'account {account_name}."
            ),
            "steps": steps,
        }
    )
