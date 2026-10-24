"""Live calls to real vendors (design §14). Run with `uv run pytest -m live`.

Each path skips with a printed reason when its key is missing; nothing passes silently.
Keys are read here at import time, before the autouse fixture clears the environment.
"""

import base64
import os
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from pydantic import BaseModel

from cairn.llm.roles import Role, RoleConfig
from cairn.llm.types import ImagePart, LlmRequest, Message, ToolSpec
from cairn.llm.vendors.anthropic import AnthropicAdapter
from cairn.llm.vendors.gateway import GatewayVendor
from cairn.settings import Settings

pytestmark = pytest.mark.live

_settings = Settings(_env_file=Path(__file__).parents[2] / ".env")  # pyright: ignore[reportCallIssue]
GATEWAY_KEY = (
    os.environ.get("AI_GATEWAY_API_KEY") or _settings.ai_gateway_api_key.get_secret_value()
)
ANTHROPIC_KEY = (
    os.environ.get("ANTHROPIC_API_KEY") or _settings.anthropic_api_key.get_secret_value()
)

PATHS = [
    pytest.param("gateway", "anthropic/claude-sonnet-5.5", id="gateway-claude"),
    pytest.param("gateway", "openai/gpt-5.4-mini", id="gateway-gpt"),
    pytest.param("anthropic", "claude-sonnet-5-5", id="direct-anthropic"),
]


class Verdict(BaseModel):
    answer: str
    confident: bool


def _vendor(vendor: str) -> GatewayVendor | AnthropicAdapter:
    if vendor == "gateway":
        if not GATEWAY_KEY:
            pytest.skip("AI_GATEWAY_API_KEY is not set: live gateway test skipped")
        return GatewayVendor(GATEWAY_KEY)
    if not ANTHROPIC_KEY:
        pytest.skip("ANTHROPIC_API_KEY is not set: live direct-Anthropic test skipped")
    return AnthropicAdapter("anthropic", ANTHROPIC_KEY)


def _config(vendor: str, model: str) -> RoleConfig:
    return RoleConfig(vendor=vendor, model=model, effort="low", max_tokens=4000)


@pytest.mark.parametrize(("vendor", "model"), PATHS)
async def test_structured_output(vendor: str, model: str) -> None:
    request = LlmRequest(
        role=Role.CASE_CHECK_ITEM,
        system="Answer with the JSON the schema asks for.",
        messages=[Message.user("What is 2 + 3? Put the number in answer.")],
        output_schema=Verdict.model_json_schema(),
    )
    result = await _vendor(vendor).complete(_config(vendor, model), request)
    verdict = Verdict.model_validate(result.data)
    assert "5" in verdict.answer
    assert result.tokens_in > 0
    assert result.tokens_out > 0


@pytest.mark.parametrize(("vendor", "model"), PATHS)
async def test_tool_use(vendor: str, model: str) -> None:
    tool = ToolSpec(
        name="read_memory",
        description="Read one memory file by slug.",
        parameters={
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
            "additionalProperties": False,
        },
    )
    request = LlmRequest(
        role=Role.AGENT_MAIN,
        system="Use the read_memory tool to read the memory called pilot-scope before answering.",
        messages=[Message.user("What is the pilot scope?")],
        tools=[tool],
    )
    result = await _vendor(vendor).complete(_config(vendor, model), request)
    assert result.stop_reason == "tool_use"
    assert [(c.name, c.args) for c in result.tool_calls] == [
        ("read_memory", {"slug": "pilot-scope"})
    ]


@pytest.mark.parametrize(("vendor", "model"), PATHS)
async def test_image_input(vendor: str, model: str) -> None:
    image = Image.new("RGB", (480, 120), "white")
    ImageDraw.Draw(image).text((20, 40), "INVOICE 4471", fill="black", font_size=36)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    request = LlmRequest(
        role=Role.DOCUMENT_TRANSCRIBE,
        system="Transcribe the text in the image exactly. Return it in answer.",
        messages=[Message.user(ImagePart(data_b64=base64.b64encode(buffer.getvalue()).decode()))],
        output_schema=Verdict.model_json_schema(),
    )
    result = await _vendor(vendor).complete(_config(vendor, model), request)
    assert "4471" in Verdict.model_validate(result.data).answer
