"""`call(request) -> LlmResult`: the one entry point to every model (design §10.3)."""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from cairn.llm.roles import ConfigError, Role, RoleConfig, load_roles
from cairn.llm.types import LlmError, LlmRequest, LlmResult
from cairn.settings import Settings


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


def build_client(settings: Settings, env: Mapping[str, str] | None = None) -> LlmClient:
    """Roles from config + env; vendors constructed for the roles that use them."""
    from cairn.llm.vendors.fake import FakeVendor

    roles = load_roles(
        settings.roles_file, env if env is not None else os.environ, settings.llm_vendor
    )
    vendors: dict[str, Vendor] = {}
    if any(c.vendor == "fake" for c in roles.values()):
        if settings.fake_scenario is None:
            raise ConfigError("the fake vendor needs CAIRN_FAKE_SCENARIO (a scenario JSON file)")
        vendors["fake"] = FakeVendor(Path(settings.fake_scenario))
    return LlmClient(roles, vendors)
