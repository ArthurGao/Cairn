"""`call(request) -> LlmResult`: the one entry point to every model (design §10.3)."""

from collections.abc import Mapping
from typing import Protocol

import httpx2

from cairn.llm.roles import ConfigError, Role, RoleConfig, load_roles
from cairn.llm.types import LlmError, LlmRequest, LlmResult
from cairn.settings import Settings, role_env


class Vendor(Protocol):
    """A vendor maps its own SDK errors to `LlmError(retryable=...)` (design §10.3);
    the client does not classify vendor exceptions."""

    name: str

    async def complete(self, config: RoleConfig, request: LlmRequest) -> LlmResult: ...


class LlmClient:
    def __init__(self, roles: Mapping[Role, RoleConfig], vendors: Mapping[str, Vendor]):
        self.roles = dict(roles)
        self.vendors = dict(vendors)
        for role, config in self.roles.items():
            if config.vendor not in self.vendors:
                raise ConfigError(f"role {role.value}: vendor {config.vendor!r} is not available")

    async def call(self, request: LlmRequest) -> LlmResult:
        config = self.roles[request.role]
        result = await self.vendors[config.vendor].complete(config, request)
        if request.output_schema is not None:
            if result.stop_reason == "max_tokens":
                raise LlmError(
                    f"{request.role}: reply cut off at max_tokens ({config.max_tokens})",
                    retryable=False,
                    code="max_tokens",
                )
            if result.data is None:
                raise LlmError(
                    f"{request.role}: no structured output", retryable=False, code="schema"
                )
        return result


def build_client(
    settings: Settings,
    env: Mapping[str, str] | None = None,
    http_client: httpx2.AsyncClient | None = None,
) -> LlmClient:
    """Roles from config + env; a vendor is built only when some role uses it, and a
    configured vendor without its key stops startup (design §10.3)."""
    from cairn.llm.vendors.anthropic import AnthropicAdapter
    from cairn.llm.vendors.fake import FakeVendor
    from cairn.llm.vendors.gateway import GatewayVendor
    from cairn.llm.vendors.llmgw import LlmgwVendor

    roles = load_roles(
        settings.roles_file, env if env is not None else role_env(), settings.llm_vendor
    )
    used = {c.vendor for c in roles.values()}
    vendors: dict[str, Vendor] = {}
    if "fake" in used:
        if settings.fake_scenario is None:
            raise ConfigError(
                "the fake vendor needs CAIRN_FAKE_SCENARIO (scenario JSON files, colon-separated)"
            )
        vendors["fake"] = FakeVendor(*settings.fake_scenarios)
    if "gateway" in used:
        key = settings.ai_gateway_api_key.get_secret_value()
        if not key:
            raise ConfigError("roles use the gateway but AI_GATEWAY_API_KEY is not set")
        vendors["gateway"] = GatewayVendor(key, http_client)
    if "anthropic" in used:
        key = settings.anthropic_api_key.get_secret_value()
        if not key:
            raise ConfigError("roles use the anthropic vendor but ANTHROPIC_API_KEY is not set")
        vendors["anthropic"] = AnthropicAdapter("anthropic", key, None, http_client)
    if "llmgw" in used:
        if not settings.llmgw_base_url:
            raise ConfigError("roles use the llmgw vendor but CAIRN_LLMGW_BASE_URL is not set")
        vendors["llmgw"] = LlmgwVendor(
            settings.llmgw_base_url, http_client, settings.llmgw_token.get_secret_value()
        )
    return LlmClient(roles, vendors)
