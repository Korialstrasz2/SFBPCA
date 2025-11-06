"""Orchestratore delle allerte per la nuova applicazione."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from .alert_summary import ALERT_SUMMARY, AlertSummaryStore
from .alerts import (
    check_contatti_senza_recapiti,
    check_contatti_senza_ruolo,
    check_duplicati_ruolo,
    check_email_contactpoint,
    check_nominali_ruoli_differenti,
    check_sol_email,
    check_telefono_contactpoint,
)
from .data_store import DATA_STORE, SalesforceRelationshipStore

ALERT_MODULES = (
    check_duplicati_ruolo,
    check_contatti_senza_ruolo,
    check_contatti_senza_recapiti,
    check_nominali_ruoli_differenti,
    check_telefono_contactpoint,
    check_email_contactpoint,
    check_sol_email,
)


class AlertLoopRunner:
    """Esegue i moduli di allerta sugli account caricati."""

    def __init__(
        self,
        store: SalesforceRelationshipStore | None = None,
        summary: AlertSummaryStore | None = None,
    ) -> None:
        self.store = store or DATA_STORE
        self.summary = summary or ALERT_SUMMARY

    def run(self, account_ids: Optional[Sequence[str]] = None) -> Dict[str, List[dict]]:
        """Esegue il ciclo di allerte e restituisce i risultati."""

        self.summary.reset()
        for module in ALERT_MODULES:
            module.reset_state()

        targets = list(self._iter_targets(account_ids))
        print(f"[Allerte] Trovati {len(targets)} account da analizzare.")

        for index, account_id in enumerate(targets, start=1):
            context = self.store.describe_account(account_id)
            account_name = self.store.resolve_account_name(account_id)
            print(
                f"[Allerte] ({index}/{len(targets)}) Analisi dell'account "
                f"{account_name} ({account_id})."
            )
            for module in ALERT_MODULES:
                module.run(context, summary=self.summary)

        details = self.summary.all_alerts()
        print(f"[Allerte] Rilevate {len(details)} allerte complessive.")
        return {
            "details": details,
            "summary": self.summary.summary_rows(),
            "statistics": self.summary.statistics(total_accounts=len(targets)),
        }

    def _iter_targets(self, account_ids: Optional[Sequence[str]]) -> Iterable[str]:
        if account_ids:
            seen = set()
            for account_id in account_ids:
                if account_id in self.store.accounts and account_id not in seen:
                    seen.add(account_id)
                    yield account_id
            return

        yield from self.store.iter_account_ids()


ALERT_LOOP = AlertLoopRunner()
