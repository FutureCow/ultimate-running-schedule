from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://runuser:runpass@localhost:5432/rundb"

    # Security
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str = ""  # Optioneel: bijv. http://192.168.1.81:8317 voor CLIProxyAPI
    CLAUDE_MODEL: str = "claude-opus-4-6"  # Overschrijf bij gebruik van een proxy

    # Garmin credential encryption (Fernet key)
    GARMIN_ENCRYPTION_KEY: str = ""

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    REGISTRATION_OPEN: bool = True

    # SMTP — password reset emails
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""          # e.g. "Cadence <noreply@cadence.app>"
    SMTP_TLS: bool = True        # STARTTLS; set False for SSL-only port 465
    APP_URL: str = "http://localhost:3000"  # Base URL for reset links

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
