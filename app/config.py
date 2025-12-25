from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Telegram
    bot_token: str = Field(..., alias="BOT_TOKEN")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")  # e.g. postgresql+asyncpg://user:pass@localhost:5432/db

    # Unisender
    unisender_api_key: str = Field(..., alias="UNISENDER_API_KEY")
    unisender_lang: str = Field("ru", alias="UNISENDER_LANG")  # ru|en
    unisender_base_url: str = Field("https://api.unisender.com", alias="UNISENDER_BASE_URL")
    unisender_list_id: str = Field(..., alias="UNISENDER_LIST_ID")  # the mailing list used for the giveaway

    # Giveaway
    cinema_limit: int = Field(40, alias="CINEMA_LIMIT")
    guide_link: str = Field(..., alias="GUIDE_LINK")
    fallback_promo: str | None = Field(None, alias="FALLBACK_PROMO")  # optional

    # Admins
    admin_ids_raw: str = Field("97209077,764643451", alias="ADMIN_IDS")

    # Optional: rate limiting, etc.
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @computed_field(return_type=list[int])
    @property
    def admin_ids(self) -> list[int]:
        if not self.admin_ids_raw:
            return []
        parts = [item.strip() for item in str(self.admin_ids_raw).split(",") if item.strip()]
        return [int(item) for item in parts]


settings = Settings()
