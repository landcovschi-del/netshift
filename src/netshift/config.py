"""Configuration from environment variables and .env.

pydantic-settings is roughly IOptions<T> + IConfiguration in .NET: typed access
to settings, validated at startup rather than at first use. Put garbage in
.env and it fails immediately, with a message that says what is wrong.
"""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    netshift_store: Literal["memory", "postgres"] = "memory"
    netshift_log_level: str = "INFO"

    netshift_llm_provider: Literal["anthropic", "openai", "none"] = "none"
    netshift_llm_model: str = "claude-sonnet-5"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    postgres_user: str = "netshift"
    postgres_password: str = "netshift_local_only"
    postgres_db: str = "netshift"
    # 127.0.0.1, not "localhost". On Windows the name resolves to the IPv6
    # address ::1 first, docker-compose publishes the port on IPv4 only, and
    # Docker Desktop swallows the connection attempt instead of refusing it --
    # so the client waits instead of failing. Using the address skips the
    # resolver entirely.
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_connect_timeout: int = 10

    @property
    def postgres_dsn(self) -> str:
        # A network client with no timeout turns an outage into a hang, and a
        # hang costs far more to debug than an error.
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            f"?connect_timeout={self.postgres_connect_timeout}"
        )

    @property
    def llm_key_present(self) -> bool:
        match self.netshift_llm_provider:
            case "anthropic":
                return bool(self.anthropic_api_key)
            case "openai":
                return bool(self.openai_api_key)
            case "none":
                return False


def load_settings() -> Settings:
    return Settings()
