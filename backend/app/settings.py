from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://launchscope:launchscope@localhost:5432/launchscope"
    cors_origins: str = "http://localhost:5173"
    session_secret: str = ""
    session_cookie_secure: bool = False
    analyst_username: str = ""
    analyst_password_hash: str = ""
    reviewer_username: str = ""
    reviewer_password_hash: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()