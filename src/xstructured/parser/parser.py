"""Schema-aware parsing of model output."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from itertools import islice
from typing import Any, Literal, overload

from pydantic import TypeAdapter, ValidationError

from xstructured._scan import scan_for_delimiter
from xstructured.core.config import ParserConfig
from xstructured.core.errors import (
    LimitExceededError,
    ParseError,
    RecoveryError,
    SchemaError,
)
from xstructured.core.result import ParseResult
from xstructured.envelope.scanner import EnvelopeScanner, EnvelopeState
from xstructured.envelope.spec import EnvelopeSpec
from xstructured.schema._resolve import is_named_targets
from xstructured.schema.introspection import (
    SchemaInfo,
    SchemaTarget,
    inspect_schema,
)
from xstructured.schema.named import (
    NamedSchemas,
    NamedSchemaTargets,
    inspect_named_schemas,
)

from .json_safety import JsonSafetyError, loads_strict
from .recovery import recovery_candidates

__all__ = ["StructuredParser"]

_CANDIDATE_ERRORS = (RecursionError, SchemaError, TypeError, ValueError)
_MAX_REPORTED_ERRORS = 10

type _Validator = Callable[[Any, str], tuple[Any, str | None]]


@dataclass(frozen=True, slots=True)
class _NamedMatch:
    start: int
    end: int  # -1 when the envelope is malformed or never closed
    name: str
    payload: str


class StructuredParser[T]:
    """Parse model output and validate it against a Pydantic v2 schema.

    Parsing extracts the envelope (when configured), then tries conservative recovery
    candidates in order until one decodes as strict JSON and validates. Validation uses
    Pydantic's JSON mode, so strict models accept JSON representations such as ISO
    dates.

    Args:
        schema: A schema target (model class, `TypeAdapter`, or annotation), a
            `SchemaInfo`, or named schemas (a mapping of names to targets, or
            `NamedSchemas`). With named schemas each value is a JSON object
            ``{"schema": "<name>", "payload": <value>}``, unless *multiple_envelopes* is
            set.
        config: Limits and recovery settings.
        envelope: Extract the JSON from this envelope first. Required envelopes are
            controlled by `ParserConfig.require_envelope`.
        multiple: Expect a JSON array and validate every item; the value is a list.
        multiple_envelopes: Expect one tag-style envelope per named schema, such as
            ``<xstructured name="finding">``; the value is a dict keyed by name.

    Raises:
        ValueError: If *multiple* and *multiple_envelopes* are both set.
        SchemaError: If the schema cannot be introspected, a JSON Schema document is
            passed, or *multiple_envelopes* is set without named schemas.
        EnvelopeError: If *multiple_envelopes* is set with non-tag-style delimiters.

    Example:
        ```python
        from pydantic import BaseModel
        from xstructured import StructuredParser


        class Answer(BaseModel):
            value: int


        result = StructuredParser(Answer).parse('Sure! {"value": 42}')
        assert result.value == Answer(value=42)
        assert result.recovered
        ```
    """

    @overload
    def __init__[S](
        self: StructuredParser[S],
        schema: type[S],
        *,
        config: ParserConfig | None = None,
        envelope: EnvelopeSpec | None = None,
        multiple: Literal[False] = False,
        multiple_envelopes: Literal[False] = False,
    ) -> None: ...

    @overload
    def __init__[S](
        self: StructuredParser[list[S]],
        schema: type[S],
        *,
        config: ParserConfig | None = None,
        envelope: EnvelopeSpec | None = None,
        multiple: Literal[True],
        multiple_envelopes: Literal[False] = False,
    ) -> None: ...

    @overload
    def __init__[S](
        self: StructuredParser[S],
        schema: TypeAdapter[S],
        *,
        config: ParserConfig | None = None,
        envelope: EnvelopeSpec | None = None,
        multiple: Literal[False] = False,
        multiple_envelopes: Literal[False] = False,
    ) -> None: ...

    @overload
    def __init__[S](
        self: StructuredParser[list[S]],
        schema: TypeAdapter[S],
        *,
        config: ParserConfig | None = None,
        envelope: EnvelopeSpec | None = None,
        multiple: Literal[True],
        multiple_envelopes: Literal[False] = False,
    ) -> None: ...

    @overload
    def __init__(
        self: StructuredParser[dict[str, Any]],
        schema: NamedSchemaTargets | NamedSchemas,
        *,
        config: ParserConfig | None = None,
        envelope: EnvelopeSpec | None = None,
        multiple: Literal[False] = False,
        multiple_envelopes: Literal[True],
    ) -> None: ...

    @overload
    def __init__(
        self: StructuredParser[Any],
        schema: SchemaTarget | SchemaInfo | NamedSchemaTargets | NamedSchemas,
        *,
        config: ParserConfig | None = None,
        envelope: EnvelopeSpec | None = None,
        multiple: bool = False,
        multiple_envelopes: bool = False,
    ) -> None: ...

    def __init__(
        self,
        schema: SchemaTarget | SchemaInfo | NamedSchemaTargets | NamedSchemas,
        *,
        config: ParserConfig | None = None,
        envelope: EnvelopeSpec | None = None,
        multiple: bool = False,
        multiple_envelopes: bool = False,
    ) -> None:
        if multiple and multiple_envelopes:
            raise ValueError(
                "multiple and multiple_envelopes are mutually exclusive"
            )
        resolved: SchemaInfo | NamedSchemas
        if isinstance(schema, (SchemaInfo, NamedSchemas)):
            resolved = schema
        elif is_named_targets(schema):
            resolved = inspect_named_schemas(schema)
        elif isinstance(schema, Mapping):
            raise SchemaError(
                "StructuredParser needs Pydantic schema targets; a JSON Schema document "
                "cannot validate values"
            )
        else:
            resolved = inspect_schema(schema)
        if multiple_envelopes and not isinstance(resolved, NamedSchemas):
            raise SchemaError("multiple_envelopes requires named schemas")

        self._config = config or ParserConfig()
        if envelope is None and (
            multiple_envelopes or self._config.require_envelope
        ):
            envelope = EnvelopeSpec()
        self._named_envelopes: tuple[NamedSchemas, EnvelopeSpec] | None = None
        if (
            multiple_envelopes
            and isinstance(resolved, NamedSchemas)
            and envelope is not None
        ):
            _ = envelope.named_prefix  # Validates tag-style delimiters.
            self._named_envelopes = (resolved, envelope)
        self._schema = resolved
        self._envelope = envelope
        self._multiple = multiple

    @property
    def schema(self) -> SchemaInfo | NamedSchemas:
        """The resolved schema or named schemas."""
        return self._schema

    @property
    def config(self) -> ParserConfig:
        """Limits and recovery settings."""
        return self._config

    @property
    def envelope(self) -> EnvelopeSpec | None:
        """The envelope delimiters, or ``None`` when the whole text is parsed."""
        return self._envelope

    @property
    def multiple(self) -> bool:
        """Whether a JSON array of values is expected."""
        return self._multiple

    @property
    def multiple_envelopes(self) -> bool:
        """Whether one named envelope per schema is expected."""
        return self._named_envelopes is not None

    def parse(self, text: str) -> ParseResult[T]:
        """Parse one complete response.

        Raises:
            TypeError: If *text* is not a string.
            LimitExceededError: If a resource limit is exceeded.
            RecoveryError: If no recovery candidate validates (recovery enabled).
            ParseError: For every other parsing or validation failure.
        """
        if not isinstance(text, str):
            raise TypeError("Parser input must be a string")
        maximum = self._config.max_input_chars
        if len(text) > maximum:
            raise LimitExceededError(
                f"Input exceeds the configured limit of {maximum} characters",
                text=text,
                limit="max_input_chars",
                maximum=maximum,
            )
        if self._named_envelopes is not None:
            return self._parse_named_envelopes(text, *self._named_envelopes)
        payload, spans = self._extract(text)
        value, json_text, recovered, schema_name = self._first_valid(
            payload, self._validate, raw=text, label=""
        )
        return ParseResult(
            value=value,
            raw=text,
            json_text=json_text,
            recovered=recovered,
            envelope_spans=spans,
            schema_name=schema_name,
        )

    def parse_payload(self, payload: str) -> ParseResult[T]:
        """Parse JSON text that was already extracted from its envelope.

        Recovery and validation work as in `parse`; envelope handling and the input
        limit are skipped. `ParseResult.raw` is the payload itself.

        Raises:
            TypeError: If *payload* is not a string.
            ValueError: If the parser expects named envelopes.
            RecoveryError: If no recovery candidate validates (recovery enabled).
            ParseError: For every other parsing or validation failure.
        """
        if not isinstance(payload, str):
            raise TypeError("Parser input must be a string")
        if self._named_envelopes is not None:
            raise ValueError("parse_payload does not support named envelopes")
        value, json_text, recovered, schema_name = self._first_valid(
            payload, self._validate, raw=payload, label=""
        )
        return ParseResult(
            value=value,
            raw=payload,
            json_text=json_text,
            recovered=recovered,
            schema_name=schema_name,
        )

    def strip_envelopes(self, text: str) -> str:
        """Return the natural-language part of *text*, with every envelope removed.

        Complete envelopes are removed. An envelope that is never closed is removed
        together with everything after it. Without a configured envelope *text* is
        returned unchanged.
        """
        envelope = self._envelope
        if envelope is None:
            return text
        if self._named_envelopes is not None:
            parts: list[str] = []
            position = 0
            for match in _scan_named(text, envelope):
                parts.append(text[position : match.start])
                if match.end < 0:
                    return "".join(parts)
                position = match.end
            parts.append(text[position:])
            return "".join(parts)
        limit = max(len(text), 1)
        scanner = EnvelopeScanner(
            envelope, max_envelope_chars=limit, max_payload_chars=limit
        )
        scan = scanner.feed(text)
        if scanner.span is not None:
            start, end = scanner.span
            return text[:start] + text[end:]
        if scanner.state is EnvelopeState.COLLECTING:
            return scan.text_before
        return text

    def _extract(self, text: str) -> tuple[str, tuple[tuple[int, int], ...]]:
        envelope = self._envelope
        if envelope is None:
            return text, ()
        scanner = EnvelopeScanner(
            envelope,
            max_envelope_chars=self._config.max_envelope_chars,
            max_payload_chars=self._config.max_payload_chars,
        )
        scanner.feed(text)
        if scanner.payload is not None and scanner.span is not None:
            return scanner.payload, (scanner.span,)
        if self._config.require_envelope:
            raise ParseError(
                f"No complete {envelope.start}...{envelope.end} envelope was found",
                text=text,
            )
        return text, ()

    def _parse_named_envelopes(
        self, text: str, named: NamedSchemas, envelope: EnvelopeSpec
    ) -> ParseResult[T]:
        values: dict[str, Any] = {}
        json_texts: dict[str, str] = {}
        spans: list[tuple[int, int]] = []
        recovered = False
        for match in _scan_named(text, envelope):
            if match.end < 0:
                problem = (
                    f"Named envelope {match.name!r} is not closed"
                    if match.name
                    else "Named envelope opening delimiter is not closed"
                )
                raise ParseError(problem, text=text)
            if match.name not in named.schemas:
                raise ParseError(
                    f"Unknown named envelope {match.name!r}; expected one of {list(named.names)}",
                    text=text,
                )
            if match.name in values:
                raise ParseError(
                    f"Duplicate named envelope {match.name!r}", text=text
                )
            self._check_named_limits(match, text)
            value, json_text, was_recovered, _ = self._first_valid(
                match.payload,
                _schema_validator(named.schemas[match.name]),
                raw=text,
                label=f"named envelope {match.name!r}",
            )
            values[match.name] = value
            json_texts[match.name] = json_text
            spans.append((match.start, match.end))
            recovered = recovered or was_recovered
        if not values:
            raise ParseError(
                f'No named {envelope.named_prefix}NAME">...{envelope.end} envelopes were found',
                text=text,
            )
        combined = ",".join(
            f"{json.dumps(name)}:{body}" for name, body in json_texts.items()
        )
        result: ParseResult[Any] = ParseResult(
            value=values,
            raw=text,
            json_text=f"{{{combined}}}",
            recovered=recovered,
            envelope_spans=tuple(spans),
        )
        return result

    def _check_named_limits(self, match: _NamedMatch, text: str) -> None:
        payload_limit = self._config.max_payload_chars
        if len(match.payload) > payload_limit:
            raise LimitExceededError(
                f"Named envelope {match.name!r} payload exceeds the configured limit of "
                f"{payload_limit} characters",
                text=text,
                limit="max_payload_chars",
                maximum=payload_limit,
            )
        envelope_limit = self._config.max_envelope_chars
        if match.end - match.start > envelope_limit:
            raise LimitExceededError(
                f"Named envelope {match.name!r} exceeds the configured limit of "
                f"{envelope_limit} characters",
                text=text,
                limit="max_envelope_chars",
                maximum=envelope_limit,
            )

    def _first_valid(
        self, payload: str, validate: _Validator, *, raw: str, label: str
    ) -> tuple[Any, str, bool, str | None]:
        recovery = self._config.recovery
        candidates: Iterator[str] = (
            islice(
                recovery_candidates(
                    payload,
                    strip_markdown_fences=recovery.strip_markdown_fences,
                    strip_surrounding_text=recovery.strip_surrounding_text,
                ),
                recovery.max_candidates,
            )
            if recovery.enabled
            else iter((payload,))
        )
        failures: list[str] = []
        first_error: BaseException | None = None
        schema_failure: tuple[str, BaseException] | None = None
        for index, candidate in enumerate(candidates):
            try:
                decoded = self._decode(candidate)
            except _CANDIDATE_ERRORS as exc:
                failures.append(_describe(exc))
                first_error = first_error or exc
                continue
            try:
                value, schema_name = validate(decoded, candidate)
            except _CANDIDATE_ERRORS as exc:
                failures.append(_describe(exc))
                first_error = first_error or exc
                schema_failure = schema_failure or (failures[-1], exc)
                continue
            return value, candidate, index > 0, schema_name

        where = f" in {label}" if label else ""
        if not failures:
            raise ParseError(f"No JSON content was found{where}", text=raw)
        # A schema failure of decodable JSON explains the problem better than decode errors.
        summary, cause = schema_failure or (failures[0], first_error)
        if recovery.enabled:
            raise RecoveryError(
                f"No recovery candidate{where} is valid JSON matching the schema "
                f"({len(failures)} tried): {summary}",
                text=raw,
                failures=tuple(failures),
            ) from cause
        raise ParseError(f"Invalid JSON{where}: {summary}", text=raw) from cause

    def _decode(self, candidate: str) -> Any:
        if len(candidate) > self._config.max_payload_chars:
            raise JsonSafetyError(
                "JSON payload exceeds the configured limit of "
                f"{self._config.max_payload_chars} characters"
            )
        return loads_strict(
            candidate, max_nesting_depth=self._config.max_nesting_depth
        )

    def _validate(self, decoded: Any, candidate: str) -> tuple[Any, str | None]:
        if not self._multiple:
            return self._validate_item(decoded, candidate)
        if not isinstance(decoded, list):
            raise TypeError("Expected a JSON array of values")
        values: list[Any] = []
        names: set[str | None] = set()
        for index, item in enumerate(decoded):
            try:
                value, name = self._validate_item(item, None)
            except _CANDIDATE_ERRORS as exc:
                raise ValueError(f"item {index}: {_describe(exc)}") from exc
            values.append(value)
            names.add(name)
        return values, names.pop() if len(names) == 1 else None

    def _validate_item(
        self, decoded: Any, candidate: str | None
    ) -> tuple[Any, str | None]:
        schema = self._schema
        if isinstance(schema, SchemaInfo):
            text = candidate if candidate is not None else _dumps(decoded)
            return schema.validate_json(text), None
        spec = schema.spec
        if not isinstance(decoded, dict):
            raise TypeError(
                f"Expected a JSON object with {spec.schema_key!r} and {spec.payload_key!r} keys"
            )
        name = decoded.get(spec.schema_key)
        if not isinstance(name, str):
            raise TypeError(
                f"Expected {spec.schema_key!r} to be a string schema name"
            )
        if spec.payload_key not in decoded:
            raise ValueError(f"Missing {spec.payload_key!r} key")
        return schema.resolve(name).validate_json(
            _dumps(decoded[spec.payload_key])
        ), name


def _scan_named(text: str, envelope: EnvelopeSpec) -> list[_NamedMatch]:
    """Find named envelopes in order; a malformed or unclosed one ends the list."""
    matches: list[_NamedMatch] = []
    prefix = envelope.named_prefix
    position = 0
    while (start := text.find(prefix, position)) >= 0:
        name_start = start + len(prefix)
        name_end = text.find('">', name_start)
        if name_end < 0:
            matches.append(_NamedMatch(start, -1, "", ""))
            break
        name = text[name_start:name_end]
        payload_start = name_end + 2
        scan = scan_for_delimiter(text, envelope.end, start=payload_start)
        if scan.index < 0:
            matches.append(_NamedMatch(start, -1, name, text[payload_start:]))
            break
        end = scan.index + len(envelope.end)
        matches.append(
            _NamedMatch(start, end, name, text[payload_start : scan.index])
        )
        position = end
    return matches


def _schema_validator(info: SchemaInfo) -> _Validator:
    def validate(_decoded: Any, candidate: str) -> tuple[Any, str | None]:
        return info.validate_json(candidate), None

    return validate


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _describe(error: BaseException) -> str:
    if not isinstance(error, ValidationError):
        return str(error)
    details = [
        f"{'.'.join(str(part) for part in item['loc']) or '(root)'}: {item['msg']}"
        for item in error.errors(include_url=False)
    ]
    shown = "; ".join(details[:_MAX_REPORTED_ERRORS])
    hidden = len(details) - _MAX_REPORTED_ERRORS
    return f"{shown}; and {hidden} more" if hidden > 0 else shown
