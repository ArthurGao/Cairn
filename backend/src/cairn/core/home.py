"""What makes a directory usable as a harness home or a case store (design §3)."""

import os
from pathlib import Path

HOME_REQUIRED = ("AGENTS.md", "memory")


def home_problem(home: Path) -> str | None:
    """None when `home` is a harness home, else why it is not."""
    if not home.is_dir():
        return f"{home} is not a directory"
    for required in HOME_REQUIRED:
        if not (home / required).exists():
            return f"{home} has no {required}"
    return None


def case_store_problem(cases: Path) -> str | None:
    """None when `cases` is a readable and writable directory, else why it is not."""
    if not cases.is_dir():
        return f"{cases} is not a directory"
    if not os.access(cases, os.R_OK | os.W_OK):
        return f"{cases} is not readable and writable"
    return None
