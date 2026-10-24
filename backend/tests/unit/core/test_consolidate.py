"""Merge-draft acceptance (design §7.3): exact refusal reasons and the exact merged file."""

from datetime import date
from pathlib import Path

import pytest

from cairn.core.consolidate import (
    MergeDraft,
    archive_change,
    change_group,
    check_draft,
    facts,
    merge_change,
)
from cairn.core.index import Memory, load_memories

TODAY = date(2026, 10, 24)
BODY = (
    "Write every conflict as a neutral question the adviser can put to the client, for example\n"
    '"Which start date is correct?".\n\n'
    "**Why:** most conflicts are typos or date-format differences, and advisers forward the\n"
    "questions to clients.\n"
    "**How to apply:** give both versions with their sources, then ask which one is right; never\n"
    "say a document is wrong.\n"
    "Related: [[intake-form-v1-dates]]\n"
)


@pytest.fixture
def cluster(home: Path) -> list[Memory]:
    pair = ("conflicts-as-questions", "neutral-wording-for-discrepancies")
    return [m for m in load_memories(home)[0] if m.slug in pair]


def _draft(**kw: object) -> MergeDraft:
    base: dict[str, object] = {
        "target_slug": "conflicts-as-questions",
        "description": "Phrase each conflict as a neutral question to confirm, never an accusation",
        "body": BODY,
        "evidence": ["never as an allegation that a document is wrong"],
    }
    return MergeDraft.model_validate(base | kw)


def test_facts_are_identifiers_numbers_paths_and_urls() -> None:
    assert facts("Use `MM/YYYY` (see https://x.test/a), memory/_archive/x.md, 2026-10-24, v1.") == [
        "`MM/YYYY`",
        "https://x.test/a",
        "memory/_archive/x.md",
        "2026-10-24",
        "v1",
    ]


def test_faithful_draft_gives_the_merged_target_file(cluster: list[Memory]) -> None:
    check = check_draft(cluster, _draft(), TODAY)
    assert check.problem is None
    assert check.text == (
        "---\n"
        "name: conflicts-as-questions\n"
        "description: Phrase each conflict as a neutral question to confirm, never an accusation\n"
        "metadata:\n"
        "  type: feedback\n"
        "  created: 2026-07-14\n"
        "  updated: 2026-10-24\n"
        "---\n\n" + BODY
    )


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (
            {"target_slug": "pilot-scope"},
            "target 'pilot-scope' is not one of "
            "['conflicts-as-questions', 'neutral-wording-for-discrepancies']",
        ),
        ({"description": ""}, "description must be one non-empty line"),
        ({"body": BODY + "Key sk-ant-abcdefghijkl.\n"}, "matches the anthropic_key pattern"),
        ({"body": BODY + "Call +64 21 555 0199.\n"}, "matches the phone pattern"),
        (
            {"evidence": ["always accuse the client"]},
            "evidence not in the cluster: 'always accuse the client'",
        ),
        (
            {"body": BODY + "Reply within 14 days.\n"},
            "the merged body adds '14', which no source has",
        ),
        (
            {"body": BODY.replace("[[intake-form-v1-dates]]", "[[intake-form-v2-dates]]")},
            "the merged body adds 'intake-form-v2-dates', which no source has",
        ),
    ],
)
def test_unfaithful_or_unsafe_drafts_are_refused(
    cluster: list[Memory], change: dict[str, object], problem: str
) -> None:
    check = check_draft(cluster, _draft(**change), TODAY)
    assert (check.text, check.problem) == (None, problem)


def test_a_merge_applies_as_one_group_against_lint_time_hashes(cluster: list[Memory]) -> None:
    hashes = {"conflicts-as-questions": "h-target", "neutral-wording-for-discrepancies": "h-member"}
    change = merge_change(cluster, "conflicts-as-questions", "MERGED", hashes)
    group = change_group(change, "cleanup-1")
    assert group.group_id == "cleanup-1:merge:conflicts-as-questions"
    assert [(o.op_id, o.op, o.slug, o.after, o.base_hash) for o in group.ops] == [
        (
            "cleanup-1:merge:conflicts-as-questions:0",
            "update",
            "conflicts-as-questions",
            "MERGED",
            "h-target",
        ),
        (
            "cleanup-1:merge:conflicts-as-questions:1",
            "archive",
            "neutral-wording-for-discrepancies",
            None,
            "h-member",
        ),
    ]
    stale = change_group(
        archive_change("old-note", "text", "h-old", "last read 2026-04-02"), "cleanup-1"
    )
    assert [(o.op_id, o.op, o.base_hash, o.reason) for o in stale.ops] == [
        ("cleanup-1:archive:old-note:0", "archive", "h-old", "stale: last read 2026-04-02")
    ]
