from pathlib import Path

import pytest

from cairn.core.formats import (
    FormatError,
    parse_memory,
    parse_skill,
    serialise,
    validate_memory,
    validate_skill,
)
from cairn.core.index import (
    index_lines,
    indexed_slugs,
    load_memories,
    load_skills,
    render_memory_index,
    skill_index_lines,
    title,
)
from tests.support import FIXTURES

HOME = FIXTURES / "home"


def _memory_text(**front: str) -> str:
    fields = {
        "name": "a-note",
        "description": "When this applies",
        "type": "reference",
        "body": "Body.\n",
    } | front
    return (
        f"---\nname: {fields['name']}\ndescription: {fields['description']}\n"
        f"metadata:\n  type: {fields['type']}\n  created: 2026-10-01\n---\n\n{fields['body']}"
    )


@pytest.mark.parametrize("path", sorted((HOME / "memory").glob("[!_M]*.md")), ids=lambda p: p.name)
def test_fixture_memories_round_trip_byte_identical(path: Path) -> None:
    text = path.read_text()
    assert serialise(parse_memory(text)) == text
    assert validate_memory(parse_memory(text), path.stem) == []


def test_unknown_frontmatter_keys_survive_a_rewrite() -> None:
    text = _memory_text().replace("metadata:", "owner_tool: claude-code\nmetadata:")
    memory = parse_memory(text)
    memory.front["description"] = "Changed"
    rewritten = serialise(memory)
    assert "owner_tool: claude-code\n" in rewritten
    assert parse_memory(rewritten).description == "Changed"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("no frontmatter", "missing YAML frontmatter"),
        ("---\nname: x\n", "not closed"),
        ("---\n- a\n---\nbody", "must be a mapping"),
        ("---\nname: [\n---\nbody", "not valid YAML"),
    ],
)
def test_unparseable(text: str, message: str) -> None:
    with pytest.raises(FormatError, match=message):
        parse_memory(text)


def test_memory_rules_each_code() -> None:
    def codes(slug: str = "a-note", **front: str) -> list[str]:
        return [i.code for i in validate_memory(parse_memory(_memory_text(**front)), slug)]

    assert codes() == []
    assert codes("other") == ["name_mismatch"]
    assert codes("Bad_Slug", name="Bad_Slug") == ["name_format"]
    assert codes(description="''") == ["description_missing"]
    assert codes(description="x" * 151) == ["description_too_long"]
    assert codes(type="opinion") == ["type_invalid"]
    assert codes(body="y" * 2001) == ["body_too_long"]
    assert codes(type="feedback") == ["why_how_missing"]
    assert codes(type="project", body="**Why:** a\n**How to apply:** b\n") == []


def test_skill_rules() -> None:
    skill = parse_skill((HOME / "skills/presubmission-aewv/SKILL.md").read_text())
    assert validate_skill(skill, "presubmission-aewv") == []
    assert [i.code for i in validate_skill(skill, "other")] == ["skill_name_mismatch"]
    skill.front["description"] = "z" * 301
    assert [i.code for i in validate_skill(skill, "presubmission-aewv")] == [
        "skill_description_too_long"
    ]


def test_render_index_is_byte_identical_to_the_sample_golden() -> None:
    memories, broken = load_memories(HOME)
    assert broken == []
    assert render_memory_index(memories) == (HOME / "memory/MEMORY.md").read_text()
    assert indexed_slugs((HOME / "memory/MEMORY.md").read_text()) == [
        "adviser-wants-english-findings",
        "conflicts-as-questions",
        "neutral-wording-for-discrepancies",
        "pilot-scope",
        "checklist-owner",
        "intake-form-v1-dates",
    ]


def test_title_prefers_metadata_title(home: Path) -> None:
    path = home / "memory/pilot-scope.md"
    path.write_text(path.read_text().replace("metadata:\n", "metadata:\n  title: AEWV pilot\n"))
    memories, _ = load_memories(home)
    assert [title(m) for m in memories if m.slug == "pilot-scope"] == ["AEWV pilot"]
    assert "- [AEWV pilot](pilot-scope.md) — " in "\n".join(index_lines(memories))


def test_skills_local_first_and_collisions_reported(home: Path, tmp_path: Path) -> None:
    mount = tmp_path / "mount"
    for name in ("presubmission-aewv", "write-letters"):
        (mount / name).mkdir(parents=True)
        (mount / name / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: mounted {name}\n---\n\nBody\n"
        )
    loaded = load_skills(home, [mount])
    assert [(s.name, s.read_only, s.source) for s in loaded.skills] == [
        ("case-consistency-check", False, "local"),
        ("presubmission-aewv", False, "local"),
        ("write-letters", True, str(mount)),
    ]
    assert [(p.parent.name, i.code) for p, i in loaded.issues] == [
        ("presubmission-aewv", "skill_name_collision")
    ]
    assert skill_index_lines(loaded.skills)[2] == "- write-letters — mounted write-letters"
