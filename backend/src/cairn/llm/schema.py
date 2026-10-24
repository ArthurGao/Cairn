"""Turn a Pydantic JSON schema into one both vendors' strict structured output accept.

Rules from design §10.3 and the KB provider notes: refs inlined, every object closed
(`additionalProperties: false`) with every property required (optional fields stay nullable),
no numeric bounds (sent bounds are rejected; the reply is validated locally anyway), and no
`default`/`title` noise.
"""

from typing import Any, cast

_DROP = {
    "default",
    "title",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
}


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    defs = cast(dict[str, Any], schema.get("$defs", {}))

    def walk(node: Any) -> Any:
        if isinstance(node, list):
            return [walk(item) for item in cast(list[Any], node)]
        if not isinstance(node, dict):
            return node
        obj = cast(dict[str, Any], node)
        if "$ref" in obj:
            return walk(defs[str(obj["$ref"]).rsplit("/", 1)[-1]])
        out = {k: walk(v) for k, v in obj.items() if k not in _DROP and k != "$defs"}
        if out.get("type") == "object" and "properties" in out:
            out["required"] = list(cast(dict[str, Any], out["properties"]))
            out["additionalProperties"] = False
        return out

    return cast(dict[str, Any], walk(schema))
