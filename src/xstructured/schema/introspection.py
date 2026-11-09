"""Pydantic v2 schema target introspection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, PydanticUserError, TypeAdapter

from xstructured.core.errors import SchemaError

from .options import SchemaOptions

__all__ = ["UNSET", "SchemaInfo", "SchemaTarget", "inspect_schema"]

type SchemaTarget = type[BaseModel] | TypeAdapter[Any] | Any
"""Anything Pydantic v2 can validate: a model class, a `TypeAdapter`, or a type annotation."""

UNSET: Any = object()
"""Sentinel for an omitted per-call validation context."""

_FALLBACK_NAME = "structured output"


@dataclass(frozen=True, slots=True, eq=False)
class SchemaInfo:
    """A schema target resolved to a Pydantic adapter and its JSON Schema.

    Attributes:
        target: The original schema target.
        adapter: The `TypeAdapter` used for validation.
        json_schema: The target's JSON Schema. Treat it as read-only.
        name: Display name: the schema title, the target's ``__name__``, or
            ``"structured output"``.
        options: The Pydantic options used to build and validate the schema.
    """

    target: SchemaTarget
    adapter: TypeAdapter[Any]
    json_schema: dict[str, Any]
    name: str
    options: SchemaOptions = field(default_factory=SchemaOptions)

    def validate_json(self, text: str, *, context: Any = UNSET) -> Any:
        """Validate JSON *text* against the target using Pydantic's JSON mode.

        Args:
            text: Standard JSON text.
            context: Validation context for this call. Defaults to
                `SchemaOptions.context`.

        Raises:
            pydantic.ValidationError: If the value does not match the schema.
        """
        options = self.options
        return self.adapter.validate_json(
            text,
            strict=options.strict,
            extra=options.extra,
            context=options.context if context is UNSET else context,
            by_alias=options.by_alias,
            by_name=options.by_name,
        )


def inspect_schema(
    target: SchemaTarget | SchemaInfo, *, options: SchemaOptions | None = None
) -> SchemaInfo:
    """Resolve *target* to a `SchemaInfo`.

    A `SchemaInfo` is returned unchanged when *options* is omitted, and rebuilt
    from its target otherwise.

    Args:
        target: A model class, `TypeAdapter`, annotation, or `SchemaInfo`.
        options: Pydantic options for the adapter, validation, and JSON Schema.

    Raises:
        SchemaError: If Pydantic cannot build a validator or JSON Schema for *target*.
    """
    if isinstance(target, SchemaInfo):
        if options is None:
            return target
        target = target.target
    options = options or SchemaOptions()
    if isinstance(target, TypeAdapter) and options.config is not None:
        raise SchemaError(
            "SchemaOptions.config cannot be applied to an existing TypeAdapter; "
            "pass the annotation instead"
        )
    try:
        adapter = (
            target
            if isinstance(target, TypeAdapter)
            else TypeAdapter(target, config=options.config)
        )
        schema = adapter.json_schema(
            by_alias=options.json_schema_by_alias,
            ref_template=options.ref_template,
            union_format=options.union_format,
            schema_generator=options.schema_generator,
            mode=options.json_schema_mode,
        )
    except (
        AttributeError,
        KeyError,
        NameError,
        PydanticUserError,
        SyntaxError,
        TypeError,
        ValueError,
    ) as exc:
        raise SchemaError(
            f"Cannot introspect schema target {target!r}: {exc}"
        ) from exc
    return SchemaInfo(
        target=target,
        adapter=adapter,
        json_schema=schema,
        name=_name(target, schema),
        options=options,
    )


def _name(target: object, schema: dict[str, Any]) -> str:
    title = schema.get("title")
    if isinstance(title, str) and title:
        return title
    name = getattr(target, "__name__", None)
    return name if isinstance(name, str) and name else _FALLBACK_NAME
