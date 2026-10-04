"""Named schema targets.

Named schemas let one response choose which of several schemas applies. In array and
single-value modes the choice is carried inside the JSON payload as
``{"schema": "<name>", "payload": <value>}``; with named envelopes it is carried by the
envelope itself (``<xstructured name="<name>">``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from xstructured.core.errors import SchemaError
from xstructured.envelope.spec import NAME_PATTERN

from .introspection import SchemaInfo, SchemaTarget, inspect_schema

__all__ = [
    "NamedSchemaSpec",
    "NamedSchemaTargets",
    "NamedSchemas",
    "inspect_named_schemas",
]

type NamedSchemaTargets = Mapping[str, SchemaTarget]
"""A mapping of schema names to schema targets."""


@dataclass(frozen=True, slots=True)
class NamedSchemaSpec:
    """The JSON keys that carry the schema name and the payload.

    Attributes:
        schema_key: Key holding the schema name.
        payload_key: Key holding the value validated against that schema.

    Raises:
        SchemaError: If a key is empty or both keys are equal.
    """

    schema_key: str = "schema"
    payload_key: str = "payload"

    def __post_init__(self) -> None:
        if not self.schema_key or not self.payload_key:
            raise SchemaError("Named schema keys must be non-empty")
        if self.schema_key == self.payload_key:
            raise SchemaError("Named schema keys must differ")


@dataclass(frozen=True, slots=True, eq=False)
class NamedSchemas:
    """A resolved, immutable set of named schemas.

    Names must be 1-64 characters from ``A-Z``, ``a-z``, ``0-9``, ``_``, ``.`` and ``-``.

    Attributes:
        schemas: Read-only mapping of names to resolved schemas.
        spec: The keys used by the ``{"schema": ..., "payload": ...}`` form.

    Raises:
        SchemaError: If no schema is given or a name is invalid.
    """

    schemas: Mapping[str, SchemaInfo]
    spec: NamedSchemaSpec = field(default_factory=NamedSchemaSpec)

    def __post_init__(self) -> None:
        if not self.schemas:
            raise SchemaError("At least one named schema is required")
        for name in self.schemas:
            if (
                not isinstance(name, str)
                or NAME_PATTERN.fullmatch(name) is None
            ):
                raise SchemaError(
                    f"Invalid schema name {name!r}: use 1-64 letters, digits, '_', '.' or '-'"
                )
        object.__setattr__(
            self, "schemas", MappingProxyType(dict(self.schemas))
        )

    @property
    def names(self) -> tuple[str, ...]:
        """The configured names, sorted."""
        return tuple(sorted(self.schemas))

    def resolve(self, name: str) -> SchemaInfo:
        """Return the schema registered under *name*.

        Raises:
            SchemaError: If *name* is not configured.
        """
        try:
            return self.schemas[name]
        except KeyError:
            raise SchemaError(
                f"{name!r} is not one of the configured schema names {list(self.names)}"
            ) from None


def inspect_named_schemas(
    targets: NamedSchemaTargets | NamedSchemas,
    *,
    spec: NamedSchemaSpec | None = None,
) -> NamedSchemas:
    """Resolve every named schema target.

    Args:
        targets: Mapping of names to schema targets, or an existing `NamedSchemas`.
        spec: Keys for the ``{"schema": ..., "payload": ...}`` form. Defaults to the
            existing spec, or to `NamedSchemaSpec()`.

    Raises:
        SchemaError: If *targets* is empty, a name is invalid, or a target cannot be
            introspected.
    """
    if isinstance(targets, NamedSchemas):
        return targets if spec is None else NamedSchemas(targets.schemas, spec)
    return NamedSchemas(
        {name: inspect_schema(target) for name, target in targets.items()},
        spec or NamedSchemaSpec(),
    )
