"""`MemoryCleanupWorkflow`: weekly lint, merge drafts, a person's review, then apply (§7).

Index re-derivation is the only change applied without review. Archives and merges wait for
`submit_review` until `review_timeout`; an unanswered proposal expires with nothing applied.
Deterministic: no I/O, no clock but workflow.now(), no randomness.
"""

from temporalio import workflow
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from cairn.activities.cleanup import CleanupActivities
    from cairn.core.consolidate import not_drafted
    from cairn.workflows.cleanup_models import (
        MAX_CLUSTERS,
        ApplyChangesIn,
        CleanupInput,
        CleanupState,
        CleanupStatus,
        DraftIn,
        DraftOut,
        LintIn,
        MechanicalIn,
        Proposal,
        ReviewDecision,
    )
    from cairn.workflows.common import act, act_model, reason_of


@workflow.defn
class MemoryCleanupWorkflow:
    def __init__(self) -> None:
        self._state: CleanupState | None = None
        self._decision: ReviewDecision | None = None

    @workflow.query
    def get_state(self) -> CleanupState | None:
        return self._state

    @workflow.signal
    def submit_review(self, decision: ReviewDecision) -> None:
        """Only the first decision while awaiting review counts; later ones are ignored."""
        if self._state and self._state.status == "awaiting_review" and self._decision is None:
            self._decision = decision

    @workflow.run
    async def run(self, config: CleanupInput) -> CleanupState:
        wf_id = workflow.info().workflow_id
        self._state = CleanupState(workflow_id=wf_id, started=workflow.now())
        state = self._state
        self._set("linting")
        try:
            linted = await act(
                CleanupActivities.lint_for_cleanup,
                LintIn(workflow_id=wf_id, now=workflow.now(), config=config),
            )
            proposal = state.proposal = Proposal(
                findings=linted.findings, changes=list(linted.archives)
            )
            if config.auto_apply_mechanical and linted.index_drift:
                proposal.mechanical = await act(
                    CleanupActivities.apply_mechanical,
                    MechanicalIn(workflow_id=wf_id, now=workflow.now()),
                )
        except ActivityError as error:
            return self._fail(error)

        self._set("drafting")
        for cluster in linted.clusters[:MAX_CLUSTERS]:
            try:
                out: DraftOut = await act_model(
                    CleanupActivities.draft_merge,
                    DraftIn(workflow_id=wf_id, cluster=cluster, now=workflow.now(), tz=config.tz),
                )
            except ActivityError as error:  # a failed draft is a finding, never a weaker merge
                out = DraftOut(finding=not_drafted(cluster.slugs, reason_of(error)))
            if out.change:
                proposal.changes.append(out.change)
            if out.finding:
                proposal.findings.append(out.finding)

        if not proposal.changes:
            self._set("no_changes")
            return state
        state.expires = workflow.now() + config.review_timeout
        self._set("awaiting_review")
        try:
            await workflow.wait_condition(
                lambda: self._decision is not None, timeout=config.review_timeout
            )
        except TimeoutError:
            self._set("expired")
            return state

        decision = state.decision = self._decision
        assert decision is not None
        approved = [c for c in proposal.changes if c.op_id in decision.approved_op_ids]
        if not approved:
            self._set("rejected")
            return state
        self._set("applying")
        try:
            state.outcome = await act(
                CleanupActivities.apply_changes,
                ApplyChangesIn(workflow_id=wf_id, changes=approved, now=workflow.now()),
            )
        except ActivityError as error:
            return self._fail(error)
        self._set("applied")
        return state

    def _set(self, status: CleanupStatus) -> None:
        """Status also goes to the memo, so the API lists cleanups without querying each one."""
        state = self._state
        assert state is not None
        state.status = status
        workflow.upsert_memo(
            {
                "status": status,
                "expires": state.expires.isoformat() if state.expires else None,
                "changes": len(state.proposal.changes) if state.proposal else 0,
            }
        )

    def _fail(self, error: ActivityError) -> CleanupState:
        assert self._state is not None
        self._state.error = reason_of(error)
        self._set("failed")
        return self._state
