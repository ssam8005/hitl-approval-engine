"""
config.py — Centralized settings, loaded and validated at startup.

All environment variables are parsed here. Missing required vars raise
ValueError immediately on import — fail-fast rather than fail at runtime.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_secret_key: str
    service_port: int
    environment: str
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_mode: str
    telegram_webhook_url: str
    auto_approve_threshold: int
    auto_reject_threshold: int
    approval_ttl_hours: int
    default_approval_action: str
    n8n_webhook_url: str
    n8n_webhook_secret: str
    webhook_timeout: int
    database_url: str
    audit_enabled: bool
    audit_retention_days: int

    @classmethod
    def from_env(cls) -> "Settings":
        """Load and validate. Raises ValueError on missing required vars."""
        required = [
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID",
            "N8N_WEBHOOK_URL",
            "API_SECRET_KEY",
        ]
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
        return cls(
            api_secret_key=os.getenv("API_SECRET_KEY", ""),
            service_port=int(os.getenv("SERVICE_PORT", 8080)),
            environment=os.getenv("ENVIRONMENT", "development"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            telegram_mode=os.getenv("TELEGRAM_MODE", "polling"),
            telegram_webhook_url=os.getenv("TELEGRAM_WEBHOOK_URL", ""),
            auto_approve_threshold=int(os.getenv("AUTO_APPROVE_SCORE_THRESHOLD", 85)),
            auto_reject_threshold=int(os.getenv("AUTO_REJECT_SCORE_THRESHOLD", 30)),
            approval_ttl_hours=int(os.getenv("APPROVAL_TTL_HOURS", 24)),
            default_approval_action=os.getenv("DEFAULT_APPROVAL_ACTION", "reject"),
            n8n_webhook_url=os.getenv("N8N_WEBHOOK_URL", ""),
            n8n_webhook_secret=os.getenv("N8N_WEBHOOK_SECRET", ""),
            webhook_timeout=int(os.getenv("WEBHOOK_TIMEOUT_SECONDS", 10)),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./hitl_engine.db"),
            audit_enabled=os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true",
            audit_retention_days=int(os.getenv("AUDIT_RETENTION_DAYS", 90)),
        )


# Loaded lazily so tests can patch env before import
def get_settings() -> Settings:
    return Settings.from_env()
