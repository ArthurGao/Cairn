"""The worker's ready file: the demo stack's healthcheck (deploy/oracle) waits for it."""

import asyncio
import uuid
from pathlib import Path

import pytest
from temporalio.testing import WorkflowEnvironment

from cairn import worker
from cairn.llm.roles import ConfigError
from tests.support import FIXTURES, make_settings

STALE = "left over from a crashed start"


async def test_ready_only_once_validated_and_about_to_poll(
    home: Path, cases_dir: Path, temporal_env: WorkflowEnvironment, tmp_path: Path
) -> None:
    ready = tmp_path / "ready"
    ready.write_text(STALE)
    settings = make_settings(
        home,
        cases_dir,
        temporal_address=temporal_env.client.service_client.config.target_host,
        llm_vendor="fake",
        fake_scenario=FIXTURES / "llm" / "agent_run.json",
        task_queue=f"ready-{uuid.uuid4()}",
        ready_file=ready,
    )

    running = asyncio.create_task(worker.main(settings))
    try:
        async with asyncio.timeout(30):
            while not ready.exists() or ready.read_text() != settings.task_queue:
                assert not running.done(), running.exception()
                await asyncio.sleep(0.05)
        assert not running.done()
    finally:
        running.cancel()
        with pytest.raises(asyncio.CancelledError):
            await running


async def test_a_worker_that_fails_validation_is_never_ready(
    home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    ready = tmp_path / "ready"
    ready.write_text(STALE)
    # Every role on the real gateway, with no key: refused before Temporal (design §10.3).
    settings = make_settings(home, cases_dir, ready_file=ready)

    with pytest.raises(ConfigError, match="AI_GATEWAY_API_KEY"):
        await worker.main(settings)

    assert not ready.exists()
