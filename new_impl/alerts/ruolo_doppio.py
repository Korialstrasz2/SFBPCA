"""Avviso per la verifica di ruoli duplicati nello stesso account."""

from __future__ import annotations

from typing import Dict, List, Set

from ..alert_summary import ALERT_SUMMARY
from ..data_store import AccountContext, DATA_STORE


_EMITTED_KEYS: Set[str] = set()


def _normalise(value: str | None) -> str:
    return (value or "").strip().lower()


def reset_state() -> None:
    _EMITTED_KEYS.clear()


def run(account_context: AccountContext) -> None:
    account_id = account_context.account_id
    account_name = DATA_STORE.resolve_account_name(account_id)

    grouped_roles: Dict[str, Dict[str, List[str]]] = {}
    for contact in account_context.contacts:
        contact_id = contact.get("Id")
        if not contact_id:
            continue
        relation = contact.get("_relation") or {}
        role_label = relation.get("Roles")
        role_key = _normalise(role_label)
        if not role_key:
            continue
        bucket = grouped_roles.setdefault(
            role_key,
            {"label": role_label or "(ruolo senza nome)", "contacts": []},
        )
        bucket["contacts"].append(contact_id)

    issue_blocks: List[str] = []
    for role_key, payload in grouped_roles.items():
        contact_ids = payload["contacts"]
        if len(contact_ids) <= 1:
            continue
        dedupe_key = f"role_doppio::{account_id}::{role_key}"
        if dedupe_key in _EMITTED_KEYS:
            continue
        _EMITTED_KEYS.add(dedupe_key)

        contact_names = [DATA_STORE.resolve_contact_name(contact_id) for contact_id in contact_ids]
        details = [
            f"- Ruolo '{payload['label']}' in comune",
            f"    # Coinvolge: {', '.join(sorted(set(contact_names)))}",
            f"    # ID contatti: {', '.join(contact_ids)}",
        ]
        issue_blocks.append("\n".join(details))

    if not issue_blocks:
        return

    steps = [
        f"Passo 1 — Ho esaminato i ruoli collegati all'account {account_name} ({account_id}).",
        "Passo 2 — Ho cercato ruoli assegnati a più di un contatto.",
        "Passo 3 — Situazioni da rivedere:",
        *issue_blocks,
    ]

    ALERT_SUMMARY.record(
        {
            "alert_type": "Ruoli account duplicati",
            "account_id": account_id,
            "account_name": account_name,
            "contact_id": "",
            "contact_name": "",
            "details": "\n".join(steps),
            "message": "Sono presenti ruoli assegnati a più contatti nello stesso account.",
        }
    )
