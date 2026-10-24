import shutil
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment

from cairn.settings import env_names
from tests.support import FIXTURES


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test sees the developer's shell settings or vendor keys (tests/support.py skips .env)."""
    for name in env_names():
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """A private copy of the canonical fixture home; tests never touch workspace/."""
    target = tmp_path / "home"
    shutil.copytree(FIXTURES / "home", target)
    return target


@pytest.fixture
def cases_dir(tmp_path: Path) -> Path:
    target = tmp_path / "cases"
    target.mkdir()
    return target


@pytest.fixture(scope="session")
async def temporal_env() -> AsyncIterator[WorkflowEnvironment]:
    """A real local Temporal dev server (first run downloads the binary)."""
    env = await WorkflowEnvironment.start_local(data_converter=pydantic_data_converter)
    try:
        yield env
    finally:
        await env.shutdown()
