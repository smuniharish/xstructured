"""Pydantic v2 schema target introspection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, PydanticUserError, TypeAdapter

from xstructured.core.errors import SchemaError

__all__ = ["SchemaInfo", "SchemaTarget", "inspect_schema"]

type SchemaTarget = type[BaseModel] | TypeAdapter[Any] | Any
"""Anything Pydantic v2 can validate: a model class, a `TypeAdapter`, or a type annotation."""

_FALLBACK_NAME = "structured output"


@dataclass(frozen=True, slots=True, eq=False)
class SchemaInfo:
    """A schema target resolved to a Pydantic adapter and its JSON Schema.

    Attributes:
        target: The original schema target.
        adapter: The `TypeAdapter` used for validation.
        json_schema: The target's JSON Schema in validation mode. Treat it as read-only.
        name: Display name: the schema title, the target's ``__name__``, or
            ``"structured output"``.
    """

    target: SchemaTarget
    adapter: TypeAdapter[Any]
    json_schema: dict[str, Any]
    name: str

    def validate_json(self, text: str) -> Any:
        """Validate JSON *text* against the target using Pydantic's JSON mode.

        Raises:
            pydantic.ValidationError: If the value does not match the schema.
        """
        return self.adapter.validate_json(text)


def inspect_schema(target: SchemaTarget | SchemaInfo) -> SchemaInfo:
    """Resolve *target* to a `SchemaInfo`. A `SchemaInfo` is returned unchanged.

    Raises:
        SchemaError: If Pydantic cannot build a validator or JSON Schema for *target*.
    """
    if isinstance(target, SchemaInfo):
        return target
    try:
        adapter = (
            target if isinstance(target, TypeAdapter) else TypeAdapter(target)
        )
        schema = adapter.json_schema(mode="validation")
    except (
        AttributeError,
        NameError,
        PydanticUserError,
        SyntaxError,
        TypeError,
        ValueError,
    ) as exc:
        raise SchemaError(
            f"Cannot introspect schema target {target!r}: {exc}"
        ) from exc
    name = _name(target, schema)
    return SchemaInfo(
        target=target, adapter=adapter, json_schema=schema, name=name
    )


def _name(target: object, schema: dict[str, Any]) -> str:
    title = schema.get("title")
    if isinstance(title, str) and title:
        return title
    name = getattr(target, "__name__", None)
    return name if isinstance(name, str) and name else _FALLBACK_NAME
