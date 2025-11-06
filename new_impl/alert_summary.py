"""Archivio delle allerte per la nuova applicazione."""

from __future__ import annotations

import csv
import io
from typing import Dict, Iterable, List


FIELDNAMES = [
    "alert_type",
    "account_id",
    "account_name",
    "contact_id",
    "contact_name",
    "contact_roles",
    "issue_category",
    "data_focus",
    "details",
    "message",
]


class AlertSummaryStore:
    """Memorizza le allerte prodotte dal ciclo di controllo."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._alerts: List[Dict[str, str]] = []

    def record(self, alert: Dict[str, str]) -> None:
        if not alert:
            return
        normalised = {field: alert.get(field, "") for field in FIELDNAMES}
        self._alerts.append(normalised)

    def extend(self, alerts: Iterable[Dict[str, str]]) -> None:
        for alert in alerts:
            self.record(alert)

    def all_alerts(self) -> List[Dict[str, str]]:
        return list(self._alerts)

    def summary_rows(self) -> List[Dict[str, str]]:
        return self.all_alerts()

    def to_csv(self) -> bytes:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=FIELDNAMES)
        writer.writeheader()
        for alert in self._alerts:
            writer.writerow({field: alert.get(field, "") for field in FIELDNAMES})
        return output.getvalue().encode("utf-8")


ALERT_SUMMARY = AlertSummaryStore()
