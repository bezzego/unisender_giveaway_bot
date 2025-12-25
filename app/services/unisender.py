from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

from app.config import settings

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class UnisenderContactStatus:
    email_status: str | None  # active/invited/new/...
    in_list: bool
    list_status: str | None   # active/unsubscribed/...


class UnisenderClient:
    """
    Uses Unisender 'getContact' method.
    Docs: status values like invited/active/etc.  [oai_citation:2‡Unisender](https://www.unisender.com/ru/support/api/contacts/getcontact/)
    """
    def __init__(self, api_key: str, base_url: str, lang: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.lang = lang

    async def get_contact(self, email: str, include_lists: bool = True) -> dict[str, Any]:
        url = f"{self.base_url}/{self.lang}/api/getContact"
        params = {
            "format": "json",
            "api_key": self.api_key,
            "email": email,
        }
        if include_lists:
            params["include_lists"] = "1"

        log.debug("Unisender getContact request", extra={"email": email, "include_lists": include_lists})
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.get(url, params=params) as resp:
                log.debug("Unisender response status", extra={"status": resp.status})
                data = await resp.json(content_type=None)

        # Unisender returns {"result": {...}} or {"error": "...", "code": "..."}
        if isinstance(data, dict) and "error" in data:
            log.error(
                "Unisender error response",
                extra={"email": email, "error": data.get("error"), "code": data.get("code")},
            )
            return data

        log.debug("Unisender getContact success", extra={"email": email})
        return data

    async def check_confirmed_in_list(self, email: str, list_id: str) -> UnisenderContactStatus:
        log.info("Checking Unisender list confirmation", extra={"email": email, "list_id": list_id})
        data = await self.get_contact(email=email, include_lists=True)

        if isinstance(data, dict) and "error" in data:
            error_code = data.get("code")
            if error_code == "object_not_found":
                log.warning("Unisender contact not found", extra={"email": email})
                return UnisenderContactStatus(
                    email_status=None,
                    in_list=False,
                    list_status=None,
                )
            raise RuntimeError(f"Unisender error: {data.get('error')} (code={error_code})")

        result = (data or {}).get("result") or {}
        email_obj = result.get("email") or {}

        email_status = email_obj.get("status")  # invited/active/...
        lists = result.get("lists") or []

        in_list = False
        list_status = None
        for item in lists:
            if str(item.get("id")) == str(list_id):
                in_list = True
                list_status = item.get("status")
                break

        log.debug(
            "Unisender list status",
            extra={
                "email": email,
                "email_status": email_status,
                "in_list": in_list,
                "list_status": list_status,
            },
        )
        return UnisenderContactStatus(
            email_status=email_status,
            in_list=in_list,
            list_status=list_status,
        )


unisender = UnisenderClient(
    api_key=settings.unisender_api_key,
    base_url=settings.unisender_base_url,
    lang=settings.unisender_lang,
)
