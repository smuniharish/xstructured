"""Schema-aware JSON parser."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Generic, TypeVar, cast

from xstructured.core import ParseError, ParserConfig, ParseResult, RecoveryError, SchemaError
from xstructured.envelope import EnvelopeScanner, EnvelopeSpec
from xstructured.schema import SchemaInfo, SchemaTarget, inspect_schema
from xstructured.schema.named import NamedSchemas, NamedSchemaTargets, inspect_named_schemas

from .json_safety import JsonSafetyError, loads_strict
from .recovery import recovery_candidates

T = TypeVar("T")


class StructuredParser(Generic[T]):
    """Parse JSON text and validate it with a Pydantic v2 schema target.

    *schema* is either a single schema target (a `BaseModel` subclass, a
    `TypeAdapter`, or anything `TypeAdapter` accepts) or a *named* set of
    schema targets -- a `Mapping[str, SchemaTarget]` or an already-built
    `NamedSchemas`. With named schemas, the JSON payload must be a single
    object shaped ``{"schema": "<name>", "payload": <value>}`` and
    `ParseResult.schema_name` reports which named schema matched. With
    ``multiple=True``, the JSON value must be an array and each item is
    validated independently; named schemas may be mixed in that array.
    """

    def __init__(
        self,
        schema: SchemaTarget | NamedSchemaTargets | NamedSchemas,
        *,
        config: ParserConfig | None = None,
        envelope: EnvelopeSpec | None = None,
        multiple: bool = False,
        multiple_envelopes: bool = False,
    ) -> None:
        if isinstance(schema, NamedSchemas):
            self.schema: SchemaInfo | None = None
            self.named_schemas: NamedSchemas | None = schema
        elif isinstance(schema, Mapping):
            self.schema = None
            self.named_schemas = inspect_named_schemas(schema)
        else:
            self.schema = inspect_schema(schema)
            self.named_schemas = None
        self.config = config or ParserConfig()
        self.envelope = envelope
        self.multiple = multiple
        self.multiple_envelopes = multiple_envelopes

    def parse(self, text: str) -> ParseResult[T]:
        """Parse one response, optionally extracting its configured envelope."""
        if not isinstance(text, str):
            raise TypeError("Parser input must be a string")
        if len(text) > self.config.max_input_chars:
            raise ParseError(
                f"Input exceeds configured limit of {self.config.max_input_chars} characters", text
            )

        if self.multiple_envelopes:
            return self._parse_named_envelopes(text)
        json_text, envelope_found = self._extract_envelope(text)
        candidates = [json_text]
        if self.config.recovery.enabled:
            candidates = list(
                recovery_candidates(
                    json_text,
                    strip_markdown_fences=self.config.recovery.strip_markdown_fences,
                    strip_surrounding_text=self.config.recovery.strip_surrounding_text,
                )
            )[: self.config.recovery.max_candidates]

        failures: list[str] = []
        last_error: Exception | None = None
        for index, candidate in enumerate(candidates):
            try:
                if len(candidate) > self.config.max_payload_chars:
                    raise JsonSafetyError(
                        "JSON payload exceeds configured limit of "
                        f"{self.config.max_payload_chars} characters"
                    )
                decoded: Any = loads_strict(
                    candidate,
                    max_nesting_depth=self.config.max_nesting_depth,
                )
                value, schema_name = self._validate(decoded)
            except (JsonSafetyError, ValueError, TypeError, SchemaError) as exc:
                failures.append(str(exc))
                last_error = exc
                continue
            return ParseResult(
                value=value,
                raw=text,
                json_text=candidate,
                recovered=index > 0,
                envelope_found=envelope_found,
                schema_name=schema_name,
            )

        if self.config.recovery.enabled:
            raise RecoveryError(
                "Unable to parse and validate any recovery candidate",
                text,
                last_error,
                tuple(failures),
            ) from last_error
        detail = f": {last_error}" if last_error is not None else ""
        raise ParseError(
            f"Unable to parse and validate JSON{detail}", text, last_error
        ) from last_error

    def _parse_named_envelopes(self, text: str) -> ParseResult[T]:
        if self.named_schemas is None:
            raise SchemaError("multiple_envelopes requires named schema targets")
        pattern = re.compile(
            r'<xstructured name="([A-Za-z0-9_.-]+)">(.*?)</xstructured>',
            re.DOTALL,
        )
        matches = list(pattern.finditer(text))
        if not matches:
            raise ParseError("No named xstructured envelopes were found", text)
        values: dict[str, Any] = {}
        for match in matches:
            name, payload = match.groups()
            if name in values:
                raise ParseError(f"Duplicate named envelope: {name!r}", text)
            if name not in self.named_schemas.schemas:
                raise ParseError(f"Unknown named envelope: {name!r}", text)
            if len(payload) > self.config.max_payload_chars:
                raise ParseError("Named envelope payload exceeds configured limit", text)
            try:
                decoded = loads_strict(payload, max_nesting_depth=self.config.max_nesting_depth)
                values[name] = self.named_schemas.resolve(name).validate_python(decoded)
            except (JsonSafetyError, ValueError, TypeError, SchemaError) as exc:
                raise ParseError(f"Invalid named envelope {name!r}: {exc}", text, exc) from exc
        return ParseResult(
            value=cast(T, values),
            raw=text,
            json_text="".join(match.group(2) for match in matches),
            envelope_found=True,
        )

    def _validate(self, decoded: Any) -> tuple[Any, str | None]:
        if self.multiple:
            if not isinstance(decoded, list):
                raise ValueError("Multiple payload mode requires a JSON array")
            values: list[Any] = []
            names: list[str] = []
            for item in decoded:
                value, name = self._validate_one(item)
                values.append(value)
                if name is not None:
                    names.append(name)
            schema_name = names[0] if names and all(name == names[0] for name in names) else None
            return values, schema_name
        return self._validate_one(decoded)

    def _validate_one(self, decoded: Any) -> tuple[Any, str | None]:
        if self.schema is not None:
            return self.schema.validate_python(decoded), None
        assert self.named_schemas is not None
        spec = self.named_schemas.spec
        if not isinstance(decoded, dict):
            raise ValueError("Named schema payloads must be a JSON object")
        if spec.schema_key not in decoded:
            raise ValueError(f"Missing required {spec.schema_key!r} discriminator key")
        name = decoded[spec.schema_key]
        if not isinstance(name, str):
            raise ValueError(f"{spec.schema_key!r} must be a string schema name")
        if spec.payload_key not in decoded:
            raise ValueError(f"Missing required {spec.payload_key!r} payload key")
        schema_info = self.named_schemas.resolve(name)
        return schema_info.validate_python(decoded[spec.payload_key]), name

    def _extract_envelope(self, text: str) -> tuple[str, bool]:
        if self.envelope is None:
            if self.config.require_envelope:
                raise ParseError(
                    "An envelope is required but no envelope spec was configured",
                    text,
                )
            return text, False
        scanner = EnvelopeScanner(
            self.envelope,
            max_envelope_chars=self.config.max_envelope_chars,
            max_payload_chars=self.config.max_payload_chars,
        )
        scanner.feed(text)
        if scanner.complete:
            return scanner.finalize(), True
        if self.config.require_envelope:
            raise ParseError("No complete envelope was found", text)
        return text, False
