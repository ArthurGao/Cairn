"""Vercel AI Gateway: each model family over its native protocol, picked by prefix (D-12).

`anthropic/*` -> Anthropic Messages at https://ai-gateway.vercel.sh;
`openai/*` -> OpenAI Chat Completions at https://ai-gateway.vercel.sh/v1. One key for both.
"""

from typing import Any

import httpx2

from cairn.llm.roles import ConfigError, RoleConfig
from cairn.llm.types import LlmRequest, LlmResult
from cairn.llm.vendors.anthropic import AnthropicAdapter
from cairn.llm.vendors.openai import OpenAIAdapter

GATEWAY = "https://ai-gateway.vercel.sh"
MODELS_URL = f"{GATEWAY}/v1/models"
PREFIXES = ("anthropic/", "openai/")


class GatewayVendor:
    name = "gateway"

    def __init__(self, api_key: str, http_client: httpx2.AsyncClient | None = None):
        self.anthropic = AnthropicAdapter(self.name, api_key, GATEWAY, http_client)
        self.openai = OpenAIAdapter(self.name, api_key, f"{GATEWAY}/v1", http_client)

    async def complete(self, config: RoleConfig, request: LlmRequest) -> LlmResult:
        if config.model.startswith("anthropic/"):
            return await self.anthropic.complete(config, request)
        if config.model.startswith("openai/"):
            return await self.openai.complete(config, request)
        raise ConfigError(f"gateway model {config.model!r}: only anthropic/* and openai/* in v1")


def model_tags(listing: dict[str, Any]) -> dict[str, set[str]]:
    """`GET /v1/models` -> {model id: tags}."""
    return {str(m["id"]): set(m.get("tags") or []) for m in listing.get("data", [])}
