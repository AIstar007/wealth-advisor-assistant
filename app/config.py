from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=False)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    run_mode: str = os.getenv("RUN_MODE", "mock").strip().lower()
    log_level: str = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    auto_approve: bool = _env_bool("AUTO_APPROVE", False)
    database_path: str = os.getenv("DATABASE_PATH", "data/wealth_advisor.db")
    mock_crm_url: str = os.getenv("MOCK_CRM_URL", "https://wealth-advisor-assistant-backend.onrender.com/mock/crm")
    crm_mode: str = os.getenv("CRM_MODE", "memory").strip().lower()

    # Azure OpenAI (primary runtime for this assignment)
    azure_openai_endpoint: str | None = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_openai_base_url: str | None = os.getenv("AZURE_OPENAI_BASE_URL")
    azure_openai_api_key: str | None = os.getenv("AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str | None = (
        os.getenv("AZURE_OPENAI_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_CHAT_MODEL")
        or os.getenv("AZURE_OPENAI_MODEL")
    )
    azure_openai_api_version: str | None = os.getenv("AZURE_OPENAI_API_VERSION")

    # Microsoft Foundry project mode (optional alternative)
    foundry_project_endpoint: str | None = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    foundry_model: str | None = os.getenv("FOUNDRY_MODEL")

    # Empty means: do not send temperature, allowing reasoning deployments such as GPT-5-class models.
    agent_temperature: float | None = (
        float(os.getenv("AGENT_TEMPERATURE")) if os.getenv("AGENT_TEMPERATURE") else None
    )

    anomaly_z_threshold: float = float(os.getenv("ANOMALY_Z_THRESHOLD", "3.0"))
    spending_spike_pct: float = float(os.getenv("SPENDING_SPIKE_PCT", "0.25"))
    low_cash_buffer_months: float = float(os.getenv("LOW_CASH_BUFFER_MONTHS", "3"))
    concentration_threshold: float = float(os.getenv("CONCENTRATION_THRESHOLD", "0.50"))
    human_review_min_risk: str = os.getenv("HUMAN_REVIEW_MIN_RISK", "HIGH").upper()

    def validate_azure_openai(self) -> None:
        missing = [
            name
            for name, value in (
                (
                    "AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_BASE_URL",
                    self.azure_openai_endpoint or self.azure_openai_base_url,
                ),
                ("AZURE_OPENAI_API_KEY", self.azure_openai_api_key),
                ("AZURE_OPENAI_DEPLOYMENT", self.azure_openai_deployment),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing Azure OpenAI configuration: " + ", ".join(missing)
            )

    @property
    def resolved_database_path(self) -> Path:
        return _resolve_project_path(self.database_path)

    def validate_foundry(self) -> None:
        missing = [
            name
            for name, value in (
                ("FOUNDRY_PROJECT_ENDPOINT", self.foundry_project_endpoint),
                ("FOUNDRY_MODEL", self.foundry_model),
            )
            if not value
        ]
        if missing:
            raise RuntimeError("Missing Foundry configuration: " + ", ".join(missing))


settings = Settings()

# Resolve paths relative to the project, not the caller's current directory.
def _resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


_resolve_project_path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
(PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)
