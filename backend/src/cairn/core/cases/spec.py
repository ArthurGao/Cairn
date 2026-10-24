"""Parse the files advisers maintain: fact categories and pre-submission checklists (§4.3)."""

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from cairn.errors import Invalid

FACT_CATEGORIES = Path("references/fact-categories.md")
CHECKLIST = Path("references/checklist.yaml")
PRESUBMISSION_PREFIX = "presubmission-"

Kind = Literal["date", "period", "text"]
_PREFIX_KINDS: tuple[Kind, ...] = ("period", "date")
_ROW = re.compile(r"^\|\s*`(?P<id>[a-z_.]+)`\s*\|(?P<cells>.*)\|\s*$")


class SpecInvalid(Invalid):
    code = "spec_invalid"


def _reject_duplicates(ids: Iterable[str], what: str) -> None:
    if duplicates := sorted(i for i, n in Counter(ids).items() if n > 1):
        raise SpecInvalid(f"duplicate {what}: {', '.join(duplicates)}")


# --- fact categories ------------------------------------------------------------------------


@dataclass(frozen=True)
class Category:
    id: str
    kind: Kind


def parse_categories(text: str) -> list[Category]:
    """Rows whose first cell is a backticked id; the Normalised column gives the kind."""
    categories: list[Category] = []
    for line in text.splitlines():
        match = _ROW.match(line.strip())
        if not match:
            continue
        cells = [c.strip() for c in match["cells"].split("|")]
        if len(cells) < 2:
            raise SpecInvalid(f"category {match['id']}: row has no Normalised column")
        categories.append(Category(match["id"], _kind(cells[1].lower())))
    if not categories:
        raise SpecInvalid("fact-categories.md lists no categories")
    _reject_duplicates((c.id for c in categories), "fact categories")
    return categories


def _kind(normalised: str) -> Kind:
    """The Normalised column starts with the kind: "period + text" is a period."""
    for kind in _PREFIX_KINDS:
        if normalised.startswith(kind):
            return kind
    return "text"


def load_categories(skill_dir: Path) -> list[Category]:
    return parse_categories((skill_dir / FACT_CATEGORIES).read_text(encoding="utf-8"))


def kinds_by_id(categories: Sequence[Category]) -> dict[str, Kind]:
    return {c.id: c.kind for c in categories}


# --- checklists -----------------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
        str_min_length=1,
        coerce_numbers_to_str=True,
    )


class ChecklistItem(_Strict):
    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    requirement: str
    verify: str


class Checklist(_Strict):
    visa: str
    version: str
    owner: str
    items: tuple[ChecklistItem, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        _reject_duplicates((i.id for i in self.items), "checklist item ids")
        return self


@dataclass(frozen=True)
class ChecklistInfo:
    skill: str
    checklist: Checklist | None
    error: str | None


def parse_checklist(text: str) -> Checklist:
    try:
        data: object = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SpecInvalid(f"checklist.yaml is not valid YAML: {exc}") from exc
    try:
        return Checklist.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or 'checklist'}: {e['msg']}" for e in exc.errors()
        )
        raise SpecInvalid(f"checklist.yaml: {problems}") from exc


def load_checklist(skill_dir: Path) -> Checklist:
    return parse_checklist((skill_dir / CHECKLIST).read_text(encoding="utf-8"))


def list_checklists(skills_root: Path) -> list[ChecklistInfo]:
    """Every `presubmission-*` skill under `skills_root`, valid or not, sorted by name."""
    infos: list[ChecklistInfo] = []
    for skill_dir in sorted(skills_root.glob(f"{PRESUBMISSION_PREFIX}*")):
        if not skill_dir.is_dir():
            continue
        try:
            infos.append(ChecklistInfo(skill_dir.name, load_checklist(skill_dir), None))
        except (SpecInvalid, OSError) as exc:
            infos.append(ChecklistInfo(skill_dir.name, None, str(exc)))
    return infos
