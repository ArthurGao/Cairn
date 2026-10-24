"""Agent runs, context preview, memory and skills (design §11): the "Manage" side."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from temporalio.client import WorkflowExecutionStatus
from ulid import ULID

from cairn.api.schemas import (
    ContextPreview,
    ErrorResponse,
    IndexBudget,
    MemoryDetail,
    MemoryEntry,
    MemoryList,
    RunBrief,
    RunStarted,
    SkillDetail,
    SkillEntry,
    SkillReference,
    StartRun,
)
from cairn.api.services import Services, services
from cairn.api.workflows import workflow_view
from cairn.core.context import build_context
from cairn.core.formats import parse_memory
from cairn.core.index import (
    Skill,
    by_type,
    find_skill,
    index_tokens,
    load_memories,
    load_skills,
    read_memory_text,
    skill_references,
    title,
)
from cairn.core.runs import recorded_status, run_records
from cairn.core.usage import UsageEntry, load_usage
from cairn.core.writer import ChangeEntry, changelog, undo, undone_ids
from cairn.errors import NotFound
from cairn.workflows.agent_run import AgentRunWorkflow, run_workflow_id
from cairn.workflows.run_models import RunInput, RunState

router = APIRouter(prefix="/api", tags=["manage"])
Deps = Annotated[Services, Depends(services)]
ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorResponse} for code in (404, 409, 422, 503)
}


# --- runs -------------------------------------------------------------------------------------


@router.post(
    "/runs", status_code=202, response_model=RunStarted, responses=ERRORS, operation_id="startRun"
)
async def start_run(body: StartRun, deps: Deps) -> RunStarted:
    settings = deps.settings
    client = await deps.temporal.client()
    run_id = str(ULID())
    run = RunInput(
        run_id=run_id,
        task=body.task,
        max_steps=body.max_steps or settings.max_steps,
        l0_budget=settings.l0_budget,
        memory_index_budget=settings.memory_index_budget,
        dup_threshold=settings.dup_threshold,
        tz=settings.tz,
    )
    await client.start_workflow(
        AgentRunWorkflow.run,
        run,
        id=run_workflow_id(run_id),
        task_queue=settings.task_queue,
        memo={"task": body.task[:500]},
    )
    return RunStarted(run_id=run_id)


@router.get("/runs", response_model=list[RunBrief], responses=ERRORS, operation_id="listRuns")
async def list_runs(deps: Deps, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[RunBrief]:
    client = await deps.temporal.client()
    records = run_records(deps.settings.home)
    briefs: list[RunBrief] = []
    async for execution in client.list_workflows('WorkflowType="AgentRunWorkflow"', limit=limit):
        run_id = execution.id.removeprefix("run-")
        memo = await execution.memo()
        if execution.status == WorkflowExecutionStatus.RUNNING:
            status = "running"
        else:
            record = records.get(run_id)
            status = "completed" if record and recorded_status(record) == "completed" else "failed"
        briefs.append(
            RunBrief(
                run_id=run_id,
                task=str(memo.get("task", "")),
                status=status,
                started=execution.start_time,
            )
        )
    return briefs


@router.get("/runs/{run_id}", response_model=RunState, responses=ERRORS, operation_id="getRun")
async def get_run(run_id: str, deps: Deps) -> RunState:
    client = await deps.temporal.client()
    handle = client.get_workflow_handle_for(AgentRunWorkflow.run, run_workflow_id(run_id))

    def stopped(status: str | None) -> RunState:
        if status is None:
            return RunState(run_id=run_id, task="")
        return RunState(
            run_id=run_id, task="", status="failed", error=f"the run stopped ({status})"
        )

    state = await workflow_view(
        handle,
        AgentRunWorkflow.get_state,
        NotFound(f"no run {run_id}", code="run_not_found"),
        stopped,
    )
    return _with_undone(state, deps)


def _with_undone(state: RunState, deps: Services) -> RunState:
    """Applied ops are marked undone from the change log, which outlives the run."""
    if state.writeback and state.writeback.applied:
        undone = undone_ids(deps.settings.home)
        for op in state.writeback.applied:
            op.undone = op.change_id in undone
    return state


# --- context ----------------------------------------------------------------------------------


@router.get(
    "/context/preview",
    response_model=ContextPreview,
    responses=ERRORS,
    operation_id="previewContext",
)
def preview_context(deps: Deps) -> ContextPreview:
    s = deps.settings
    context = build_context(s.home, s.l0_budget, s.memory_index_budget, s.skill_mounts)
    return ContextPreview(prompt=context.prompt, breakdown=context.breakdown)


# --- memory -----------------------------------------------------------------------------------


@router.get("/memory", response_model=MemoryList, operation_id="listMemory")
def list_memory(deps: Deps) -> MemoryList:
    home = deps.settings.home
    memories, broken = load_memories(home)
    usage = load_usage(home)
    tokens = index_tokens(memories)
    budget = deps.settings.memory_index_budget
    return MemoryList(
        entries=[
            MemoryEntry(
                slug=m.slug,
                title=title(m),
                type=m.file.type,
                description=m.file.description,
                created=m.file.created(),
                usage=usage.get(m.slug, UsageEntry()),
            )
            for m in by_type(memories)
        ],
        budget=IndexBudget(tokens=tokens, budget=budget, over=tokens > budget),
        broken=[b.path.name for b in broken],
    )


@router.get("/memory/changelog", response_model=list[ChangeEntry], operation_id="listChangelog")
def list_changelog(
    deps: Deps, limit: Annotated[int, Query(ge=1, le=500)] = 50
) -> list[ChangeEntry]:
    return changelog(deps.settings.home, limit=limit)


@router.post(
    "/memory/changelog/{change_id}/undo",
    response_model=list[ChangeEntry],
    responses=ERRORS,
    operation_id="undoChange",
)
def undo_change(change_id: str, deps: Deps) -> list[ChangeEntry]:
    return undo(deps.settings.home, change_id, "user", datetime.now(UTC)).applied


@router.get(
    "/memory/{slug}", response_model=MemoryDetail, responses=ERRORS, operation_id="getMemory"
)
def get_memory(slug: str, deps: Deps) -> MemoryDetail:
    home = deps.settings.home
    text = read_memory_text(home, slug)
    return MemoryDetail(
        slug=slug, text=text, body=parse_memory(text).body, changelog=changelog(home, slug=slug)
    )


# --- skills -----------------------------------------------------------------------------------


def _skill_entry(skill: Skill) -> SkillEntry:
    return SkillEntry(
        name=skill.name,
        description=skill.file.description,
        source=skill.source,
        read_only=skill.read_only,
        body_chars=len(skill.file.body),
        references=[
            SkillReference(path=str(p), chars=len((skill.path / p).read_text(encoding="utf-8")))
            for p in skill_references(skill)
        ],
    )


@router.get("/skills", response_model=list[SkillEntry], operation_id="listSkills")
def list_skills(deps: Deps) -> list[SkillEntry]:
    loaded = load_skills(deps.settings.home, deps.settings.skill_mounts)
    return [_skill_entry(s) for s in sorted(loaded.skills, key=lambda s: s.name)]


@router.get("/skills/{name}", response_model=SkillDetail, responses=ERRORS, operation_id="getSkill")
def get_skill(name: str, deps: Deps) -> SkillDetail:
    skill = find_skill(deps.settings.home, deps.settings.skill_mounts, name)
    return SkillDetail(**_skill_entry(skill).model_dump(), body=skill.file.body)
