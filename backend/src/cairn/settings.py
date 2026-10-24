"""Every CAIRN_* setting, declared once. `backend/.env.example` lists the same names.

Workflows never read settings: the API and `schedule ensure` copy the values they need into
workflow inputs (design §7.1, §8.1).
"""

from datetime import timedelta
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CAIRN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Storage (design §3)
    home: Path = Path("../workspace")
    cases_dir: Path = Path("../.cases")
    skill_paths: str = ""

    # Data-class gate (design §10.4)
    data_class: Literal["synthetic", "client"] = "synthetic"
    client_data_vendors: str = ""

    # LLM vendors (design §10). Vendor keys keep their vendors' own names, without the prefix.
    ai_gateway_api_key: SecretStr = Field(
        default=SecretStr(""), validation_alias="AI_GATEWAY_API_KEY"
    )
    anthropic_api_key: SecretStr = Field(
        default=SecretStr(""), validation_alias="ANTHROPIC_API_KEY"
    )
    llm_vendor: str = ""

    # Temporal and API
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    task_queue: str = "cairn"
    cors_origin: str = "http://localhost:4710"

    # Progressive disclosure and agent runs (design §4.2, §5, §6)
    l0_budget: int = 4000
    memory_index_budget: int = 1500
    max_steps: int = 8

    # Case checks (design §8)
    map_budget: int = 100_000
    case_context_budget: int = 150_000
    min_page_chars: int = 40
    check_concurrency: int = 4
    item_batch_size: int = 5
    max_documents_per_case: int = 100
    max_pages_per_case: int = 500
    max_upload_mb: int = 20

    # Memory cleanup (design §7)
    cleanup_cron: str = "0 3 * * 0"
    tz: str = "Pacific/Auckland"
    stale_days: int = 90
    dup_threshold: float = 0.82
    dup_body_threshold: float = 0.70
    review_timeout: timedelta = timedelta(days=6)
    auto_apply_mechanical: bool = True

    @model_validator(mode="after")
    def _cases_dir_outside_home(self) -> "Settings":
        home = self.home.resolve()
        cases = self.cases_dir.resolve()
        if cases.is_relative_to(home):
            raise ValueError(
                f"CAIRN_CASES_DIR ({cases}) must not be inside CAIRN_HOME ({home}); "
                "client documents never live in the harness home (design §3.2)"
            )
        return self


def env_names() -> set[str]:
    """The environment variable names Settings reads, for keeping .env.example in sync."""
    names: set[str] = set()
    prefix = Settings.model_config.get("env_prefix", "")
    for name, field in Settings.model_fields.items():
        alias = field.validation_alias
        names.add(alias if isinstance(alias, str) else f"{prefix}{name}".upper())
    return names
