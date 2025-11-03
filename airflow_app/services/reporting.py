from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, List

from airflow_app.services.context import AirflowRuntimeContext

logger = logging.getLogger(__name__)


def _top_accounts(store, limit: int = 10) -> List[Dict[str, object]]:
    pairs = []
    for account_id, account in store.accounts.items():
        contacts = store.get_contacts_for_account(account_id)
        pairs.append(
            {
                "account_id": account_id,
                "account_name": account.get("Name"),
                "contact_count": len(contacts),
            }
        )
    pairs.sort(key=lambda item: item["contact_count"], reverse=True)
    return pairs[:limit]


def _contacts_missing_roles(store) -> List[Dict[str, object]]:
    missing: List[Dict[str, object]] = []
    for relation in store.account_contact_relations:
        roles = (relation.get("Roles") or "").strip()
        if roles:
            continue
        contact = store.contacts.get(relation.get("ContactId"), {})
        account = store.accounts.get(relation.get("AccountId"), {})
        missing.append(
            {
                "account_id": relation.get("AccountId"),
                "account_name": account.get("Name"),
                "contact_id": relation.get("ContactId"),
                "contact_name": f"{contact.get('FirstName', '')} {contact.get('LastName', '')}".strip(),
            }
        )
    return missing


def generate_operational_report(context: AirflowRuntimeContext) -> Dict[str, object]:
    store = context.load_data_store()
    summary = {
        "accounts": len(store.accounts),
        "contacts": len(store.contacts),
        "individuals": len(store.individuals),
        "account_contact_relations": len(store.account_contact_relations),
        "contact_point_phones": len(store.contact_point_phones),
        "contact_point_emails": len(store.contact_point_emails),
    }
    top_accounts = _top_accounts(store)
    missing_roles = _contacts_missing_roles(store)
    marked_accounts = store.find_accounts_with_customer_marking("d1")

    generated_at = datetime.utcnow().isoformat()
    report = {
        "generated_at": generated_at,
        "summary": summary,
        "top_accounts": top_accounts,
        "missing_roles": missing_roles,
        "customer_marking_d1": [
            {"id": account.get("Id"), "name": account.get("Name")} for account in marked_accounts
        ],
    }

    artifacts_dir = context.config.reports_dir
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    json_path = context.config.reports_index_path
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    markdown_path = artifacts_dir / f"report_{generated_at.replace(':', '').replace('-', '')}.md"
    lines = [
        f"# Salesforce Relationship Report",
        "",
        f"Generated at: {generated_at}",
        "",
        "## Summary",
    ]
    for key, value in summary.items():
        lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
    lines.extend(
        [
            "",
            "## Top Accounts by Contact Count",
        ]
    )
    if top_accounts:
        for account in top_accounts:
            lines.append(
                f"- {account['account_name']} ({account['account_id']}): {account['contact_count']} contacts"
            )
    else:
        lines.append("- No accounts available")

    lines.extend(["", "## Contacts Missing Roles"])
    if missing_roles:
        for item in missing_roles:
            lines.append(
                f"- {item['contact_name']} ({item['contact_id']}) on {item['account_name']} ({item['account_id']})"
            )
    else:
        lines.append("- All account-contact relations include roles")

    lines.extend(["", "## Accounts with CustomerMarking__c = D1"])
    if marked_accounts:
        for account in marked_accounts:
            lines.append(f"- {account.get('Name')} ({account.get('Id')})")
    else:
        lines.append("- None")

    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    context.save_data_store(store)
    logger.info("Generated operational report with %d accounts", len(store.accounts))
    return report


__all__ = ["generate_operational_report"]
