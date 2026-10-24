import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cairn.activities.cases import CaseActivities
from cairn.core.cases import store
from cairn.llm.client import LlmClient, build_client
from cairn.llm.prompts import load_prompt
from cairn.llm.roles import ConfigError, Role, RoleConfig, data_class_problem, load_roles
from cairn.llm.types import LlmError, LlmRequest, Message
from cairn.llm.vendors.fake import FakeVendor
from cairn.settings import role_env
from cairn.worker import validate_startup
from cairn.workflows.case_models import IngestInput
from tests.support import make_settings

ROLES = Path(__file__).parents[2] / "config" / "roles.toml"
NOW = datetime(2026, 10, 24, tzinfo=UTC)


def test_roles_file_defaults_every_role_to_the_gateway() -> None:
    roles = load_roles(ROLES, env={})
    assert set(roles) == set(Role)
    assert {(c.vendor, c.model) for c in roles.values()} == {
        ("gateway", "anthropic/claude-sonnet-5.5")
    }
    assert roles[Role.DOCUMENT_TRANSCRIBE].effort == "low"


def test_env_overrides_per_field_and_vendor_override() -> None:
    env = {
        "CAIRN_ROLE_MEMORY_CONSOLIDATE_MODEL": "openai/gpt-5.4-mini",
        "CAIRN_ROLE_CASE_EXTRACT_FACTS_MAX_TOKENS": "24000",
    }
    roles = load_roles(ROLES, env)
    assert roles[Role.MEMORY_CONSOLIDATE].model == "openai/gpt-5.4-mini"
    assert roles[Role.CASE_EXTRACT_FACTS].max_tokens == 24000
    assert {c.vendor for c in load_roles(ROLES, env, "fake").values()} == {"fake"}


def test_role_overrides_in_the_env_file_apply_and_the_process_env_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CAIRN_ROLE_AGENT_MAIN_MODEL=openai/gpt-5.2\n"
        "CAIRN_ROLE_MEMORY_CONSOLIDATE_MODEL=openai/gpt-5-mini\n"
    )
    monkeypatch.setenv("CAIRN_ROLE_MEMORY_CONSOLIDATE_MODEL", "openai/gpt-5-nano")
    roles = load_roles(ROLES, role_env(env_file))
    assert roles[Role.AGENT_MAIN].model == "openai/gpt-5.2"
    assert roles[Role.MEMORY_CONSOLIDATE].model == "openai/gpt-5-nano"
    assert roles[Role.CASE_CHECK_ITEM].model == "anthropic/claude-sonnet-5.5"


def test_invalid_role_config_is_a_config_error() -> None:
    with pytest.raises(ConfigError, match=r"role case\.check_item"):
        load_roles(ROLES, {"CAIRN_ROLE_CASE_CHECK_ITEM_EFFORT": "maximum"})


def _roles(vendor: str) -> dict[Role, RoleConfig]:
    return {r: RoleConfig(vendor=vendor, model="m", max_tokens=10) for r in Role}


def test_data_class_gate() -> None:
    assert data_class_problem(_roles("gateway"), "synthetic", "") is None
    assert data_class_problem(_roles("fake"), "client", "") is None
    problem = data_class_problem(
        _roles("gateway"), "client", "gateway,anthropic", (Role.CASE_CHECK_ITEM,)
    )
    assert problem == (
        "client data may only go to allow-listed vendors (CAIRN_CLIENT_DATA_VENDORS); "
        "not allowed: case.check_item -> gateway"
    )
    assert data_class_problem(_roles("azure"), "client", "azure") is None


def test_worker_refuses_to_start_with_client_data_on_the_gateway(tmp_path: Path) -> None:
    settings = make_settings(tmp_path / "h", tmp_path / "c", data_class="client")
    client = LlmClient(_roles("gateway"), {"gateway": FakeVendor.__new__(FakeVendor)})
    with pytest.raises(ConfigError, match="refusing to start: client data may only go"):
        validate_startup(settings, client)


def _scenario(tmp_path: Path, entries: list[dict[str, object]]) -> Path:
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(entries))
    return path


