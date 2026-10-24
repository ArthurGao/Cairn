"""OpenAI Chat Completions adapter: the gateway's `openai/*` models (design §10.1).

The only module that imports the OpenAI SDK. SDK retries are off; Temporal retries.
"""

import json
from typing import Any

import httpx2
import openai

from cairn.llm.roles import RoleConfig
from cairn.llm.schema import strict_schema
from cairn.llm.types import (
    ImagePart,
    LlmError,
    LlmRequest,
    LlmResult,
    Message,
    StopReason,
    TextPart,
    ToolResultPart,
    ToolUsePart,
)

_STOP: dict[str, StopReason] = {
    "stop": "end",
    "tool_calls": "tool_use",
    "function_call": "tool_use",
    "length": "max_tokens",
    "content_filter": "refusal",
}


def _messages(request: LlmRequest) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if request.system:  # the gateway refuses an empty system message
        out.append({"role": "system", "content": request.system})
    for message in request.messages:
        out.extend(_convert(message))
    return out


def _convert(message: Message) -> list[dict[str, Any]]:
    if message.role == "assistant":
        text = "".join(p.text for p in message.content if isinstance(p, TextPart))
        calls = [
            {
                "id": p.id,
                "type": "function",
                "function": {"name": p.name, "arguments": json.dumps(p.args)},
            }
            for p in message.content
            if isinstance(p, ToolUsePart)
        ]
        entry: dict[str, Any] = {"role": "assistant", "content": text or None}
        if calls:
            entry["tool_calls"] = calls
        return [entry]
    results = [
        {"role": "tool", "tool_call_id": p.tool_use_id, "content": p.content}
        for p in message.content
        if isinstance(p, ToolResultPart)
    ]
    parts: list[dict[str, Any]] = []
    for p in message.content:
        if isinstance(p, TextPart):
            parts.append({"type": "text", "text": p.text})
        elif isinstance(p, ImagePart):
            url = f"data:{p.media_type};base64,{p.data_b64}"
            parts.append({"type": "image_url", "image_url": {"url": url}})
    return results + ([{"role": "user", "content": parts}] if parts else [])


def build_params(config: RoleConfig, request: LlmRequest, model: str) -> dict[str, Any]:
    params: dict[str, Any] = {
        "model": model,
        "messages": _messages(request),
        "max_completion_tokens": config.max_tokens,  # newer models reject max_tokens
    }
    if config.effort:
        params["reasoning_effort"] = config.effort
    if request.output_schema is not None:
        params["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "output",
                "schema": strict_schema(request.output_schema),
                "strict": True,
            },
        }
    if request.tools:
        params["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in request.tools
        ]
    return params


def classify(exc: Exception) -> LlmError:
    if isinstance(exc, openai.APIConnectionError):  # includes timeouts
        return LlmError(f"openai: connection failed: {exc}", retryable=True, code="connection")
    if isinstance(exc, openai.RateLimitError):
        if getattr(exc, "code", None) == "insufficient_quota":  # an empty balance, not a rate
            return LlmError(f"openai: {exc.message}", retryable=False, code="no_credit")
        return LlmError(f"openai: rate limited: {exc.message}", retryable=True, code="rate_limited")
    if isinstance(exc, openai.APIStatusError):
        status = exc.status_code
        if status >= 500:
            return LlmError(f"openai: {status}: {exc.message}", retryable=True, code="server")
        if status == 402:
            return LlmError(f"budget exhausted: {exc.message}", retryable=False, code="budget")
        return LlmError(f"openai: {status}: {exc.message}", retryable=False, code="rejected")
    return LlmError(f"openai: {exc}", retryable=False, code="unexpected")


class OpenAIAdapter:
    def __init__(
        self, name: str, api_key: str, base_url: str, http_client: httpx2.AsyncClient | None = None
    ):
        self.name = name
        self.client = openai.AsyncOpenAI(
            api_key=api_key, base_url=base_url, max_retries=0, http_client=http_client
        )

    async def complete(
        self, config: RoleConfig, request: LlmRequest, model: str | None = None
    ) -> LlmResult:
        try:
            response = await self.client.chat.completions.create(
                **build_params(config, request, model or config.model)
            )
        except openai.OpenAIError as exc:
            raise classify(exc) from exc
        choice = response.choices[0]
        message = choice.message
        stop = "refusal" if message.refusal else _STOP.get(str(choice.finish_reason), "end")
        text = message.content or ""
        tools = [
            ToolUsePart(
                id=c.id, name=c.function.name, args=json.loads(c.function.arguments or "{}")
            )
            for c in message.tool_calls or []
            if c.type == "function"
        ]
        data: dict[str, Any] | None = None
        if request.output_schema is not None and stop not in ("max_tokens", "refusal") and text:
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise LlmError(
                    f"openai: reply is not JSON: {exc}", retryable=False, code="schema"
                ) from exc
        usage = response.usage
        return LlmResult(
            role=request.role,
            vendor=self.name,
            model=model or config.model,
            text=text,
            data=data,
            tool_calls=tools,
            stop_reason=stop,
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
        )
