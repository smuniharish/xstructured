"""Pydantic v2 schema target introspection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

from pydantic import BaseModel, TypeAdapter

from xstructured.core.errors import SchemaError

SchemaTarget: TypeAlias = type[BaseModel] | TypeAdapter[Any] | Any


@dataclass(frozen=True, slots=True)
class SchemaInfo:
    """The Pydantic adapter and JSON Schema for a target annotation."""

    target: SchemaTarget
    adapter: TypeAdapter[Any]
    json_schema: dict[str, Any]
    name: str

    def validate_python(self, value: Any) -> Any:
        """Validate a Python value against the target."""
        return self.adapter.validate_python(value)

    def validate_json(self, value: str | bytes | bytearray) -> Any:
        """Validate JSON text against the target."""
        return self.adapter.validate_json(value)


def inspect_schema(target: SchemaTarget) -> SchemaInfo:
    """Build a Pydantic v2 adapter and JSON Schema for *target*."""
    try:
        adapter = target if isinstance(target, TypeAdapter) else TypeAdapter(target)
        schema = adapter.json_schema(mode="validation")
    except (TypeError, ValueError, AttributeError) as exc:
        raise SchemaError(f"Cannot introspect schema target {target!r}") from exc

    if not isinstance(schema, dict):
        raise SchemaError("Pydantic returned a non-object JSON Schema")

    name = _schema_name(target, schema)
    return SchemaInfo(target=target, adapter=adapter, json_schema=schema, name=name)


def _schema_name(target: SchemaTarget, schema: dict[str, Any]) -> str:
    title = schema.get("title")
    if isinstance(title, str) and title:
        return title
    target_name = getattr(target, "__name__", None)
    if isinstance(target_name, str) and target_name:
        return target_name
    return "structured output"
