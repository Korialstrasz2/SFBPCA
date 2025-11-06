"""Alert loop orchestrator for the alternate application."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

import alert_contact_doppio
import alert_ruolo_doppio
from new_alert_summary import ALERT_SUMMARY, AlertSummaryStore
from new_data_structure_and_store import DATA_STORE, SalesforceRelationshipStore


class AlertLoopRunner:
    """Runs the configured alert modules across imported data."""

    def __init__(
        self,
        store: SalesforceRelationshipStore | None = None,
        summary: AlertSummaryStore | None = None,
    ) -> None:
        self.store = store or DATA_STORE
        self.summary = summary or ALERT_SUMMARY

    def run(self, account_ids: Optional[Sequence[str]] = None) -> Dict[str, List[dict]]:
        """Execute the alert loop and return the captured alerts."""

        self.summary.reset()
        alert_contact_doppio.reset_state()
        alert_ruolo_doppio.reset_state()

        for account_id in self._iter_targets(account_ids):
            context = self.store.describe_account(account_id)
            for contact in context.contacts:
                alert_contact_doppio.inspect_contact(context, contact)
                alert_ruolo_doppio.inspect_contact(context, contact)

        return {
            "details": self.summary.all_alerts(),
            "summary": self.summary.summary_rows(),
        }

    def _iter_targets(self, account_ids: Optional[Sequence[str]]) -> Iterable[str]:
        if account_ids:
            seen = set()
            for account_id in account_ids:
                if account_id in self.store.accounts and account_id not in seen:
                    seen.add(account_id)
                    yield account_id
            return

        for account_id in self.store.iter_account_ids():
            yield account_id


ALERT_LOOP = AlertLoopRunner()
