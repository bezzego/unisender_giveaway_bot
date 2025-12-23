from __future__ import annotations

from email_validator import validate_email, EmailNotValidError


def normalize_email(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Пустой email")

    try:
        v = validate_email(raw, check_deliverability=False)
    except EmailNotValidError as e:
        raise ValueError("Некорректный email") from e

    return v.normalized