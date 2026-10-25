"""Roles and their configuration (design §10.2). Call sites name a role, never a model."""

import tomllib
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from cairn.errors import CairnError


class Role(StrEnum):
    CASE_EXTRACT_FACTS = "case.extract_facts"
    CASE_COMPARE_FACTS = "case.compare_facts"
    CASE_CHECK_ITEM = "case.check_item"
    CASE_READ_LETTER = "case.read_letter"
    CASE_MATCH_EVIDENCE = "case.match_evidence"
    DOCUMENT_TRANSCRIBE = "document.transcribe"
    AGENT_MAIN = "agent.main"
    MEMORY_EXTRACT = "memory.extract"
    MEMORY_CONSOLIDATE = "memory.consolidate"


Capability = Literal["tool-use", "structured-output", "vision"]

NEEDS: dict[Role, frozenset[Capability]] = {
    Role.CASE_EXTRACT_FACTS: frozenset({"structured-output"}),
    Role.CASE_COMPARE_FACTS: frozenset({"structured-output"}),
    Role.CASE_CHECK_ITEM: frozenset({"structured-output"}),
    Role.CASE_READ_LETTER: frozenset({"structured-output"}),
    Role.CASE_MATCH_EVIDENCE: frozenset({"structured-output"}),
    Role.DOCUMENT_TRANSCRIBE: frozenset({"structured-output", "vision"}),
    Role.AGENT_MAIN: frozenset({"tool-use"}),
    Role.MEMORY_EXTRACT: frozenset({"structured-output"}),
    Role.MEMORY_CONSOLIDATE: frozenset({"structured-output"}),
}

# Roles each case check calls; the data-class gate checks exactly these (§10.4).
CHECK_ROLES: dict[str, tuple[Role, ...]] = {
    "consistency": (Role.DOCUMENT_TRANSCRIBE, Role.CASE_EXTRACT_FACTS, Role.CASE_COMPARE_FACTS),
    "presubmission": (Role.DOCUMENT_TRANSCRIBE, Role.CASE_CHECK_ITEM),
    "letter": (Role.DOCUMENT_TRANSCRIBE, Role.CASE_READ_LETTER, Role.CASE_MATCH_EVIDENCE),
}

# Vendors that may never receive client data in v1, whatever the allow-list says (D-15);
# `llmgw` never may: it answers on a personal subscription (D-19).
NEVER_CLIENT_DATA = frozenset({"gateway", "anthropic", "llmgw"})


class ConfigError(CairnError):
    code = "config_invalid"
    status = 500


class RoleConfig(BaseModel):
    vendor: str
    model: str
    effort: Literal["low", "medium", "high"] | None = None
    max_tokens: int


_FIELDS = ("vendor", "model", "effort", "max_tokens")


def load_roles(
    path: Path, env: Mapping[str, str], vendor_override: str = ""
) -> dict[Role, RoleConfig]:
    """roles.toml, then CAIRN_ROLE_<ROLE>_<FIELD> env overrides, then CAIRN_LLM_VENDOR."""
    raw = tomllib.loads(path.read_text(encoding="utf-8")).get("roles", {})
    roles: dict[Role, RoleConfig] = {}
    for role in Role:
        values = dict(raw.get(role.value, {}))
        prefix = "CAIRN_ROLE_" + role.value.upper().replace(".", "_") + "_"
        for field in _FIELDS:
            if (value := env.get(prefix + field.upper())) is not None:
                values[field] = value
        if vendor_override:
            values["vendor"] = vendor_override
        try:
            roles[role] = RoleConfig.model_validate(values)
        except ValidationError as exc:
            raise ConfigError(f"role {role.value}: {exc.errors()[0]['msg']}") from exc
    return roles


def data_class_problem(
    roles: Mapping[Role, RoleConfig],
    data_class: str,
    allowed_vendors: str,
    check_roles: tuple[Role, ...] = tuple(Role),
) -> str | None:
    """Why client data may not go to these roles' vendors, or None (design §10.4)."""
    if data_class != "client":
        return None
    allowed = {v.strip() for v in allowed_vendors.split(",") if v.strip()} - NEVER_CLIENT_DATA
    blocked = sorted(
        f"{role.value} -> {roles[role].vendor}"
        for role in check_roles
        if roles[role].vendor not in allowed and roles[role].vendor != "fake"
    )
    if blocked:
        return (
            "client data may only go to allow-listed vendors (CAIRN_CLIENT_DATA_VENDORS); "
            f"not allowed: {', '.join(blocked)}"
        )
    return None
