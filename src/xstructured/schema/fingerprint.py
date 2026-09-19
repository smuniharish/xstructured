"""Deterministic JSON Schema serialization and hashing."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .introspection import SchemaTarget, inspect_schema
from .named import NamedSchemas, inspect_named_schemas

_NON_SEMANTIC_KEYS = frozenset({"$id", "title", "description", "examples", "default"})


def canonical_schema_json(
    target: SchemaTarget | dict[str, Any] | NamedSchemas, *, include_metadata: bool = False
) -> str:
    """Return stable JSON for a schema target, a JSON Schema mapping, or named schemas."""
    if isinstance(target, Mapping) and _looks_like_named_targets(target):
        target = inspect_named_schemas(target)
    if isinstance(target, NamedSchemas):
        schema: dict[str, Any] = {
            "schema_key": target.spec.schema_key,
            "payload_key": target.spec.payload_key,
            "schemas": {name: info.json_schema for name, info in target.schemas.items()},
        }
    else:
        schema = target if isinstance(target, dict) else inspect_schema(target).json_schema
    normalized = _normalize(schema, include_metadata=include_metadata)
    return json.dumps(normalized, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _looks_like_named_targets(target: Mapping[str, Any]) -> bool:
    """Distinguish a mapping of Pydantic targets from a JSON Schema mapping."""
    schema_keywords = {"type", "properties", "items", "$defs", "anyOf", "oneOf", "allOf"}
    return not any(key in schema_keywords for key in target)


def fingerprint_schema(
    target: SchemaTarget | dict[str, Any] | NamedSchemas,
    *,
    algorithm: str = "sha256",
    include_metadata: bool = False,
) -> str:
    """Hash a schema's canonical representation."""
    try:
        hasher = hashlib.new(algorithm)
    except ValueError as exc:
        raise ValueError(f"Unsupported digest algorithm: {algorithm}") from exc
    hasher.update(canonical_schema_json(target, include_metadata=include_metadata).encode("utf-8"))
    return hasher.hexdigest()


def _normalize(value: Any, *, include_metadata: bool) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize(item, include_metadata=include_metadata)
            for key, item in sorted(value.items())
            if include_metadata or key not in _NON_SEMANTIC_KEYS
        }
    if isinstance(value, list):
        return [_normalize(item, include_metadata=include_metadata) for item in value]
    return value
