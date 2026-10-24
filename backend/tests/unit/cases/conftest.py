import json

import pytest

from cairn.core.cases.facts import validate_facts
from cairn.core.cases.models import Fact, RawFact
from cairn.core.cases.spec import Category, load_categories
from tests.fixtures.cases.make_cases import DOCS
from tests.support import FIXTURES

SAMPLE = FIXTURES / "cases" / "aewv-sample"
SKILLS = FIXTURES / "home" / "skills"


def page_texts(filename: str) -> dict[int, str]:
    return {n: "\n".join(lines) for n, lines in enumerate(DOCS[filename], start=1)}


@pytest.fixture(scope="session")
def categories() -> list[Category]:
    return load_categories(SKILLS / "case-consistency-check")


@pytest.fixture(scope="session")
def expected() -> dict[str, object]:
    return json.loads((SAMPLE / "expected.json").read_text())


@pytest.fixture(scope="session")
def sample_facts(categories: list[Category]) -> list[Fact]:
    """The sample extraction, validated document by document as the workflow will do it."""
    raw = json.loads((SAMPLE / "facts.json").read_text())
    facts: list[Fact] = []
    for doc_id, items in raw.items():
        if doc_id.startswith("_"):
            continue
        accepted, dropped = validate_facts(
            doc_id,
            [RawFact.model_validate(i) for i in items],
            page_texts(f"{doc_id}.pdf"),
            categories,
            first_id=len(facts) + 1,
        )
        assert dropped == []
        facts.extend(accepted)
    return facts
