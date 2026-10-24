"""The sample case end to end on the default roles (gateway, Claude Sonnet 5.5). Live only.

A real model extracts its own facts, so ids and counts differ from the fake run; the test
asserts what must hold: the two planted conflicts are found, the unreadable photo is a gap.
"""

import uuid
from pathlib import Path

import pytest
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment

from cairn.core.cases import store
from cairn.llm.client import build_client
from cairn.llm.validate import validate_models
from cairn.worker import build_worker
from cairn.workflows.case_check import CaseCheckWorkflow
from cairn.workflows.case_models import CheckInput
from tests.live.test_live_vendors import GATEWAY_KEY
from tests.support import make_settings
from tests.workflows.test_case_check import _upload_sample

pytestmark = pytest.mark.live


async def test_sample_consistency_check_live(home: Path, cases_dir: Path) -> None:
    if not GATEWAY_KEY:
        pytest.skip("AI_GATEWAY_API_KEY is not set: live end-to-end check skipped")
    settings = make_settings(
        home, cases_dir, AI_GATEWAY_API_KEY=GATEWAY_KEY, task_queue=f"live-{uuid.uuid4()}"
    )
    llm = build_client(settings, env={})
    await validate_models(llm.roles)
    _upload_sample(cases_dir)
    env = await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter)
    try:
        async with build_worker(settings, env.client, llm):
            summary = await env.client.execute_workflow(
                CaseCheckWorkflow.run,
                CheckInput(check_id="L1", case_id="C1", kind="consistency"),
                id=f"live-{uuid.uuid4()}",
                task_queue=settings.task_queue,
            )
    finally:
        await env.shutdown()
    result = store.read_result(cases_dir, "C1", "L1")
    assert (summary.status, result.error) == ("completed", None)
    facts = {f.fact_id: f for f in result.facts}
    conflict_categories = {facts[c.fact_ids[0]].category for c in result.conflicts}
    assert {"employment.period", "address.period"} <= conflict_categories
    assert [g.doc_id for g in result.gaps] == ["unreadable-photo"]
