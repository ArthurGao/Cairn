"""Anthropic Messages adapter: the direct API and the gateway's `anthropic/*` models (§10.1).

The only module that imports the Anthropic SDK. SDK retries are off: Temporal retries the
activity, and the error class below tells it whether to.
"""

import json
from typing import Any

import anthropic
import httpx2

from cairn.llm.roles import RoleConfig
from cairn.llm.schema import strict_schema
from cairn.llm.types import (
    ImagePart,
    LlmError,
    LlmRequest,
    LlmResult,
    StopReason,
    TextPart,
    ToolResultPart,
    ToolUsePart,
)

_STOP: dict[str, StopReason] = {
    "end_turn": "end",
    "stop_sequence": "end",
    "pause_turn": "end",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
    "refusal": "refusal",
}


def _block(part: Any) -> dict[str, Any]:
    if isinstance(part, TextPart):
        block: dict[str, Any] = {"type": "text", "text": part.text}
        if part.cache:
            block["cache_control"] = {"type": "ephemeral"}
        return block
    if isinstance(part, ImagePart):
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": part.media_type, "data": part.data_b64},
        }
    if isinstance(part, ToolUsePart):
        return {"type": "tool_use", "id": part.id, "name": part.name, "input": part.args}
    assert isinstance(part, ToolResultPart)
    return {"type": "tool_result", "tool_use_id": part.tool_use_id, "content": part.content}


def build_params(config: RoleConfig, request: LlmRequest, model: str) -> dict[str, Any]:
    params: dict[str, Any] = {
        "model": model,
        "max_tokens": config.max_tokens,
        "messages": [
            {"role": m.role, "content": [_block(p) for p in m.content]} for m in request.messages
        ],
    }
    if request.system:  # never sent empty
        params["system"] = (
            [{"type": "text", "text": request.system, "cache_control": {"type": "ephemeral"}}]
            if request.cache_system
            else request.system
        )
    output: dict[str, Any] = {}
    if config.effort:
        output["effort"] = config.effort
    if request.output_schema is not None:
        output["format"] = {"type": "json_schema", "schema": strict_schema(request.output_schema)}
    if output:
        params["output_config"] = output
    if request.tools:
        params["tools"] = [
            {"name": t.name, "description": t.description, "input_schema": t.parameters}
            for t in request.tools
        ]
    return params


def classify(exc: Exception) -> LlmError:
    """Design §10.3 error classes: only rate limits, 5xx and transport errors are retried."""
    if isinstance(exc, anthropic.APIConnectionError):  # includes timeouts
        return LlmError(f"anthropic: connection failed: {exc}", retryable=True, code="connection")
    if isinstance(exc, anthropic.RateLimitError):
        return LlmError(
            f"anthropic: rate limited: {exc.message}", retryable=True, code="rate_limited"
        )
    if isinstance(exc, anthropic.APIStatusError):
        status = exc.status_code
        if status >= 500:
            return LlmError(f"anthropic: {status}: {exc.message}", retryable=True, code="server")
        if status == 402:
            return LlmError(f"budget exhausted: {exc.message}", retryable=False, code="budget")
        if "credit balance is too low" in exc.message:
            return LlmError(f"anthropic: {exc.message}", retryable=False, code="no_credit")
        return LlmError(f"anthropic: {status}: {exc.message}", retryable=False, code="rejected")
    return LlmError(f"anthropic: {exc}", retryable=False, code="unexpected")


class AnthropicAdapter:
    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: str | None = None,
        http_client: httpx2.AsyncClient | None = None,
    ):
        self.name = name
        # SDK 2.x sends the key as a bearer token, which the gateway also accepts;
        # only the base URL differs between the direct API and the gateway.
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key, base_url=base_url, max_retries=0, http_client=http_client
        )

    async def complete(
        self, config: RoleConfig, request: LlmRequest, model: str | None = None
    ) -> LlmResult:
        try:
            response = await self.client.messages.create(
                **build_params(config, request, model or config.model)
            )
        except anthropic.AnthropicError as exc:
            raise classify(exc) from exc
        text = "".join(b.text for b in response.content if b.type == "text")
        tools = [
            ToolUsePart(id=b.id, name=b.name, args=dict(b.input))
            for b in response.content
            if b.type == "tool_use"
        ]
        stop = _STOP.get(str(response.stop_reason), "end")
        data: dict[str, Any] | None = None
        if request.output_schema is not None and stop not in ("max_tokens", "refusal") and text:
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise LlmError(
                    f"anthropic: reply is not JSON: {exc}", retryable=False, code="schema"
                ) from exc
        return LlmResult(
            role=request.role,
            vendor=self.name,
            model=model or config.model,
            text=text,
            data=data,
            tool_calls=tools,
            stop_reason=stop,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
        )
