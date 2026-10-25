"""Every CAIRN_* setting, declared once. `backend/.env.example` lists the same names.

Workflows never read settings: the API and `schedule ensure` copy the values they need into
workflow inputs (design §7.1, §8.1).
"""

import os
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from dotenv import dotenv_values
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from cairn.core.lint import LintConfig


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
    llmgw_base_url: str = ""  # the local LLM gateway, local dev and demos only (D-19)
    llm_vendor: str = ""
    roles_file: Path = Path("config/roles.toml")
    fake_scenario: Path | None = None

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

    @field_validator("fake_scenario", mode="before")
    @classmethod
    def _empty_is_unset(cls, value: object) -> object:
        return None if value == "" else value

    @property
    def fake_scenarios(self) -> tuple[Path, ...]:
        """CAIRN_FAKE_SCENARIO: one scenario file or several, colon-separated."""
        if self.fake_scenario is None:
            return ()
        return tuple(Path(p) for p in str(self.fake_scenario).split(":") if p)

    @property
    def skill_mounts(self) -> tuple[Path, ...]:
        """Read-only skill sources from CAIRN_SKILL_PATHS (colon-separated)."""
        return tuple(Path(p).expanduser() for p in self.skill_paths.split(":") if p)

    def lint_config(self) -> "LintConfig":
        from cairn.core.lint import LintConfig

        return LintConfig(
            memory_index_budget=self.memory_index_budget,
            stale_days=self.stale_days,
            dup_threshold=self.dup_threshold,
            dup_body_threshold=self.dup_body_threshold,
            skill_mounts=self.skill_mounts,
        )

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


def role_env(env_file: Path | None = None) -> dict[str, str]:
    """The env file overlaid by the process environment, as Settings itself resolves them.

    Role overrides (CAIRN_ROLE_<ROLE>_<FIELD>) are not Settings fields, so pydantic-settings
    never reads them from the env file; this gives them the same two sources.
    """
    path = env_file or Path(str(Settings.model_config.get("env_file")))
    from_file = {k: v for k, v in dotenv_values(path).items() if v is not None}
    return {**from_file, **os.environ}
