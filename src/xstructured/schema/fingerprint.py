"""Deterministic JSON Schema canonicalization and fingerprints."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from ._resolve import resolve_schema, strip_annotations
from .introspection import SchemaInfo, SchemaTarget
from .named import NamedSchemas, NamedSchemaTargets

__all__ = ["canonical_schema_json", "fingerprint_schema"]

# JSON Schema annotation keywords: they document a schema without changing which
# instances are valid.
_ANNOTATIONS = frozenset(
    {
        "$comment",
        "default",
        "deprecated",
        "description",
        "examples",
        "readOnly",
        "title",
        "writeOnly",
    }
)


def canonical_schema_json(
    target: SchemaTarget
    | SchemaInfo
    | NamedSchemaTargets
    | NamedSchemas
    | Mapping[str, Any],
    *,
    include_metadata: bool = False,
) -> str:
    """Return a stable, compact JSON serialization of a schema.

    Args:
        target: A schema target, a `SchemaInfo`, named schema targets, `NamedSchemas`,
            or a JSON Schema document.
        include_metadata: Keep annotation keywords such as ``title``, ``description``,
            ``default`` and ``examples``. By default they are removed, so documentation
            changes do not change the result.

    Raises:
        SchemaError: If *target* cannot be introspected.
    """
    keywords = frozenset() if include_metadata else _ANNOTATIONS
    resolved = resolve_schema(target)
    document: Any
    if isinstance(resolved, NamedSchemas):
        document = {
            "payload_key": resolved.spec.payload_key,
            "schema_key": resolved.spec.schema_key,
            "schemas": {
                name: strip_annotations(
                    info.json_schema, keywords, sort_required=True
                )
                for name, info in resolved.schemas.items()
            },
        }
    else:
        schema = (
            resolved.json_schema
            if isinstance(resolved, SchemaInfo)
            else resolved
        )
        document = strip_annotations(schema, keywords, sort_required=True)
    return json.dumps(
        document, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )


def fingerprint_schema(
    target: SchemaTarget
    | SchemaInfo
    | NamedSchemaTargets
    | NamedSchemas
    | Mapping[str, Any],
    *,
    algorithm: str = "sha256",
    include_metadata: bool = False,
) -> str:
    """Hash a schema's canonical JSON (see `canonical_schema_json`).

    Two schemas that differ only in annotations such as titles and descriptions, or in
    the order of ``required`` fields, share a fingerprint; any change to types,
    constraints, or required fields changes it.

    Args:
        target: A schema target, a `SchemaInfo`, named schema targets, `NamedSchemas`,
            or a JSON Schema document.
        algorithm: A fixed-length `hashlib` algorithm name.
        include_metadata: Include annotation keywords in the hash.

    Returns:
        The hexadecimal digest.

    Raises:
        ValueError: If *algorithm* is unavailable or has a variable-length digest.
        SchemaError: If *target* cannot be introspected.
    """
    try:
        hasher = hashlib.new(algorithm)
    except ValueError as exc:
        raise ValueError(f"Unsupported digest algorithm {algorithm!r}") from exc
    if hasher.digest_size == 0:
        raise ValueError(
            f"Variable-length digest algorithm {algorithm!r} is not supported"
        )
    hasher.update(
        canonical_schema_json(
            target, include_metadata=include_metadata
        ).encode()
    )
    return hasher.hexdigest()
