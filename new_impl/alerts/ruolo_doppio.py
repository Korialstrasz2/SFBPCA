"""Controllo sui ruoli duplicati per account."""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from ..alert_summary import AlertSummaryStore
from ..data_store import AccountContext, DATA_STORE

_EMITTED_KEYS: Set[Tuple[str, str]] = set()


def _normalise(value: str | None) -> str:
    return (value or "").strip().lower()


def reset_state() -> None:
    _EMITTED_KEYS.clear()


def run(account_context: AccountContext, *, summary: AlertSummaryStore) -> None:
    account_id = account_context.account_id
    account_name = DATA_STORE.resolve_account_name(account_id)

    roles: Dict[str, List[str]] = {}
    labels: Dict[str, str] = {}
    for contact in account_context.contacts:
        relation = contact.get("_relation") or {}
        role_label = relation.get("Roles")
        role_key = _normalise(role_label)
        if not role_key:
            continue
        contact_id = contact.get("Id")
        if not contact_id:
            continue
        roles.setdefault(role_key, []).append(contact_id)
        labels[role_key] = role_label or role_key

    for role_key, contact_ids in roles.items():
        unique_ids = list(dict.fromkeys(contact_ids))
        if len(unique_ids) < 2:
            continue

        dedupe_key = (account_id, role_key)
        if dedupe_key in _EMITTED_KEYS:
            continue
        _EMITTED_KEYS.add(dedupe_key)

        contact_names = [DATA_STORE.resolve_contact_name(cid) for cid in unique_ids]
        role_label = labels.get(role_key, role_key)
        details = (
            f"Ruolo '{role_label}' assegnato a {len(contact_names)} contatti: "
            f"{', '.join(contact_names)}"
        )
        message_lines = [
            "Passo 1 ➜ Ho raccolto i ruoli associati ai contatti dell'account.",
            f"Passo 2 ➜ Il ruolo '{role_label}' compare più volte.",
            "Passo 3 ➜ Controlla i contatti coinvolti e assegna ruoli distinti se necessario:",
        ]
        message_lines.extend([f"    - {name}" for name in contact_names])
        message_lines.append("// Nota: una chiara attribuzione dei ruoli evita sovrapposizioni operative.")
        message = "\n".join(message_lines)

        summary.record(
            {
                "alert_type": "Ruoli duplicati per account",
                "account_id": account_id,
                "account_name": account_name,
                "contact_id": ", ".join(unique_ids),
                "contact_name": ", ".join(contact_names),
                "details": details,
                "message": message,
            }
        )
