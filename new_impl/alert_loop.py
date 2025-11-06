"""Alert loop orchestrator for the alternate application."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from .alert_summary import ALERT_SUMMARY, AlertSummaryStore
from .alerts import ALERT_MODULES
from .data_store import DATA_STORE, SalesforceRelationshipStore


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
        for module in ALERT_MODULES:
            module.reset_state()

        account_counter = 0
        for account_counter, account_id in enumerate(self._iter_targets(account_ids), start=1):
            if account_counter <= 3 or account_counter % 10 == 0:
                print(f"[new_impl] Analisi dell'account {account_id}")
            context = self.store.describe_account(account_id)
            for module in ALERT_MODULES:
                module.run(context)

        print(f"[new_impl] Ciclo avvisi completato su {account_counter} account")
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
