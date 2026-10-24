from pathlib import Path
from typing import Any

from cairn.settings import Settings


def make_settings(home: Path, cases_dir: Path, **overrides: Any) -> Settings:
    """Settings for a test: ignore backend/.env so a developer's local values never leak in."""
    return Settings(_env_file=None, home=home, cases_dir=cases_dir, **overrides)  # pyright: ignore[reportCallIssue]
