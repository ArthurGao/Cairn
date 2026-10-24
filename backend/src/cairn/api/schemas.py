"""API models; the OpenAPI source for the frontend's generated client."""

from typing import Literal

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthOk(BaseModel):
    status: Literal["ok"]
    data_class: Literal["synthetic", "client"]
    temporal: Literal["ok"]
    home: str
    cases: str
