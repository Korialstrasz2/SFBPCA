from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

from airflow_app.services.context import AirflowRuntimeContext

logger = logging.getLogger(__name__)


PLACEHOLDER_MESSAGE = (
    "STILL TO BE IMPLEMENTED: Review the proposed contact reassignments and "
    "apply changes in Salesforce once the automation is available."
)


def build_reassignment_catalog(
    context: AirflowRuntimeContext, role: Optional[str] = None
) -> Dict[str, object]:
    store = context.load_data_store()
    if role:
        contacts = store.get_contacts_with_role(role)
    else:
        contacts = []
        for contact_id, contact in store.contacts.items():
            entry = contact.copy()
            relation = next(
                (item for item in store.account_contact_relations if item.get("ContactId") == contact_id),
                None,
            )
            if relation:
                entry["_relation"] = relation
            contacts.append(entry)

    catalog: List[Dict[str, object]] = []
    for contact in contacts:
        contact_role = None
        relation = contact.get("_relation")
        if isinstance(relation, dict):
            contact_role = relation.get("Roles")
        else:
            relation = next(
                (item for item in store.account_contact_relations if item.get("ContactId") == contact.get("Id")),
                None,
            )
            if relation:
                contact_role = relation.get("Roles")
        candidates = store.find_matching_accounts_for_contact(contact, required_marking="d1")
        catalog.append(
            {
                "contact_id": contact.get("Id"),
                "contact_name": f"{contact.get('FirstName', '')} {contact.get('LastName', '')}".strip(),
                "current_account_id": relation.get("AccountId") if relation else None,
                "current_role": contact_role,
                "candidate_accounts": [
                    {
                        "id": account.get("Id"),
                        "name": account.get("Name"),
                        "customer_marking": account.get("CustomerMarking__c"),
                    }
                    for account in candidates
                ],
            }
        )

    artifact_path = context.config.base_dir / "artifacts" / "pending_data_changes.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"status": PLACEHOLDER_MESSAGE, "role": role, "contacts": catalog}
    with artifact_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")

    context.save_data_store(store)
    logger.info(
        "Prepared data-change placeholder with %d contact entries for role '%s'",
        len(catalog),
        role,
    )
    return payload


__all__ = ["build_reassignment_catalog", "PLACEHOLDER_MESSAGE"]
