"""What route handlers share: settings and the Temporal client holder."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Request

from cairn.settings import Settings

if TYPE_CHECKING:
    from cairn.api.app import TemporalState


@dataclass(frozen=True)
class Services:
    settings: Settings
    temporal: "TemporalState"


def services(request: Request) -> Services:
    return request.app.state.services
