"""Load a harness home's memories and skills; render the indexes (design §3.1, §4.2, §4.3)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from cairn.core.formats import (
    MEMORY_TYPES,
    NAME,
    NAME_MAX,
    FormatError,
    Issue,
    MemoryFile,
    SkillFile,
    parse_memory,
    parse_skill,
    validate_memory,
    validate_skill,
)
from cairn.errors import Invalid

MEMORY_DIR = "memory"
INDEX_FILE = "MEMORY.md"
INDEX_HEADING = "# Memory\n"
_INDEX_LINE = re.compile(r"^- \[(?P<title>[^\]]*)\]\((?P<slug>[^)]+)\.md\) — (?P<description>.*)$")


@dataclass(frozen=True)
class Memory:
    slug: str
    file: MemoryFile
    text: str


@dataclass(frozen=True)
class Broken:
    """A file that could not be parsed at all."""

    path: Path
    error: str


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path  # the skill directory
    file: SkillFile
    read_only: bool
    source: str  # "local" or the mounted root


def checked_slug(slug: str) -> str:
    """Slugs become file names: only kebab-case passes (no separators, dots or `_` files)."""
    if not NAME.match(slug) or len(slug) > NAME_MAX:
        raise Invalid(f"{slug!r} is not a valid memory slug", code="invalid_slug")
    return slug


def memory_path(home: Path, slug: str) -> Path:
    return home / MEMORY_DIR / f"{checked_slug(slug)}.md"


def archive_path(home: Path, slug: str) -> Path:
    return home / MEMORY_DIR / "_archive" / f"{checked_slug(slug)}.md"


def index_path(home: Path) -> Path:
    return home / MEMORY_DIR / INDEX_FILE


def load_memories(home: Path) -> tuple[list[Memory], list[Broken]]:
    """Live memories (not the index, not `_`-prefixed files), sorted by slug."""
    memories: list[Memory] = []
    broken: list[Broken] = []
    for path in sorted((home / MEMORY_DIR).glob("*.md")):
        if path.name == INDEX_FILE or path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        try:
            memories.append(Memory(path.stem, parse_memory(text), text))
        except FormatError as exc:
            broken.append(Broken(path, str(exc)))
    return memories, broken


def memory_issues(memories: Sequence[Memory]) -> dict[str, list[Issue]]:
    return {m.slug: issues for m in memories if (issues := validate_memory(m.file, m.slug))}


def title(memory: Memory) -> str:
    if memory.file.title:
        return memory.file.title
    words = memory.slug.replace("-", " ")
    return words[:1].upper() + words[1:]


def _type_rank(memory: Memory) -> int:
    return MEMORY_TYPES.index(memory.file.type) if memory.file.type in MEMORY_TYPES else 99


def index_lines(memories: Sequence[Memory]) -> list[str]:
    """One line per memory, ordered by type (user, feedback, project, reference) then slug."""
    ordered = sorted(memories, key=lambda m: (_type_rank(m), m.slug))
    return [f"- [{title(m)}]({m.slug}.md) — {m.file.description.strip()}" for m in ordered]


def render_memory_index(memories: Sequence[Memory]) -> str:
    return INDEX_HEADING + "\n" + "".join(f"{line}\n" for line in index_lines(memories))


def indexed_slugs(index_text: str) -> list[str]:
    return [m["slug"] for line in index_text.splitlines() if (m := _INDEX_LINE.match(line))]


def read_index(home: Path) -> str:
    path = index_path(home)
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def index_current(home: Path) -> tuple[bool, str]:
    """(MEMORY.md equals the rendering of the files, that rendering)."""
    rendered = render_memory_index(load_memories(home)[0])
    return read_index(home) == rendered, rendered


# --- skills ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillLoad:
    skills: list[Skill]
    issues: list[tuple[Path, Issue]]


def load_skills(home: Path, mounts: Sequence[Path] = ()) -> SkillLoad:
    """Local skills first, then read-only mounts; a name already seen is reported, not loaded."""
    seen: dict[str, Skill] = {}
    issues: list[tuple[Path, Issue]] = []
    sources = [(home / "skills", False, "local"), *((m, True, str(m)) for m in mounts)]
    for root, read_only, source in sources:
        for skill_md in sorted(root.glob("*/SKILL.md")):
            directory = skill_md.parent
            try:
                parsed = parse_skill(skill_md.read_text(encoding="utf-8"))
            except FormatError as exc:
                issues.append((skill_md, Issue("skill_unparseable", "error", str(exc))))
                continue
            issues.extend((skill_md, issue) for issue in validate_skill(parsed, directory.name))
            if directory.name in seen:
                issues.append(
                    (
                        skill_md,
                        Issue(
                            "skill_name_collision",
                            "error",
                            f"{directory.name} is also at {seen[directory.name].path}; "
                            "the first one wins (local before mounts)",
                        ),
                    )
                )
                continue
            seen[directory.name] = Skill(directory.name, directory, parsed, read_only, source)
    return SkillLoad(list(seen.values()), issues)


def skill_index_lines(skills: Sequence[Skill]) -> list[str]:
    return [
        f"- {s.name} — {s.file.description.strip()}" for s in sorted(skills, key=lambda s: s.name)
    ]
