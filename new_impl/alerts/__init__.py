"""Modulo che raccoglie tutti gli avvisi della nuova implementazione."""

from . import contact_doppio, ruolo_doppio

ALERT_MODULES = [
    contact_doppio,
    ruolo_doppio,
]

__all__ = ["ALERT_MODULES", "contact_doppio", "ruolo_doppio"]
