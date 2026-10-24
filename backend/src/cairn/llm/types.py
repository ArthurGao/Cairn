"""Vendor-neutral request/result shapes (design §10.3). Call sites see only these."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from cairn.errors import CairnError
from cairn.llm.roles import Role


class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str
    # Cache everything up to and including this part (a large prefix reused across calls,
    # e.g. the case pages sent with every checklist batch). Vendors without explicit
    # caching ignore it.
    cache: bool = False


class ImagePart(BaseModel):
    type: Literal["image"] = "image"
    media_type: str = "image/png"
    data_b64: str


class ToolUsePart(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    args: dict[str, Any]


class ToolResultPart(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str


Part = Annotated[TextPart | ImagePart | ToolUsePart | ToolResultPart, Field(discriminator="type")]


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: list[Part]

    @classmethod
    def user(cls, *parts: Part | str) -> "Message":
        return cls(
            role="user", content=[TextPart(text=p) if isinstance(p, str) else p for p in parts]
        )

    def text(self) -> str:
        return "\n".join(p.text for p in self.content if isinstance(p, TextPart))


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class LlmRequest(BaseModel):
    role: Role
    system: str = ""
    messages: list[Message]
    tools: list[ToolSpec] = Field(default_factory=list[ToolSpec])
    output_schema: dict[str, Any] | None = None
    prompt_version: str = ""


StopReason = Literal["end", "tool_use", "max_tokens", "refusal"]


class LlmResult(BaseModel):
    role: str
    vendor: str
    model: str
    text: str = ""
    data: dict[str, Any] | None = None  # structured output, when output_schema was given
    tool_calls: list[ToolUsePart] = Field(default_factory=list[ToolUsePart])
    stop_reason: StopReason
    tokens_in: int = 0
    tokens_out: int = 0


class LlmError(CairnError):
    """`retryable` decides whether Temporal retries the activity (design §10.3 error classes)."""

    code = "llm_error"
    status = 502

    def __init__(self, message: str, *, retryable: bool, code: str | None = None):
        super().__init__(message, code=code)
        self.retryable = retryable
