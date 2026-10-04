"""Resolution of schema arguments and JSON-Schema-aware annotation stripping."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeGuard

from .introspection import SchemaInfo, SchemaTarget, inspect_schema
from .named import NamedSchemas, NamedSchemaTargets, inspect_named_schemas

__all__ = ["is_named_targets", "resolve_schema", "strip_annotations"]

_JSON_VALUES = (Mapping, list, tuple, str, int, float, type(None))

# Keywords whose value maps names to subschemas.
_SCHEMA_MAPS = frozenset(
    {
        "$defs",
        "definitions",
        "dependentSchemas",
        "patternProperties",
        "properties",
    }
)
# Keywords whose value is a list of subschemas.
_SCHEMA_LISTS = frozenset({"allOf", "anyOf", "items", "oneOf", "prefixItems"})
# Keywords whose value is a single subschema.
_SCHEMA_VALUES = frozenset(
    {
        "additionalItems",
        "additionalProperties",
        "contains",
        "contentSchema",
        "else",
        "if",
        "items",
        "not",
        "propertyNames",
        "then",
        "unevaluatedItems",
        "unevaluatedProperties",
    }
)


def is_named_targets(value: object) -> TypeGuard[NamedSchemaTargets]:
    """Whether *value* is a non-empty mapping of names to schema targets.

    A JSON Schema document maps keywords to JSON values, while named targets map names
    to model classes, adapters, or annotations, which are never plain JSON values.
    """
    return (
        isinstance(value, Mapping)
        and bool(value)
        and all(not isinstance(item, _JSON_VALUES) for item in value.values())
    )


def resolve_schema(
    target: SchemaTarget
    | SchemaInfo
    | NamedSchemaTargets
    | NamedSchemas
    | Mapping[str, Any],
) -> SchemaInfo | NamedSchemas | dict[str, Any]:
    """Classify and resolve a schema argument.

    Returns a `SchemaInfo` for a single target, `NamedSchemas` for named targets, or a
    plain ``dict`` for a JSON Schema document.
    """
    if isinstance(target, (SchemaInfo, NamedSchemas)):
        return target
    if is_named_targets(target):
        return inspect_named_schemas(target)
    if isinstance(target, Mapping):
        return dict(target)
    return inspect_schema(target)


def strip_annotations(
    schema: Any, keywords: frozenset[str], *, sort_required: bool = False
) -> Any:
    """Return a copy of *schema* without the given keywords at schema positions.

    Only keywords of (sub)schemas are removed. Property names, ``$defs`` names, and data
    such as ``enum``, ``const`` or ``required`` values are kept, so a field named
    ``title`` is never mistaken for the ``title`` annotation. With *sort_required*, the
    ``required`` arrays, which JSON Schema treats as sets, are sorted.
    """
    if not isinstance(schema, Mapping):
        return schema
    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key in keywords:
            continue
        if key in _SCHEMA_MAPS and isinstance(value, Mapping):
            result[key] = {
                name: strip_annotations(
                    item, keywords, sort_required=sort_required
                )
                for name, item in value.items()
            }
        elif key in _SCHEMA_LISTS and isinstance(value, list):
            result[key] = [
                strip_annotations(item, keywords, sort_required=sort_required)
                for item in value
            ]
        elif key in _SCHEMA_VALUES:
            result[key] = strip_annotations(
                value, keywords, sort_required=sort_required
            )
        elif key == "required" and sort_required and isinstance(value, list):
            result[key] = sorted(value, key=str)
        else:
            result[key] = value
    return result
