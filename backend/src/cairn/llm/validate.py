"""Startup validation of model ids and capabilities (design §10.3): fail before the first call.

The gateway's public model list (no key needed) gives each id's tags; a role whose model is
missing, has the wrong prefix, or lacks a tag the role needs stops the worker. A role on the
local `llmgw` must name one of its profiles and need nothing beyond what its v1 serves.
"""

import asyncio
from collections.abc import Mapping

import httpx2

from cairn.llm.client import LlmClient
from cairn.llm.roles import NEEDS, ConfigError, Role, RoleConfig
from cairn.llm.vendors.gateway import MODELS_URL, PREFIXES, model_tags
from cairn.llm.vendors.llmgw import CAPABILITIES, LlmgwVendor


def model_problems(
    roles: Mapping[Role, RoleConfig], gateway_tags: Mapping[str, set[str]]
) -> list[str]:
    problems: list[str] = []
    for role, config in roles.items():
        if config.vendor != "gateway":
            continue
        if not config.model.startswith(PREFIXES):
            problems.append(f"{role.value}: {config.model} is neither anthropic/* nor openai/*")
            continue
        tags = gateway_tags.get(config.model)
        if tags is None:
            problems.append(f"{role.value}: {config.model} is not in the gateway model list")
            continue
        if missing := sorted(NEEDS[role] - tags):
            problems.append(f"{role.value}: {config.model} lacks {', '.join(missing)}")
    return problems


def llmgw_problems(roles: Mapping[Role, RoleConfig], profiles: set[str]) -> list[str]:
    problems: list[str] = []
    for role, config in roles.items():
        if config.vendor != "llmgw":
            continue
        if missing := sorted(NEEDS[role] - CAPABILITIES):
            problems.append(f"{role.value}: llmgw lacks {', '.join(missing)}")
        elif config.model not in profiles:
            problems.append(f"{role.value}: {config.model} is not an llmgw profile")
    return problems


async def _listing(
    client: httpx2.AsyncClient, url: str, name: str, headers: dict[str, str]
) -> dict[str, set[str]]:
    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return model_tags(response.json())
    except httpx2.HTTPError as exc:
        raise ConfigError(f"could not read the {name} model list ({url}): {exc}") from exc


async def validate_models(llm: LlmClient, http: httpx2.AsyncClient | None = None) -> None:
    """Raise ConfigError listing every problem; a no-op when no role uses a listed vendor."""
    listings: dict[str, tuple[str, dict[str, str]]] = {}
    if "gateway" in llm.vendors:
        listings["gateway"] = (MODELS_URL, {})
    if isinstance(local := llm.vendors.get("llmgw"), LlmgwVendor):
        listings["llmgw"] = (
            f"{local.base_url}/models",
            {"Authorization": f"Bearer {local.token}"},
        )
    if not listings:
        return
    client = http or httpx2.AsyncClient(timeout=20)
    try:
        fetched = await asyncio.gather(
            *(_listing(client, url, name, headers) for name, (url, headers) in listings.items())
        )
    finally:
        if http is None:
            await client.aclose()
    tags = dict(zip(listings, fetched, strict=True))
    problems: list[str] = []
    if "gateway" in tags:
        problems += model_problems(llm.roles, tags["gateway"])
    if "llmgw" in tags:
        problems += llmgw_problems(llm.roles, set(tags["llmgw"]))
    if problems:
        raise ConfigError("refusing to start: " + "; ".join(problems))
