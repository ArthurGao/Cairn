"""Base model for everything that crosses the API: a field with a default is still always
present in responses, so the generated client types say so (no needless optionals)."""

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
