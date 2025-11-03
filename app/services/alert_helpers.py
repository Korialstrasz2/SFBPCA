from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List, Sequence


class AlertHelpers:
    """Utility helpers exposed to dynamic alert logic."""

    @staticmethod
    def normalize(value: str | None) -> str:
        return (value or "").strip().lower()

    @staticmethod
    def title_case(value: str | None) -> str:
        return (value or "").strip().title()

    @staticmethod
    def normalize_phone(value: str | None) -> str:
        if not value:
            return ""
        digits = [ch for ch in value if ch.isdigit()]
        if digits:
            return "".join(digits)
        return (value or "").strip().lower()

    @staticmethod
    def format_contact_name(contact: dict | None) -> str:
        if not contact:
            return "Unknown contact"
        first = (contact.get("FirstName") or "").strip()
        last = (contact.get("LastName") or "").strip()
        full_name = f"{first} {last}".strip()
        return full_name or contact.get("Id", "Unknown contact")

    @staticmethod
    def collect_values(records: Sequence[dict], candidate_keys: Iterable[str]) -> List[str]:
        values: List[str] = []
        for record in records:
            for key in candidate_keys:
                value = record.get(key)
                if value:
                    values.append(value.strip())
                    break
        return values

    @staticmethod
    def find_duplicates(values: Sequence[str]) -> List[str]:
        seen: dict[str, int] = defaultdict(int)
        original: dict[str, str] = {}
        for value in values:
            normalized = value.lower()
            seen[normalized] += 1
            original.setdefault(normalized, value)
        return [original[value] for value, count in seen.items() if count > 1]

    @staticmethod
    def get_account_name(data_store, account_id: str) -> str:
        account = data_store.accounts.get(account_id, {})
        return account.get("Name", account_id)
