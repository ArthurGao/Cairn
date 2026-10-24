"""Token estimate, L0 context and budgets, secret/personal scans, similarity, usage."""

from datetime import date
from pathlib import Path

import pytest

from cairn.core.context import ContextBreakdown, ContextBudgetError, build_context
from cairn.core.index import load_memories
from cairn.core.secrets import find_personal_data, find_secret
from cairn.core.similarity import normalise, similarity
from cairn.core.tokens import estimate_tokens
from cairn.core.usage import UsageEntry, load_usage, record_run, save_usage
from tests.support import FIXTURES

HOME = FIXTURES / "home"


@pytest.mark.parametrize(
    ("chars", "tokens"), [(0, 0), (1, 1), (3, 1), (4, 2), (7, 2), (8, 3), (35, 10)]
)
def test_estimate_is_ceil_chars_over_3_5(chars: int, tokens: int) -> None:
    assert estimate_tokens("x" * chars) == tokens


def test_context_breakdown_on_the_fixture_home() -> None:
    context = build_context(HOME, l0_budget=4000, memory_index_budget=1500)
    assert context.breakdown == ContextBreakdown(
        agents_md=386,
        skill_index=165,
        memory_index=240,
        l0_total=790,
        baseline_all=1374,
        omitted_index_lines=0,
    )
    assert context.prompt.startswith("# AGENTS.md — runtime agent instructions\n")
    assert "- presubmission-aewv — Final completeness check" in context.prompt
    assert "- [Intake form v1 dates](intake-form-v1-dates.md) — " in context.prompt
    assert "**Why:**" not in context.prompt  # no memory body is loaded eagerly


def test_baseline_counts_every_body(home: Path) -> None:
    before = build_context(home, 4000, 1500).breakdown.baseline_all
    target = home / "memory" / "pilot-scope.md"
    target.write_text(target.read_text() + "x" * 35)
    assert build_context(home, 4000, 1500).breakdown.baseline_all == before + 10


def test_memory_index_trimmed_from_the_end_and_stated() -> None:
    context = build_context(HOME, l0_budget=4000, memory_index_budget=150)
    assert context.breakdown.omitted_index_lines == 4
    assert context.breakdown.memory_index <= 150
    assert "(4 more memories not shown: the index is over its token budget)" in context.prompt
    assert "adviser-wants-english-findings.md" in context.prompt  # user line kept first
    assert "intake-form-v1-dates.md" not in context.prompt


def test_l0_budget_is_shared_with_agents_md_and_skills() -> None:
    context = build_context(HOME, l0_budget=386 + 165 + 120, memory_index_budget=1500)
    assert context.breakdown.memory_index <= 120
    assert context.breakdown.omitted_index_lines == 4


def test_agents_md_and_skills_over_budget_fail_loudly() -> None:
    with pytest.raises(ContextBudgetError, match="need 551 tokens; CAIRN_L0_BUDGET is 550"):
        build_context(HOME, l0_budget=550, memory_index_budget=1500)


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("key sk-ant-api03-abcdefgh1234", "anthropic_key"),
        ("token sk-proj1234567890abcdef", "api_key"),
        ("AKIAABCDEFGHIJKLMNOP", "aws_access_key"),
        ("ghp_abcdefghijklmnopqrstu123", "github_token"),
        ("xoxb-1234567890-abc", "slack_token"),
        ("-----BEGIN OPENSSH PRIVATE KEY-----", "private_key"),
        ("Password: hunter2", "password"),
        ("sha " + "a1" * 20, "hex_run"),
        ("dGhpcyBpcyBhIHNlY3JldCB2YWx1ZSB0aGF0IGlzIGxvbmc0", "base64_run"),
    ],
)
def test_secret_patterns(text: str, name: str) -> None:
    assert find_secret(text) == name


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("mail alex@example.test", "email"),
        ("call +64 21 555 1234", "phone"),
        ("passport XS0000001", "passport_number"),
        ("Date of birth: 12 April 1990", "date_of_birth"),
        ("born 1990", "date_of_birth"),
    ],
)
def test_personal_patterns(text: str, name: str) -> None:
    assert find_personal_data(text) == name


@pytest.mark.parametrize(
    "text",
    [
        "Release on 2026-10-24 at 17:00",
        "skills/presubmission-<visa>/references/checklist.yaml",
        "docs/design/sections/progressive/disclosure/budget/index",
        "Ask which start date is correct before submission",
        "confirm name, number, date of birth and expiry are readable",
    ],
)
def test_ordinary_text_is_not_flagged(text: str) -> None:
    assert (find_secret(text), find_personal_data(text)) == (None, None)


def test_no_fixture_memory_is_flagged() -> None:
    memories, _ = load_memories(HOME)
    flagged = [
        (m.slug, find_secret(text), find_personal_data(text))
        for m in memories
        if (text := m.file.description + "\n" + m.file.body)
        and (find_secret(text) or find_personal_data(text))
    ]
    assert flagged == []


def test_similarity_of_the_planted_pair() -> None:
    memories = {m.slug: m.file for m in load_memories(HOME)[0]}
    a, b = memories["conflicts-as-questions"], memories["neutral-wording-for-discrepancies"]
    assert round(similarity(a.description, b.description), 2) == 0.52
    assert round(similarity(a.body, b.body), 2) == 0.75


def test_normalise_drops_stop_words_and_punctuation() -> None:
    assert normalise("The release, at 17:00 — for THEM!") == "release 17:00"


def test_usage_round_trip_and_record_run(home: Path) -> None:
    original = (home / "state/usage.json").read_text()
    usage = load_usage(home)
    save_usage(home, usage)
    assert (home / "state/usage.json").read_text() == original
    today = date(2026, 10, 25)
    updated = record_run(usage, ["pilot-scope", "pilot-scope", "new-one"], ["new-one"], today)
    assert updated["pilot-scope"] == UsageEntry(reads=10, last_read=today, written_by_runs=0)
    assert updated["new-one"] == UsageEntry(reads=1, last_read=today, written_by_runs=1)
    assert usage["pilot-scope"].reads == 9  # input untouched
    save_usage(home, updated)
    assert list(load_usage(home))[-1] == "new-one"
