"""The local LLM gateway (`~/Code/AI/llm-gateway`): local dev and demos only, never prod (D-19).

It serves OpenAI Chat Completions on a loopback address and answers on the user's own ChatGPT or
Claude subscription; the role's `model` is one of its profile names. Code, not config, keeps it
on loopback and away from client data (`roles.NEVER_CLIENT_DATA`).
"""

from urllib.parse import urlsplit

import httpx2

from cairn.llm.roles import Capability, ConfigError, RoleConfig
from cairn.llm.types import LlmRequest, LlmResult
from cairn.llm.vendors.openai import OpenAIAdapter

LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
# What the gateway's v1 serves; tools and images are refused with 400 `unsupported_feature`.
CAPABILITIES: frozenset[Capability] = frozenset({"structured-output"})
# Without a token the gateway ignores the key; the SDK only needs a non-empty one.
PLACEHOLDER_KEY = "llmgw-local"


def loopback_url(base_url: str) -> str:
    parts = urlsplit(base_url)
    if parts.scheme not in ("http", "https") or parts.hostname not in LOOPBACK:
        raise ConfigError(
            f"CAIRN_LLMGW_BASE_URL must be a loopback http(s) URL, got {base_url!r}; "
            "the local gateway is for local dev and demos only"
        )
    return base_url.rstrip("/")


class LlmgwVendor:
    name = "llmgw"

    def __init__(
        self, base_url: str, http_client: httpx2.AsyncClient | None = None, token: str = ""
    ):
        self.base_url = loopback_url(base_url)
        # A gateway with `local_token_env` set requires this bearer on every /v1 route.
        self.token = token or PLACEHOLDER_KEY
        self.openai = OpenAIAdapter(self.name, self.token, self.base_url, http_client)

    async def complete(self, config: RoleConfig, request: LlmRequest) -> LlmResult:
        return await self.openai.complete(config, request)
