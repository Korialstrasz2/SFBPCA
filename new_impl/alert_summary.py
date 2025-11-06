"""Alert summary store for the alternate application."""

from __future__ import annotations

import csv
import io
from typing import Dict, Iterable, List


class AlertSummaryStore:
    """Captures alert records produced by the alert loop."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._alerts: List[Dict[str, str]] = []

    def record(self, alert: Dict[str, str]) -> None:
        if not alert:
            return
        self._alerts.append(dict(alert))

    def extend(self, alerts: Iterable[Dict[str, str]]) -> None:
        for alert in alerts:
            self.record(alert)

    def all_alerts(self) -> List[Dict[str, str]]:
        return list(self._alerts)

    def summary_rows(self) -> List[Dict[str, str]]:
        return self.all_alerts()

    def to_csv(self) -> bytes:
        fieldnames = [
            "alert_type",
            "account_id",
            "account_name",
            "contact_id",
            "contact_name",
            "details",
            "message",
        ]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for alert in self._alerts:
            writer.writerow({field: alert.get(field, "") for field in fieldnames})
        return output.getvalue().encode("utf-8")


ALERT_SUMMARY = AlertSummaryStore()
