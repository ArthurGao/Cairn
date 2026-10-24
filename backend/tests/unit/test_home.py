import shutil
from pathlib import Path

from cairn.core.home import case_store_problem, home_problem


def test_fixture_home_is_a_home(home: Path) -> None:
    assert home_problem(home) is None


def test_missing_directory(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert home_problem(missing) == f"{missing} is not a directory"
    assert case_store_problem(missing) == f"{missing} is not a directory"


def test_home_without_memory(home: Path) -> None:
    shutil.rmtree(home / "memory")
    assert home_problem(home) == f"{home} has no memory"


def test_case_store_ok(cases_dir: Path) -> None:
    assert case_store_problem(cases_dir) is None
