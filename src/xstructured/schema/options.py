"""Pydantic options passed through to schema generation and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import ConfigDict
from pydantic.json_schema import (
    DEFAULT_REF_TEMPLATE,
    GenerateJsonSchema,
    JsonSchemaMode,
)

__all__ = ["SchemaOptions"]


@dataclass(frozen=True, slots=True, kw_only=True)
class SchemaOptions:
    """Options forwarded to Pydantic's `TypeAdapter`.

    Every field maps to the Pydantic argument of the same purpose, so a schema
    behaves inside xstructured exactly as it does with Pydantic directly.

    Attributes:
        config: `ConfigDict` for annotation targets such as ``list[Item]`` or a
            ``TypedDict``. Pydantic rejects it for model classes and dataclasses,
            which carry their own configuration.
        strict: Validate in strict mode (`TypeAdapter.validate_json` ``strict``).
        extra: Override how extra fields are handled: ``"ignore"``, ``"allow"``,
            or ``"forbid"``.
        context: Default validation context passed to validators. A per-call
            context passed to `StructuredParser.parse` or through
            ``RunnableConfig["configurable"]["xstructured_context"]`` replaces it.
        by_alias: Accept field aliases during validation.
        by_name: Accept field names during validation.
        json_schema_by_alias: Use aliases in the generated JSON Schema.
        ref_template: Template for ``$ref`` values in the JSON Schema.
        union_format: How unions of primitive types are rendered in the JSON Schema.
        schema_generator: `GenerateJsonSchema` subclass that builds the JSON Schema.
        json_schema_mode: Generate the JSON Schema for ``"validation"`` or
            ``"serialization"``.
    """

    config: ConfigDict | None = None
    strict: bool | None = None
    extra: Literal["allow", "ignore", "forbid"] | None = None
    context: Any = None
    by_alias: bool | None = None
    by_name: bool | None = None
    json_schema_by_alias: bool = True
    ref_template: str = DEFAULT_REF_TEMPLATE
    union_format: Literal["any_of", "primitive_type_array"] = "any_of"
    schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema
    json_schema_mode: JsonSchemaMode = "validation"
