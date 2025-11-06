"""Alert loop orchestrator for the modern application."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from . import alerts
from .alert_summary import ALERT_SUMMARY, AlertSummaryStore
from .data_store import DATA_STORE, SalesforceRelationshipStore

ALERT_MODULES = [
    alerts.contact_doppio,
    alerts.ruolo_doppio,
]


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

        print("[alert] Avvio del loop avvisi")
        self.summary.reset()
        for module in ALERT_MODULES:
            reset = getattr(module, "reset_state", None)
            if callable(reset):
                reset()

        for account_id in self._iter_targets(account_ids):
            print(f"[alert] Analisi account {account_id}")
            context = self.store.describe_account(account_id)
            for module in ALERT_MODULES:
                module.run(context)

        alerts = self.summary.all_alerts()
        print(f"[alert] Loop completato: {len(alerts)} avvisi generati")
        return {
            "details": alerts,
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
