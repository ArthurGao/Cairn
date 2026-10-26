import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from cairn.settings import env_names
from tests.support import make_settings

ENV_EXAMPLE = Path(__file__).parents[2] / ".env.example"


def test_env_example_lists_exactly_the_settings() -> None:
    declared = {
        m.group(1)
        for line in ENV_EXAMPLE.read_text().splitlines()
        if (m := re.match(r"^([A-Z][A-Z0-9_]*)=", line))
    }
    assert declared == env_names()


def test_cases_dir_inside_home_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="must not be inside CAIRN_HOME"):
        make_settings(tmp_path, tmp_path / "cases")


def test_cases_dir_equal_to_home_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="must not be inside CAIRN_HOME"):
        make_settings(tmp_path, tmp_path)


def test_unknown_data_class_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="data_class"):
        make_settings(tmp_path / "home", tmp_path / "cases", data_class="real")


def test_review_timeout_parses_iso_duration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CAIRN_REVIEW_TIMEOUT", "P6D")
    settings = make_settings(tmp_path / "h", tmp_path / "c")
    assert settings.review_timeout.total_seconds() == 6 * 24 * 3600


def test_empty_fake_scenario_means_unset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAIRN_FAKE_SCENARIO", "")
    assert make_settings(tmp_path / "h", tmp_path / "c").fake_scenario is None
    monkeypatch.setenv("CAIRN_FAKE_SCENARIO", "s.json")
    assert make_settings(tmp_path / "h", tmp_path / "c").fake_scenario == Path("s.json")


def test_empty_ready_file_means_unset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # .env.example lists CAIRN_READY_FILE= ; Path("") would be "." (the working directory).
    monkeypatch.setenv("CAIRN_READY_FILE", "")
    assert make_settings(tmp_path / "h", tmp_path / "c").ready_file is None
    monkeypatch.setenv("CAIRN_READY_FILE", "/tmp/ready")
    assert make_settings(tmp_path / "h", tmp_path / "c").ready_file == Path("/tmp/ready")