async def test_fake_scenario_files_are_read_in_order(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = _scenario(tmp_path / "a", [{"role": "agent.main", "reply": {"text": "from a"}}])
    second = _scenario(tmp_path / "b", [{"role": "agent.main", "reply": {"text": "from b"}}])
    settings = make_settings(
        tmp_path / "h", tmp_path / "c", llm_vendor="fake", fake_scenario=f"{first}:{second}"
    )
    client = build_client(settings, env={})
    ask = LlmRequest(role=Role.AGENT_MAIN, messages=[Message.user("x")])
    assert [(await client.call(ask)).text for _ in range(2)] == ["from a", "from b"]


async def test_fake_vendor_matches_consumes_and_fails_loudly(tmp_path: Path) -> None:
    fake = FakeVendor(
        _scenario(
            tmp_path,
            [
                {"role": "case.check_item", "match": "alpha", "reply": {"text": "A"}},
                {"role": "case.check_item", "reply": {"text": "any"}, "repeat": True},
            ],
        )
    )
    config = RoleConfig(vendor="fake", model="m", max_tokens=10)

    def ask(text: str) -> LlmRequest:
        return LlmRequest(role=Role.CASE_CHECK_ITEM, messages=[Message.user(text)])

    assert (await fake.complete(config, ask("say alpha"))).text == "A"
    assert (await fake.complete(config, ask("say alpha"))).text == "any"  # first one used up
    assert (await fake.complete(config, ask("other"))).text == "any"
    with pytest.raises(LlmError, match=r"no scenario entry for role memory\.extract"):
        await fake.complete(
            config, LlmRequest(role=Role.MEMORY_EXTRACT, messages=[Message.user("x")])
        )


async def test_client_rejects_cut_off_and_missing_structured_output(tmp_path: Path) -> None:
    fake = FakeVendor(
        _scenario(
            tmp_path,
            [
                {
                    "role": "case.check_item",
                    "match": "cut",
                    "reply": {"stop_reason": "max_tokens", "data": {}},
                },
                {"role": "case.check_item", "match": "none", "reply": {"text": "prose"}},
            ],
        )
    )
    client = LlmClient(_roles("fake"), {"fake": fake})

    def ask(text: str) -> LlmRequest:
        return LlmRequest(
            role=Role.CASE_CHECK_ITEM, messages=[Message.user(text)], output_schema={}
        )

    with pytest.raises(LlmError) as info:
        await client.call(ask("cut"))
    assert (info.value.code, info.value.retryable) == ("max_tokens", False)
    with pytest.raises(LlmError) as info:
        await client.call(ask("none"))
    assert info.value.code == "schema"


def test_client_needs_every_configured_vendor() -> None:
    with pytest.raises(ConfigError, match="vendor 'gateway' is not available"):
        LlmClient(_roles("gateway"), {})


def test_fake_vendor_needs_a_scenario(tmp_path: Path) -> None:
    settings = make_settings(tmp_path / "h", tmp_path / "c", llm_vendor="fake")
    with pytest.raises(ConfigError, match="CAIRN_FAKE_SCENARIO"):
        build_client(settings, env={})


def test_prompts_are_versioned() -> None:
    for name in (
        "document_transcribe",
        "case_extract_facts",
        "case_compare_facts",
        "case_check_item",
    ):
        version, text = load_prompt(name)
        assert (name, version) == (name, "1")
        assert not text.startswith("<!--")


async def test_ingest_failures_are_recorded_not_raised(
    home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    settings = make_settings(
        home, cases_dir, llm_vendor="fake", fake_scenario=_scenario(tmp_path, [])
    )
    acts = CaseActivities(settings, build_client(settings, env={}))
    store.create_case(cases_dir, "C1", "x", "synthetic", NOW)
    limits = store.CaseLimits(max_documents=10, max_file_bytes=10_000_000)
    store.add_document(cases_dir, "C1", "bad", "bad.pdf", b"%PDF-1.4 not really", NOW, limits)
    store.add_document(
        cases_dir, "C1", "notes", "notes.md", b"# Notes\nCall the client.", NOW, limits
    )
    sample = Path(__file__).parents[1] / "fixtures/cases/aewv-sample/questionnaire.pdf"
    store.add_document(cases_dir, "C1", "big", "q.pdf", sample.read_bytes(), NOW, limits)

    def job(doc_id: str, max_pages: int = 500) -> IngestInput:
        return IngestInput(
            case_id="C1", doc_id=doc_id, min_page_chars=40, max_pages_per_case=max_pages
        )

    bad = await acts.ingest_document(job("bad"))
    assert (
        bad.status,
        bad.error is not None and bad.error.startswith("bad.pdf is not a readable PDF"),
    ) == ("failed", True)
    notes = await acts.ingest_document(job("notes"))
    assert (notes.status, notes.pages) == ("ingested", 1)
    assert store.read_page(cases_dir, "C1", "notes", 1).text == "# Notes\nCall the client."
    too_many = await acts.ingest_document(job("big", max_pages=2))
    assert (too_many.status, too_many.error) == (
        "failed",
        "q.pdf has 2 pages; the case limit is 2 pages",
    )
    statuses = {d.doc_id: d.status for d in store.load_manifest(cases_dir, "C1").documents}
    assert statuses == {"bad": "failed", "notes": "ingested", "big": "failed"}


async def test_scanned_pdf_page_is_transcribed_and_ingest_is_idempotent(
    home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    from reportlab.pdfgen.canvas import Canvas

    pdf = tmp_path / "scan.pdf"
    canvas = Canvas(str(pdf), invariant=1)
    canvas.drawString(56, 800, "Bank statement - page 1 of 2, account summary")
    canvas.showPage()
    canvas.drawString(56, 800, "p2")  # under 40 characters: treated as a scanned page
    canvas.showPage()
    canvas.save()
    scenario = _scenario(
        tmp_path,
        [
            {
                "role": "document.transcribe",
                "match": "Document: scan.pdf | page 2",
                "reply": {"data": {"readable": True, "text": "Closing balance 1,204.50"}},
            }
        ],
    )
    settings = make_settings(home, cases_dir, llm_vendor="fake", fake_scenario=scenario)
    acts = CaseActivities(settings, build_client(settings, env={}))
    store.create_case(cases_dir, "C1", "x", "synthetic", NOW)
    limits = store.CaseLimits(max_documents=10, max_file_bytes=10_000_000)
    store.add_document(cases_dir, "C1", "scan", "scan.pdf", pdf.read_bytes(), NOW, limits)
    job = IngestInput(case_id="C1", doc_id="scan", min_page_chars=40, max_pages_per_case=500)
    first = await acts.ingest_document(job)
    assert (first.status, first.pages, [c.role for c in first.calls]) == (
        "ingested",
        2,
        ["document.transcribe"],
    )
    methods = [p.method for p in store.load_manifest(cases_dir, "C1").documents[0].pages]
    assert methods == ["text", "transcribed"]
    assert store.read_page(cases_dir, "C1", "scan", 2).text == "Closing balance 1,204.50"
    # A retried activity must not call the model again (the scenario entry is used up).
    again = await acts.ingest_document(job)
    assert (again.status, again.pages, again.calls) == ("ingested", 2, [])


async def test_ingest_retry_reuses_pages_already_written(
    home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    from cairn.core.cases.models import Page

    settings = make_settings(
        home, cases_dir, llm_vendor="fake", fake_scenario=_scenario(tmp_path, [])
    )
    acts = CaseActivities(settings, build_client(settings, env={}))
    store.create_case(cases_dir, "C1", "x", "synthetic", NOW)
    limits = store.CaseLimits(max_documents=10, max_file_bytes=10_000_000)
    png = Path(__file__).parents[1] / "fixtures/cases/aewv-sample/passport-scan.png"
    doc = store.add_document(cases_dir, "C1", "pp", "pp.png", png.read_bytes(), NOW, limits)
    # An earlier attempt transcribed the page, then died before updating the manifest.
    store.write_pages(
        cases_dir,
        "C1",
        [Page(doc_id="pp", page=1, method="transcribed", source_sha256=doc.sha256, text="SAMPLE")],
    )
    job = IngestInput(case_id="C1", doc_id="pp", min_page_chars=40, max_pages_per_case=500)
    outcome = await acts.ingest_document(job)  # the empty scenario fails any model call
    assert (outcome.status, outcome.pages, outcome.calls) == ("ingested", 1, [])
    assert store.read_page(cases_dir, "C1", "pp", 1).text == "SAMPLE"


async def test_domain_errors_are_not_retried(home: Path, cases_dir: Path, tmp_path: Path) -> None:
    from temporalio.exceptions import ApplicationError

    from cairn.workflows.case_models import ExtractInput

    settings = make_settings(
        home, cases_dir, llm_vendor="fake", fake_scenario=_scenario(tmp_path, [])
    )
    acts = CaseActivities(settings, build_client(settings, env={}))
    with pytest.raises(ApplicationError) as info:
        await acts.extract_facts(ExtractInput(case_id="nope", doc_id="d", map_budget=10))
    assert (info.value.type, info.value.non_retryable) == ("case_not_found", True)


async def test_oversized_pages_are_not_rendered(
    home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    from reportlab.pdfgen.canvas import Canvas

    pdf = tmp_path / "poster.pdf"
    canvas = Canvas(str(pdf), pagesize=(14000, 14000), invariant=1)  # ~194 in square, no text
    canvas.showPage()
    canvas.save()
    settings = make_settings(
        home, cases_dir, llm_vendor="fake", fake_scenario=_scenario(tmp_path, [])
    )
    acts = CaseActivities(settings, build_client(settings, env={}))
    store.create_case(cases_dir, "C1", "x", "synthetic", NOW)
    limits = store.CaseLimits(max_documents=10, max_file_bytes=10_000_000)
    store.add_document(cases_dir, "C1", "poster", "poster.pdf", pdf.read_bytes(), NOW, limits)
    job = IngestInput(case_id="C1", doc_id="poster", min_page_chars=40, max_pages_per_case=500)
    outcome = await acts.ingest_document(job)  # the empty scenario fails any model call
    assert (outcome.status, outcome.calls) == ("ingested", [])
    page = store.read_page(cases_dir, "C1", "poster", 1)
    assert (page.method, page.reason) == (
        "unreadable",
        "page is too large to render (14000 x 14000 pt)",
    )


async def test_fake_replies_resolve_document_placeholders(tmp_path: Path) -> None:
    fake = FakeVendor(
        _scenario(
            tmp_path,
            [
                {
                    "role": "case.check_item",
                    "reply": {
                        "data": {"results": [{"doc_id": "{{doc:passport-scan.png}}", "n": 1}]}
                    },
                }
            ],
        )
    )
    request = LlmRequest(
        role=Role.CASE_CHECK_ITEM,
        messages=[
            Message.user("=== document 01ULIDXYZ (passport-scan.png) | page 1 ===\nPassport")
        ],
    )
    result = await fake.complete(RoleConfig(vendor="fake", model="m", max_tokens=10), request)
    assert result.data == {"results": [{"doc_id": "01ULIDXYZ", "n": 1}]}
