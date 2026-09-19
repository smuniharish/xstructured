"""Named multiple schema targets for a single, discriminated result.

`StructuredParser` and `XStructuredRunnable` still produce exactly one
envelope and one JSON result per response (see ADR 0004). Named schemas let
that single result be validated against one of several allowed shapes,
selected by an explicit ``"schema"`` name carried inside the payload itself,
instead of requiring every alternative to be folded by hand into one
Pydantic discriminated union.

A response using named schemas is one JSON object:

    {"schema": "<name>", "payload": <value valid against schemas["<name>"]>}

``<name>`` must be one of the configured names and ``<value>`` is validated
against that name's schema target -- nothing else changes: recovery,
envelope handling, and repair all continue to apply to the object as a
whole.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TypeAlias

from xstructured.core.errors import SchemaError

from .introspection import SchemaInfo, SchemaTarget, inspect_schema

NamedSchemaTargets: TypeAlias = Mapping[str, SchemaTarget]


@dataclass(frozen=True, slots=True)
class NamedSchemaSpec:
    """The discriminator and payload keys used to select among named schemas."""

    schema_key: str = "schema"
    payload_key: str = "payload"

    def __post_init__(self) -> None:
        if not self.schema_key or not self.payload_key:
            raise SchemaError("Named schema keys must be non-empty")
        if self.schema_key == self.payload_key:
            raise SchemaError("Named schema keys must differ")


@dataclass(frozen=True, slots=True)
class NamedSchemas:
    """A resolved, named set of possible schema targets for one response."""

    schemas: Mapping[str, SchemaInfo]
    spec: NamedSchemaSpec = field(default_factory=NamedSchemaSpec)

    def resolve(self, name: str) -> SchemaInfo:
        """Return the `SchemaInfo` registered under *name*.

        Raises:
            SchemaError: if *name* is not one of the configured schema names.
        """
        try:
            return self.schemas[name]
        except KeyError:
            raise SchemaError(
                f"{name!r} is not one of the configured schema names: {sorted(self.schemas)}"
            ) from None


def inspect_named_schemas(
    targets: NamedSchemaTargets, *, spec: NamedSchemaSpec | None = None
) -> NamedSchemas:
    """Introspect every named schema target, failing fast on empty input."""
    if not targets:
        raise SchemaError("At least one named schema target is required")
    return NamedSchemas(
        schemas={name: inspect_schema(target) for name, target in targets.items()},
        spec=spec or NamedSchemaSpec(),
    )
