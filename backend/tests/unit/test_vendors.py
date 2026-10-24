"""Vendor adapters against a mocked HTTP layer (design §10.3, §14): exact request bodies,
result parsing, stop reasons and error classes. No network."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx2
import pytest
from pydantic import BaseModel, Field

from cairn.llm.client import build_client
from cairn.llm.roles import ConfigError, Role, RoleConfig, load_roles
from cairn.llm.schema import strict_schema
from cairn.llm.types import (
    ImagePart,
    LlmError,
    LlmRequest,
    Message,
    TextPart,
    ToolResultPart,
    ToolSpec,
    ToolUsePart,
)
from cairn.llm.validate import model_problems, validate_models
from cairn.llm.vendors.anthropic import AnthropicAdapter
from cairn.llm.vendors.gateway import GatewayVendor
from tests.support import make_settings

KEY = "test-key-not-real"
SONNET = RoleConfig(
    vendor="gateway", model="anthropic/claude-sonnet-5.5", effort="low", max_tokens=900
)
GPT = RoleConfig(vendor="gateway", model="openai/gpt-5.4-mini", effort="medium", max_tokens=700)


class Answer(BaseModel):
    readable: bool
    text: str = ""
    score: int = Field(default=0, ge=0, le=5)
    note: str | None = None


Seen = list[httpx2.Request]


def _http(reply: Callable[[httpx2.Request], httpx2.Response], seen: Seen) -> httpx2.AsyncClient:
    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return reply(request)

    return httpx2.AsyncClient(transport=httpx2.MockTransport(handler))


def _anthropic_reply(content: list[dict[str, Any]], stop: str = "end_turn") -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "claude-sonnet-5-5",
            "content": content,
            "stop_reason": stop,
            "stop_sequence": None,
            "usage": {"input_tokens": 120, "output_tokens": 30},
        },
    )


def _openai_reply(message: dict[str, Any], finish: str = "stop") -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "id": "c1",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-5.4-mini",
            "choices": [
                {"index": 0, "message": {"role": "assistant", **message}, "finish_reason": finish}
            ],
            "usage": {"prompt_tokens": 110, "completion_tokens": 25, "total_tokens": 135},
        },
    )


def _request(**kw: Any) -> LlmRequest:
    base: dict[str, Any] = {
        "role": Role.DOCUMENT_TRANSCRIBE,
        "system": "Transcribe the page.",
        "messages": [
            Message.user(
                TextPart(text="Case pages: ...", cache=True),
                ImagePart(data_b64="aW1n"),
                "Document: scan.pdf | page 2",
            )
        ],
        "output_schema": Answer.model_json_schema(),
        "prompt_version": "1",
    }
    return LlmRequest.model_validate(base | kw)


def test_strict_schema_closes_objects_and_drops_bounds() -> None:
    assert strict_schema(Answer.model_json_schema()) == {
        "type": "object",
        "properties": {
            "readable": {"type": "boolean"},
            "text": {"type": "string"},
            "score": {"type": "integer"},
            "note": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
        "required": ["readable", "text", "score", "note"],
        "additionalProperties": False,
    }


async def test_gateway_claude_uses_anthropic_messages_natively() -> None:
    seen: Seen = []
    http = _http(
        lambda _: _anthropic_reply(
            [{"type": "text", "text": '{"readable": true, "text": "Balance 12"}'}]
        ),
        seen,
    )
    result = await GatewayVendor(KEY, http).complete(SONNET, _request())
    [sent] = seen
    assert str(sent.url) == "https://ai-gateway.vercel.sh/v1/messages"
    assert sent.headers["authorization"] == f"Bearer {KEY}"
    body = json.loads(sent.content)
    assert body["model"] == "anthropic/claude-sonnet-5.5"
    assert body["max_tokens"] == 900
    assert body["system"] == "Transcribe the page."
    assert body["output_config"] == {
        "effort": "low",
        "format": {"type": "json_schema", "schema": strict_schema(Answer.model_json_schema())},
    }
    assert body["messages"] == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Case pages: ...", "cache_control": {"type": "ephemeral"}},
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": "aW1n"},
                },
                {"type": "text", "text": "Document: scan.pdf | page 2"},
            ],
        }
    ]
    assert (result.vendor, result.model, result.data, result.stop_reason) == (
        "gateway",
        "anthropic/claude-sonnet-5.5",
        {"readable": True, "text": "Balance 12"},
        "end",
    )
    assert (result.tokens_in, result.tokens_out) == (120, 30)


async def test_gateway_gpt_uses_chat_completions_natively() -> None:
    seen: Seen = []
    http = _http(
        lambda _: _openai_reply({"content": '{"readable": false, "text": ""}', "refusal": None}),
        seen,
    )
    result = await GatewayVendor(KEY, http).complete(GPT, _request())
    [sent] = seen
    assert str(sent.url) == "https://ai-gateway.vercel.sh/v1/chat/completions"
    assert sent.headers["authorization"] == f"Bearer {KEY}"
    body = json.loads(sent.content)
    assert body["model"] == "openai/gpt-5.4-mini"
    assert body["max_completion_tokens"] == 700
    assert "max_tokens" not in body
    assert body["reasoning_effort"] == "medium"
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "output",
            "schema": strict_schema(Answer.model_json_schema()),
            "strict": True,
        },
    }
    assert body["messages"] == [
        {"role": "system", "content": "Transcribe the page."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Case pages: ..."},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,aW1n"}},
                {"type": "text", "text": "Document: scan.pdf | page 2"},
            ],
        },
    ]
    assert (result.data, result.tokens_in, result.tokens_out) == (
        {"readable": False, "text": ""},
        110,
        25,
    )


async def test_empty_system_is_never_sent() -> None:
    seen: Seen = []
    plain = _request(system="", output_schema=None)
    await GatewayVendor(KEY, _http(lambda _: _openai_reply({"content": "ok"}), seen)).complete(
        GPT, plain
    )
    await GatewayVendor(
        KEY, _http(lambda _: _anthropic_reply([{"type": "text", "text": "ok"}]), seen)
    ).complete(SONNET, plain)
    openai_body, anthropic_body = (json.loads(r.content) for r in seen)
    assert [m["role"] for m in openai_body["messages"]] == ["user"]
    assert "system" not in anthropic_body
    assert "format" not in anthropic_body["output_config"]


async def test_tool_use_round_trip_on_both_protocols() -> None:
    tools = [
        ToolSpec(
            name="read_memory",
            description="Read one memory",
            parameters={"type": "object", "properties": {"slug": {"type": "string"}}},
        )
    ]
    history = [
        Message.user("What is the pilot scope?"),
        Message(
            role="assistant",
            content=[ToolUsePart(id="t1", name="read_memory", args={"slug": "pilot-scope"})],
        ),
        Message(role="user", content=[ToolResultPart(tool_use_id="t1", content="AEWV only")]),
    ]
    request = LlmRequest(role=Role.AGENT_MAIN, messages=history, tools=tools)
    seen: Seen = []
    claude = GatewayVendor(
        KEY,
        _http(
            lambda _: _anthropic_reply(
                [
                    {
                        "type": "tool_use",
                        "id": "t2",
                        "name": "read_memory",
                        "input": {"slug": "checklist-owner"},
                    }
                ],
                "tool_use",
            ),
            seen,
        ),
    )
    result = await claude.complete(SONNET, request)
    assert (result.stop_reason, result.tool_calls) == (
        "tool_use",
        [ToolUsePart(id="t2", name="read_memory", args={"slug": "checklist-owner"})],
    )
    body = json.loads(seen[0].content)
    assert body["tools"] == [
        {
            "name": "read_memory",
            "description": "Read one memory",
            "input_schema": tools[0].parameters,
        }
    ]
    assert body["messages"][1]["content"] == [
        {"type": "tool_use", "id": "t1", "name": "read_memory", "input": {"slug": "pilot-scope"}}
    ]
    assert body["messages"][2]["content"] == [
        {"type": "tool_result", "tool_use_id": "t1", "content": "AEWV only"}
    ]

    gpt = GatewayVendor(
        KEY,
        _http(
            lambda _: _openai_reply(
                {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "t2",
                            "type": "function",
                            "function": {
                                "name": "read_memory",
                                "arguments": '{"slug": "checklist-owner"}',
                            },
                        }
                    ],
                },
                "tool_calls",
            ),
            seen,
        ),
    )
    result = await gpt.complete(GPT, request)
    assert (result.stop_reason, result.tool_calls[0].args) == (
        "tool_use",
        {"slug": "checklist-owner"},
    )
    body = json.loads(seen[1].content)
    assert (
        body["messages"][1:]
        == [
            {"role": "user", "content": [{"type": "text", "text": "What is the pilot scope?"}]},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "t1",
                        "type": "function",
                        "function": {"name": "read_memory", "arguments": '{"slug": "pilot-scope"}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "t1", "content": "AEWV only"},
        ][1:]
    )
    assert body["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "read_memory",
                "description": "Read one memory",
                "parameters": tools[0].parameters,
            },
        }
    ]


async def test_cut_off_replies_report_max_tokens() -> None:
    seen: Seen = []
    claude = GatewayVendor(
        KEY,
        _http(
            lambda _: _anthropic_reply([{"type": "text", "text": '{"readab'}], "max_tokens"), seen
        ),
    )
    gpt = GatewayVendor(
        KEY, _http(lambda _: _openai_reply({"content": '{"readab'}, "length"), seen)
    )
    assert (await claude.complete(SONNET, _request())).stop_reason == "max_tokens"
    assert (await gpt.complete(GPT, _request())).stop_reason == "max_tokens"


def _error(status: int, body: dict[str, Any]) -> Callable[[httpx2.Request], httpx2.Response]:
    return lambda _: httpx2.Response(status, json=body)


@pytest.mark.parametrize(
    ("status", "body", "code", "retryable"),
    [
        (
            429,
            {"type": "error", "error": {"type": "rate_limit_error", "message": "slow down"}},
            "rate_limited",
            True,
        ),
        (
            529,
            {"type": "error", "error": {"type": "overloaded_error", "message": "busy"}},
            "server",
            True,
        ),
        (402, {"error": {"message": "budget exceeded"}}, "budget", False),
        (
            400,
            {
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": "Your credit balance is too low",
                },
            },
            "no_credit",
            False,
        ),
        (
            401,
            {"type": "error", "error": {"type": "authentication_error", "message": "bad key"}},
            "rejected",
            False,
        ),
    ],
)
async def test_anthropic_error_classes(
    status: int, body: dict[str, Any], code: str, retryable: bool
) -> None:
    vendor = GatewayVendor(KEY, _http(_error(status, body), []))
    with pytest.raises(LlmError) as info:
        await vendor.complete(SONNET, _request())
    assert (info.value.code, info.value.retryable) == (code, retryable)


@pytest.mark.parametrize(
    ("status", "body", "code", "retryable"),
    [
        (
            429,
            {
                "error": {
                    "message": "quota",
                    "type": "insufficient_quota",
                    "code": "insufficient_quota",
                }
            },
            "no_credit",
            False,
        ),
        (
            429,
            {"error": {"message": "slow down", "type": "requests", "code": "rate_limit_exceeded"}},
            "rate_limited",
            True,
        ),
        (502, {"error": {"message": "bad gateway"}}, "server", True),
        (400, {"error": {"message": "bad schema"}}, "rejected", False),
    ],
)
async def test_openai_error_classes(
    status: int, body: dict[str, Any], code: str, retryable: bool
) -> None:
    vendor = GatewayVendor(KEY, _http(_error(status, body), []))
    with pytest.raises(LlmError) as info:
        await vendor.complete(GPT, _request())
    assert (info.value.code, info.value.retryable) == (code, retryable)


async def test_connection_errors_are_retryable() -> None:
    def boom(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    vendor = GatewayVendor(KEY, httpx2.AsyncClient(transport=httpx2.MockTransport(boom)))
    for config in (SONNET, GPT):
        with pytest.raises(LlmError) as info:
            await vendor.complete(config, _request())
        assert (info.value.code, info.value.retryable) == ("connection", True)


async def test_direct_anthropic_uses_its_own_url_and_ids() -> None:
    seen: Seen = []
    direct = AnthropicAdapter(
        "anthropic",
        KEY,
        None,
        _http(lambda _: _anthropic_reply([{"type": "text", "text": "{}"}]), seen),
    )
    config = RoleConfig(vendor="anthropic", model="claude-sonnet-5-5", max_tokens=100)
    await direct.complete(config, _request(output_schema=None))
    [sent] = seen
    assert str(sent.url) == "https://api.anthropic.com/v1/messages"
    assert sent.headers["authorization"] == f"Bearer {KEY}"
    assert json.loads(sent.content)["model"] == "claude-sonnet-5-5"


def _listing() -> dict[str, Any]:
    return {
        "data": [
            {
                "id": "anthropic/claude-sonnet-5.5",
                "tags": ["tool-use", "structured-output", "vision"],
            },
            {"id": "openai/gpt-5.4-mini", "tags": ["tool-use", "structured-output", "vision"]},
            {"id": "openai/gpt-oss-120b", "tags": ["tool-use", "structured-output"]},
        ]
    }


def test_model_problems_name_each_role() -> None:
    roles = load_roles(Path(__file__).parents[2] / "config/roles.toml", {})
    assert model_problems(roles, {m["id"]: set(m["tags"]) for m in _listing()["data"]}) == []
    roles[Role.DOCUMENT_TRANSCRIBE] = RoleConfig(
        vendor="gateway", model="openai/gpt-oss-120b", max_tokens=10
    )
    roles[Role.CASE_CHECK_ITEM] = RoleConfig(
        vendor="gateway", model="anthropic/claude-sonnet-5-5", max_tokens=10
    )
    roles[Role.AGENT_MAIN] = RoleConfig(vendor="gateway", model="google/gemini-3", max_tokens=10)
    assert model_problems(roles, {m["id"]: set(m["tags"]) for m in _listing()["data"]}) == [
        "case.check_item: anthropic/claude-sonnet-5-5 is not in the gateway model list",
        "document.transcribe: openai/gpt-oss-120b lacks vision",
        "agent.main: google/gemini-3 is neither anthropic/* nor openai/*",
    ]


async def test_validate_models_reads_the_live_listing_shape() -> None:
    roles = load_roles(Path(__file__).parents[2] / "config/roles.toml", {})
    seen: Seen = []
    await validate_models(roles, _http(lambda _: httpx2.Response(200, json=_listing()), seen))
    assert str(seen[0].url) == "https://ai-gateway.vercel.sh/v1/models"
    with pytest.raises(ConfigError, match="could not read the gateway model list"):
        await validate_models(roles, _http(lambda _: httpx2.Response(503), []))


def test_build_client_needs_the_key_of_every_used_vendor(tmp_path: Path) -> None:
    settings = make_settings(tmp_path / "h", tmp_path / "c")
    with pytest.raises(ConfigError, match="AI_GATEWAY_API_KEY is not set"):
        build_client(settings, env={})
    keyed = make_settings(tmp_path / "h", tmp_path / "c", AI_GATEWAY_API_KEY=KEY)
    assert set(build_client(keyed, env={}).vendors) == {"gateway"}
    direct = {
        "CAIRN_ROLE_AGENT_MAIN_VENDOR": "anthropic",
        "CAIRN_ROLE_AGENT_MAIN_MODEL": "claude-sonnet-5-5",
    }
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY is not set"):
        build_client(keyed, env=direct)
