"""Moduli di allerta per la nuova implementazione."""

from . import (  # noqa: F401
    check_contatti_senza_recapiti,
    check_contatti_senza_ruolo,
    check_duplicati_ruolo,
    check_email_contactpoint,
    check_nominali_ruoli_differenti,
    check_sol_email,
    check_telefono_contactpoint,
)

__all__ = [
    "check_contatti_senza_recapiti",
    "check_contatti_senza_ruolo",
    "check_duplicati_ruolo",
    "check_email_contactpoint",
    "check_nominali_ruoli_differenti",
    "check_sol_email",
    "check_telefono_contactpoint",
]
