"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file.

    Attributes:
        bot_token: Telegram bot token from BotFather.
        db_path: Path to SQLite database file.
        storage_mode: Storage mode ('local' or 's3').
        storage_root: Root directory for local file storage.
        admin_ids: List of Telegram user IDs with admin privileges.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        debug: Debug mode flag.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Bot
    bot_token: SecretStr

    # Database
    db_path: Path = Field(default=Path("storage/protocols.db"))

    # Storage
    storage_mode: str = "local"
    storage_root: Path = Field(default=Path("storage"))

    # Admin (parsed from comma-separated ADMINS env var)
    admin_ids: list[int] = Field(default_factory=list)

    # Application
    log_level: str = "INFO"
    debug: bool = False

    @model_validator(mode="before")
    @classmethod
    def parse_admins(cls, data: Any) -> Any:
        """Parse ADMINS from comma-separated string to list of ints."""
        if isinstance(data, dict):
            admins_str = data.get("admins", data.get("ADMINS", ""))
            if isinstance(admins_str, str) and admins_str:
                data["admin_ids"] = [
                    int(x.strip()) for x in admins_str.split(",") if x.strip()
                ]
        return data
    
    @property
    def PRIMARY_ADMIN_ID(self) -> int:
        """Get primary admin ID (first admin in the list).
        
        Returns:
            Primary admin Telegram user ID.
        """
        return self.admin_ids[0] if self.admin_ids else 0


settings = Settings()
