"""Reusable business logic executed by Airflow tasks."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from app.services.alert_engine import AlertEngine
from app.services.alert_definition_store import AlertDefinitionStore
from app.services.importer import CSVImporter
from airflow_app.config import AirflowAppConfig
from airflow_app.runtime import (
    build_data_store,
    load_snapshot,
    save_snapshot,
    timestamped_subdirectory,
)

EXPECTED_ENTITIES: Tuple[str, ...] = tuple(CSVImporter.ENTITY_FIELDS.keys())


def extract_csv_records(config: AirflowAppConfig) -> Dict[str, List[dict]]:
    """Read CSV files from the configured source directory."""

    records: Dict[str, List[dict]] = {}
    for entity in EXPECTED_ENTITIES:
        file_path = config.source_dir / f"{entity}.csv"
        if not file_path.exists():
            records[entity] = []
            continue
        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            entity_records: List[dict] = []
            for row in reader:
                entity_records.append({key.strip(): (value.strip() if isinstance(value, str) else value) for key, value in row.items()})
            records[entity] = entity_records
    return records


def normalise_records(records: Dict[str, List[dict]], config: AirflowAppConfig) -> Path:
    """Build and persist a DataStore snapshot for downstream tasks."""

    store = build_data_store(records)
    snapshot_path = save_snapshot(store, config.data_snapshot_path)
    return snapshot_path


def rebuild_alert_definitions(config: AirflowAppConfig) -> List[dict]:
    """Load alert definitions so the Airflow DAG can display them."""

    store = AlertDefinitionStore(Path(config.alert_definition_path))
    return store.load_alerts()


def generate_alerts(snapshot_path: Path, config: AirflowAppConfig) -> Path:
    """Run the alert engine and persist the generated alerts to disk."""

    store = load_snapshot(snapshot_path)
    alert_store = AlertDefinitionStore(Path(config.alert_definition_path))
    engine = AlertEngine(store, alert_store)
    alerts = engine.build_alerts()
    output_path = config.reports_dir / "alerts.json"
    output_path.write_text(json.dumps({"alerts": alerts}, indent=2), encoding="utf-8")
    return output_path


def build_account_reports(snapshot_path: Path, config: AirflowAppConfig) -> Path:
    """Produce analytical reports summarising account and contact coverage."""

    store = load_snapshot(snapshot_path)
    report: Dict[str, Dict[str, int]] = {}
    for account_id, account in store.accounts.items():
        contacts = store.get_contacts_for_account(account_id)
        unique_roles = {relation.get("Roles", "") for relation in (contact.get("_relation") for contact in contacts) if relation}
        report[account_id] = {
            "account_name": account.get("Name", ""),
            "customer_marking": account.get("CustomerMarking__c", ""),
            "contact_count": len(contacts),
            "role_count": len(unique_roles),
            "phone_count": sum(len(store.get_phones_for_contact(contact.get("Id", ""))) for contact in contacts),
            "email_count": sum(len(store.get_emails_for_contact(contact.get("Id", ""))) for contact in contacts),
        }
    output_path = config.reports_dir / "account_report.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output_path


def backup_runtime_artifacts(snapshot_path: Path, config: AirflowAppConfig, extra_files: Iterable[Path]) -> Path:
    """Copy generated artifacts into a timestamped backup folder."""

    backup_root = timestamped_subdirectory(config.backup_dir, prefix="backup")
    shutil.copy2(snapshot_path, backup_root / Path(snapshot_path.name))
    for extra_file in extra_files:
        if extra_file.exists():
            shutil.copy2(extra_file, backup_root / extra_file.name)
    return backup_root


def build_data_change_candidates(snapshot_path: Path, config: AirflowAppConfig) -> Path:
    """Create a placeholder dataset for upcoming data change tooling."""

    store = load_snapshot(snapshot_path)

    accounts_by_key: Dict[Tuple[str, str], List[dict]] = {}
    for account in store.accounts.values():
        key = (account.get("Name", "").strip().lower(), account.get("CustomerMarking__c", ""))
        accounts_by_key.setdefault(key, []).append(account)

    candidates: List[dict] = []
    for contact in store.contacts.values():
        relation_accounts = [rel.get("AccountId") for rel in store.account_contact_relations if rel.get("ContactId") == contact.get("Id")]
        roles = [rel.get("Roles") for rel in store.account_contact_relations if rel.get("ContactId") == contact.get("Id")]
        first = (contact.get("FirstName") or "").strip().lower()
        last = (contact.get("LastName") or "").strip().lower()
        for account in store.accounts.values():
            if account.get("Id") not in relation_accounts:
                continue
            key = (account.get("Name", "").strip().lower(), "D1")
            possible_targets = accounts_by_key.get(key, [])
            for target in possible_targets:
                if target.get("Id") == account.get("Id"):
                    continue
                if first and last:
                    matching_contacts = [candidate for candidate in store.contacts.values() if (candidate.get("FirstName") or "").strip().lower() == first and (candidate.get("LastName") or "").strip().lower() == last]
                else:
                    matching_contacts = []
                candidates.append(
                    {
                        "contact_id": contact.get("Id"),
                        "contact_name": f"{contact.get('FirstName', '')} {contact.get('LastName', '')}".strip(),
                        "current_account_id": account.get("Id"),
                        "current_account_name": account.get("Name"),
                        "suggested_account_id": target.get("Id"),
                        "suggested_account_name": target.get("Name"),
                        "roles": roles,
                        "customer_marking": target.get("CustomerMarking__c"),
                        "matching_contacts": [match.get("Id") for match in matching_contacts],
                        "status": "STILL TO BE IMPLEMENTED",
                    }
                )
    output_path = config.reports_dir / "data_change_candidates.json"
    output_path.write_text(json.dumps({"candidates": candidates}, indent=2), encoding="utf-8")
    return output_path


def export_runtime_manifest(snapshot_path: Path, report_paths: Iterable[Path], config: AirflowAppConfig) -> Path:
    manifest_path = config.reports_dir / "manifest.json"
    manifest = {
        "snapshot": str(snapshot_path),
        "reports": [str(path) for path in report_paths],
        "config": config.as_dict(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path
