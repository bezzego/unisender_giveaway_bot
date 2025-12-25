from __future__ import annotations

import logging
from email_validator import validate_email, EmailNotValidError


log = logging.getLogger(__name__)


def normalize_email(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        log.warning("Empty email string received")
        raise ValueError("Пустой email")

    try:
        v = validate_email(raw, check_deliverability=False)
    except EmailNotValidError as e:
        log.warning("Email validation failed", extra={"email": raw})
        raise ValueError("Некорректный email") from e

    log.debug("Email normalized", extra={"email": v.normalized})
    return v.normalized
