from datetime import date
from pathlib import Path

import pytest

from cairn.cli import run
from cairn.core.lint import Finding, LintConfig, has_errors, lint_home
from cairn.core.usage import UsageEntry, load_usage
from cairn.core.writer import read_changelog, text_hash

TODAY = date(2026, 10, 24)


def _lint(home: Path, **config: object) -> list[Finding]:
    return lint_home(home, load_usage(home), TODAY, LintConfig(**config))  # pyright: ignore[reportArgumentType]


def _checks(findings: list[Finding]) -> list[tuple[str, str, list[str], str | None]]:
    return [(f.check, f.severity, f.slugs, f.proposed) for f in findings]


def test_fixture_home_has_one_duplicate_cluster_and_one_stale_memory(home: Path) -> None:
    findings = _lint(home)
    assert _checks(findings) == [
        (
            "duplicate",
            "info",
            ["conflicts-as-questions", "neutral-wording-for-discrepancies"],
            "merge",
        ),
        ("stale", "info", ["intake-form-v1-dates"], "archive"),
    ]
    assert findings[0].message == (
        "near-duplicates: conflicts-as-questions/neutral-wording-for-discrepancies "
        "description 0.52, body 0.75"
    )
    assert not has_errors(findings)
    for finding in findings:  # base hashes taken at lint time, one per slug (§7.4)
        assert finding.base_hashes == {
            slug: text_hash((home / "memory" / f"{slug}.md").read_text()) for slug in finding.slugs
        }


def test_index_missing_orphan_and_drift(home: Path) -> None:
    index = home / "memory/MEMORY.md"
    lines = index.read_text().splitlines(keepends=True)
    index.write_text("".join(lines[:-1]) + "- [Gone](gone-memory.md) — removed\n")
    assert [(f.check, f.slugs) for f in _lint(home) if f.proposed == "index_sync"] == [
        ("index_missing", ["intake-form-v1-dates"]),
        ("index_orphan", ["gone-memory"]),
    ]
    index.write_text("".join([lines[0], lines[1], lines[3], lines[2], *lines[4:]]))
    assert [f.check for f in _lint(home) if f.proposed == "index_sync"] == ["index_drift"]


def test_errors_for_broken_files_budget_and_specs(home: Path) -> None:
    (home / "memory/broken.md").write_text("no frontmatter here")
    checklist = home / "skills/presubmission-aewv/references/checklist.yaml"
    checklist.write_text("visa: aewv\nversion: 1\nowner: o\nitems: []\n")
    categories = home / "skills/case-consistency-check/references/fact-categories.md"
    categories.write_text("# nothing\n")
    findings = _lint(home, memory_index_budget=100)
    errors = [(f.check, f.slugs) for f in findings if f.severity == "error"]
    assert errors == [
        ("frontmatter_invalid", ["broken"]),
        ("index_over_budget", []),
        ("spec_invalid", ["case-consistency-check"]),
        ("spec_invalid", ["presubmission-aewv"]),
    ]
    assert has_errors(findings)


def test_stale_rules(home: Path) -> None:
    usage = load_usage(home)
    usage["intake-form-v1-dates"] = UsageEntry(reads=2, last_read=date(2026, 1, 1))
    del usage["checklist-owner"]  # never read, created 2026-08-11: not yet 90 days
    usage["adviser-wants-english-findings"] = UsageEntry(reads=0, last_read=date(2025, 1, 1))
    stale = [f.slugs for f in lint_home(home, usage, TODAY, LintConfig()) if f.check == "stale"]
    assert stale == []  # 2 reads keeps it; user memories are never stale
    later = date(2026, 11, 10)
    stale = [f.slugs for f in lint_home(home, usage, later, LintConfig()) if f.check == "stale"]
    assert stale == [["checklist-owner"]]


def test_cli_lint_exit_codes(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["lint", "--home", str(home), "--today", "2026-10-24"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "2 finding(s)"
    (home / "memory/broken.md").write_text("nope")
    assert run(["lint", "--home", str(home), "--today", "2026-10-24", "--json"]) == 1


def test_cli_index_check_and_regenerate(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    index = home / "memory/MEMORY.md"
    golden = index.read_text()
    index.write_text("# Memory\n")
    assert run(["index", "--home", str(home), "--check"]) == 1
    assert index.read_text() == "# Memory\n"
    assert run(["index", "--home", str(home)]) == 0
    assert index.read_text() == golden
    assert [(e.op, e.actor, e.before) for e in read_changelog(home)] == [
        ("index_sync", "cli", "# Memory\n")
    ]
    assert run(["index", "--home", str(home), "--check"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "MEMORY.md is up to date"


def test_cli_context_and_undo_errors(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["context", "--home", str(home), "--task", "Check case 1"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# Task\nCheck case 1\n\n# AGENTS.md")
    assert '"l0_total": 790' in out
    assert run(["undo", "--home", str(home), "chg_missing"]) == 2
    assert capsys.readouterr().err == "error [change_not_found]: no change chg_missing\n"
