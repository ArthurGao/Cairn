"""Memory files and SKILL.md: parse, serialise, validate (design §4.1, §4.3).

Frontmatter is kept as the parsed mapping so keys another tool owns survive a rewrite.
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, cast

import yaml

MEMORY_TYPES = ("user", "feedback", "project", "reference")
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
MEMORY_DESCRIPTION_MAX = 150
SKILL_DESCRIPTION_MAX = 300
BODY_MAX = 2000

Severity = Literal["error", "warn", "info"]


class FormatError(ValueError):
    """The text is not frontmatter + body at all."""


@dataclass(frozen=True)
class Issue:
    code: str
    severity: Severity
    message: str


@dataclass
class Document:
    """Frontmatter mapping (order preserved) plus Markdown body."""

    front: dict[str, Any]
    body: str

    def meta(self) -> dict[str, Any]:
        value = self.front.get("metadata")
        return cast(dict[str, Any], value) if isinstance(value, dict) else {}

    @property
    def name(self) -> str:
        return str(self.front.get("name", ""))

    @property
    def description(self) -> str:
        return str(self.front.get("description", ""))


@dataclass
class MemoryFile(Document):
    @property
    def type(self) -> str:
        return str(self.meta().get("type", ""))

    @property
    def title(self) -> str | None:
        title = self.meta().get("title")
        return str(title) if title else None

    def created(self) -> date | None:
        return _as_date(self.meta().get("created"))


@dataclass
class SkillFile(Document):
    pass


def _split(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise FormatError("missing YAML frontmatter (file must start with ---)")
    head, sep, body = text[4:].partition("\n---\n")
    if not sep:
        raise FormatError("frontmatter is not closed with ---")
    try:
        front: object = yaml.safe_load(head)
    except yaml.YAMLError as exc:
        raise FormatError(f"frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(front, dict):
        raise FormatError("frontmatter must be a mapping")
    return cast(dict[str, Any], front), body.removeprefix("\n")


def parse_document(text: str) -> Document:
    """Any frontmatter + body file (run records, §4.6)."""
    return Document(*_split(text))


def parse_memory(text: str) -> MemoryFile:
    return MemoryFile(*_split(text))


def parse_skill(text: str) -> SkillFile:
    return SkillFile(*_split(text))


class _PlainDumper(yaml.SafeDumper):
    """No `&id001` anchors when two fields share a value (e.g. created == updated)."""

    def ignore_aliases(self, data: object) -> bool:
        return True


def serialise(doc: Document) -> str:
    front = yaml.dump(
        doc.front, Dumper=_PlainDumper, sort_keys=False, allow_unicode=True, width=10**9
    )
    return f"---\n{front}---\n\n{doc.body}"


def _as_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def type_rank(memory_type: str) -> int:
    """Index and list order: user, feedback, project, reference, then anything invalid."""
    return MEMORY_TYPES.index(memory_type) if memory_type in MEMORY_TYPES else len(MEMORY_TYPES)


def _one_line(value: str) -> bool:
    return "\n" not in value.strip()


def validate_memory(memory: MemoryFile, slug: str) -> list[Issue]:
    """§4.1 rules; `slug` is the file stem."""
    issues: list[Issue] = []

    def error(code: str, message: str) -> None:
        issues.append(Issue(code, "error", message))

    if memory.name != slug:
        error("name_mismatch", f"name {memory.name!r} must equal the file stem {slug!r}")
    if not NAME.match(slug) or len(slug) > NAME_MAX:
        error("name_format", f"{slug!r} must be kebab-case and at most {NAME_MAX} characters")
    description = memory.description.strip()
    if not description or not _one_line(memory.description):
        error("description_missing", "description must be one non-empty line")
    elif len(description) > MEMORY_DESCRIPTION_MAX:
        error(
            "description_too_long",
            f"description is {len(description)} characters (max {MEMORY_DESCRIPTION_MAX})",
        )
    if memory.type not in MEMORY_TYPES:
        error("type_invalid", f"metadata.type must be one of {', '.join(MEMORY_TYPES)}")
    if len(memory.body) > BODY_MAX:
        error("body_too_long", f"body is {len(memory.body)} characters (max {BODY_MAX})")
    if memory.type in ("feedback", "project") and not (
        "**Why:**" in memory.body and "**How to apply:**" in memory.body
    ):
        issues.append(
            Issue(
                "why_how_missing", "warn", f"{memory.type} memories should have Why and How lines"
            )
        )
    return issues


def validate_skill(skill: SkillFile, directory: str) -> list[Issue]:
    """§4.3 rules; `directory` is the skill's directory name."""
    issues: list[Issue] = []
    if skill.name != directory:
        issues.append(
            Issue(
                "skill_name_mismatch",
                "error",
                f"name {skill.name!r} must equal the directory {directory!r}",
            )
        )
    description = skill.description.strip()
    if not description or not _one_line(skill.description):
        issues.append(Issue("skill_description_missing", "error", "description must be one line"))
    elif len(description) > SKILL_DESCRIPTION_MAX:
        issues.append(
            Issue(
                "skill_description_too_long",
                "error",
                f"description is {len(description)} characters (max {SKILL_DESCRIPTION_MAX})",
            )
        )
    return issues
