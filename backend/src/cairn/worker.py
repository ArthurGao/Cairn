"""Temporal worker: registers workflows and activities (run: `uv run python -m cairn.worker`).

Startup validation fails loudly instead of at the first call (design §10.3): role config,
vendor availability and the data-class gate are checked before the worker polls.
"""

import asyncio
import logging
import os

from temporalio.client import Client
from temporalio.worker import Worker

from cairn import temporal
from cairn.activities.cases import CaseActivities
from cairn.llm.client import LlmClient, build_client
from cairn.llm.roles import ConfigError, data_class_problem
from cairn.settings import Settings
from cairn.workflows.case_check import CaseCheckWorkflow

log = logging.getLogger("cairn.worker")

WORKFLOWS = [CaseCheckWorkflow]


def validate_startup(settings: Settings, client: LlmClient) -> None:
    if problem := data_class_problem(
        client.roles, settings.data_class, settings.client_data_vendors
    ):
        raise ConfigError(f"refusing to start: {problem}")


def build_worker(settings: Settings, temporal_client: Client, llm: LlmClient) -> Worker:
    activities = CaseActivities(settings, llm)
    return Worker(
        temporal_client,
        task_queue=settings.task_queue,
        workflows=WORKFLOWS,
        activities=list(activities.all()),
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    settings = Settings()
    llm = build_client(settings, os.environ)
    validate_startup(settings, llm)
    settings.cases_dir.mkdir(parents=True, exist_ok=True)
    client = await temporal.connect(settings)
    log.info("worker polling %s on %s", settings.task_queue, settings.temporal_address)
    await build_worker(settings, client, llm).run()


if __name__ == "__main__":
    asyncio.run(main())
