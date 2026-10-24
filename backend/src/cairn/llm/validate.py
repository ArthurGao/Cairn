"""Startup validation of model ids and capabilities (design §10.3): fail before the first call.

The gateway's public model list (no key needed) gives each id's tags; a role whose model is
missing, has the wrong prefix, or lacks a tag the role needs stops the worker.
"""

from collections.abc import Mapping

import httpx2

from cairn.llm.roles import NEEDS, ConfigError, Role, RoleConfig
from cairn.llm.vendors.gateway import MODELS_URL, PREFIXES, model_tags


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


async def validate_models(
    roles: Mapping[Role, RoleConfig], http: httpx2.AsyncClient | None = None
) -> None:
    """Raise ConfigError listing every problem; a no-op when no role uses the gateway."""
    if not any(c.vendor == "gateway" for c in roles.values()):
        return
    client = http or httpx2.AsyncClient(timeout=20)
    try:
        response = await client.get(MODELS_URL)
        response.raise_for_status()
        tags = model_tags(response.json())
    except httpx2.HTTPError as exc:
        raise ConfigError(f"could not read the gateway model list ({MODELS_URL}): {exc}") from exc
    finally:
        if http is None:
            await client.aclose()
    if problems := model_problems(roles, tags):
        raise ConfigError("refusing to start: " + "; ".join(problems))
