from __future__ import annotations

from datetime import date

import pytest
from pydantic import BaseModel, ConfigDict, TypeAdapter

from tests.support import Answer, Label
from xstructured import (
    EnvelopeError,
    EnvelopeSpec,
    LimitExceededError,
    NamedSchemaSpec,
    ParseError,
    ParserConfig,
    RecoveryConfig,
    RecoveryError,
    SchemaError,
    SchemaInfo,
    StructuredParser,
    inspect_named_schemas,
    inspect_schema,
)

NO_RECOVERY = ParserConfig(recovery=RecoveryConfig(enabled=False))


class StrictDate(BaseModel):
    model_config = ConfigDict(strict=True)

    when: date


def test_valid_json_is_parsed_without_recovery() -> None:
    result = StructuredParser(Answer).parse('{"value": 42}')

    assert result.value == Answer(value=42)
    assert result.json_text == '{"value": 42}'
    assert not result.recovered
    assert not result.envelope_found
    assert result.schema_name is None


@pytest.mark.parametrize(
    "text",
    [
        '```json\n{"value": 5}\n```',
        'Sure! Here it is: {"value": 5} Anything else?',
        '\n\n{"value": 5}\n',
    ],
)
def test_conservative_recovery(text: str) -> None:
    result = StructuredParser(Answer).parse(text)

    assert result.value == Answer(value=5)
    assert result.json_text == '{"value": 5}'
    assert result.recovered is (text.strip() != '{"value": 5}')


def test_validation_uses_json_mode_so_strict_models_accept_iso_dates() -> None:
    assert StructuredParser(StrictDate).parse(
        '{"when": "2026-10-04"}'
    ).value == StrictDate(when=date(2026, 10, 4))


def test_type_adapters_and_annotations_are_supported() -> None:
    assert StructuredParser(TypeAdapter(list[int])).parse("[1, 2]").value == [
        1,
        2,
    ]
    assert StructuredParser(dict[str, int]).parse('{"a": 1}').value == {"a": 1}
    assert StructuredParser(inspect_schema(Answer)).parse(
        '{"value": 1}'
    ).value == Answer(value=1)


def test_failed_recovery_reports_every_candidate() -> None:
    with pytest.raises(RecoveryError) as excinfo:
        StructuredParser(Answer).parse('Result: {"value": "nope"}')

    error = excinfo.value
    assert len(error.failures) == 2
    assert error.failures[0].startswith("Expecting value")
    assert error.failures[1].startswith(
        "value: Input should be a valid integer"
    )
    assert str(error).endswith(error.failures[1])
    assert "2 tried" in str(error)
    assert error.text == 'Result: {"value": "nope"}'
    assert error.__cause__ is not None


def test_decode_failures_are_summarized_when_no_candidate_decodes() -> None:
    with pytest.raises(
        RecoveryError, match="Expecting property name"
    ) as excinfo:
        StructuredParser(Answer).parse("{value: 1}")

    assert excinfo.value.failures == (
        "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)",
    )


def test_many_validation_errors_are_summarized() -> None:
    class Wide(BaseModel):
        a: int
        b: int
        c: int
        d: int
        e: int
        f: int
        g: int
        h: int
        i: int
        j: int
        k: int
        m: int

    with pytest.raises(RecoveryError) as excinfo:
        StructuredParser(Wide).parse("{}")

    assert excinfo.value.failures[0].endswith("and 2 more")


def test_without_recovery_a_plain_parse_error_is_raised() -> None:
    with pytest.raises(ParseError, match="Invalid JSON") as excinfo:
        StructuredParser(Answer, config=NO_RECOVERY).parse(
            'Result: {"value": 1}'
        )

    assert not isinstance(excinfo.value, RecoveryError)


@pytest.mark.parametrize("text", ["", "   \n "])
def test_empty_responses_have_a_clear_error(text: str) -> None:
    with pytest.raises(ParseError, match="No JSON content"):
        StructuredParser(Answer).parse(text)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ('{"value": NaN}', "Non-standard JSON constant"),
        ('{"value": 1, "value": 2}', "Duplicate JSON object key"),
        ('{"value": [[[[1]]]]}', "nesting exceeds"),
        ('{"value": 1e999}', "overflows a float"),
    ],
)
def test_unsafe_json_is_rejected(payload: str, message: str) -> None:
    config = ParserConfig(
        max_nesting_depth=3, recovery=RecoveryConfig(enabled=False)
    )

    with pytest.raises(ParseError, match=message):
        StructuredParser(Answer, config=config).parse(payload)


def test_input_limit_is_a_hard_failure() -> None:
    parser = StructuredParser(Answer, config=ParserConfig(max_input_chars=5))

    with pytest.raises(LimitExceededError) as excinfo:
        parser.parse('{"value": 1}')

    assert excinfo.value.limit == "max_input_chars"
    assert excinfo.value.maximum == 5


def test_payload_limit_applies_per_candidate() -> None:
    parser = StructuredParser(Answer, config=ParserConfig(max_payload_chars=12))

    result = parser.parse('A long introduction before the JSON: {"value": 1}')

    assert result.value == Answer(value=1)
    with pytest.raises(RecoveryError, match="exceeds the configured limit"):
        parser.parse('{"value": 10000000000}')


def test_envelope_is_extracted_and_located() -> None:
    parser = StructuredParser(Answer, envelope=EnvelopeSpec("<r>", "</r>"))

    result = parser.parse('Hi <r>{"value": 7}</r> bye')

    assert result.value == Answer(value=7)
    assert result.envelope_spans == ((3, 22),)
    assert result.envelope_found


def test_optional_envelope_falls_back_to_the_whole_text() -> None:
    parser = StructuredParser(Answer, envelope=EnvelopeSpec("<r>", "</r>"))

    assert parser.parse('{"value": 7}').envelope_spans == ()
    assert parser.parse('<r>{"value": 7}').value == Answer(value=7)


def test_required_envelope_must_be_complete() -> None:
    parser = StructuredParser(
        Answer, config=ParserConfig(require_envelope=True)
    )

    assert parser.envelope == EnvelopeSpec()
    assert parser.parse(
        '<xstructured>{"value": 1}</xstructured>'
    ).value == Answer(value=1)
    with pytest.raises(
        ParseError,
        match=r"No complete <xstructured>\.\.\.</xstructured> envelope",
    ):
        parser.parse('{"value": 7}')


def test_recovery_applies_inside_the_envelope() -> None:
    parser = StructuredParser(Answer, envelope=EnvelopeSpec())

    result = parser.parse(
        '<xstructured>\n```json\n{"value": 3}\n```\n</xstructured>'
    )

    assert result.value == Answer(value=3)
    assert result.recovered


def test_envelope_limits_are_enforced() -> None:
    parser = StructuredParser(
        Answer,
        envelope=EnvelopeSpec(),
        config=ParserConfig(max_payload_chars=5),
    )

    with pytest.raises(LimitExceededError, match="payload exceeds"):
        parser.parse('<xstructured>{"value": 42}</xstructured>')


def test_multiple_mode_validates_every_item() -> None:
    parser = StructuredParser(Answer, multiple=True)

    assert parser.parse('[{"value": 1}, {"value": 2}]').value == [
        Answer(value=1),
        Answer(value=2),
    ]
    assert parser.parse("[]").value == []
    with pytest.raises(RecoveryError, match="Expected a JSON array"):
        parser.parse('{"value": 1}')
    with pytest.raises(RecoveryError, match="item 1: value"):
        parser.parse('[{"value": 1}, {"value": "x"}]')


def test_named_schemas_dispatch_on_the_schema_key() -> None:
    parser = StructuredParser({"answer": Answer, "label": Label})

    result = parser.parse('{"schema": "label", "payload": {"name": "ready"}}')

    assert result.value == Label(name="ready")
    assert result.schema_name == "label"
    assert parser.parse(
        '{"schema": "answer", "payload": {"value": 1}, "note": "extra keys are ignored"}'
    ).value == Answer(value=1)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('["not", "an", "object"]', "Expected a JSON object"),
        ('{"payload": {}}', "string schema name"),
        ('{"schema": 3, "payload": {}}', "string schema name"),
        ('{"schema": "answer"}', "Missing 'payload' key"),
        (
            '{"schema": "bogus", "payload": {}}',
            "not one of the configured schema names",
        ),
    ],
)
def test_named_schema_shape_errors(text: str, message: str) -> None:
    parser = StructuredParser(
        {"answer": Answer, "label": Label}, config=NO_RECOVERY
    )

    with pytest.raises(ParseError, match=message):
        parser.parse(text)


def test_named_schema_keys_are_configurable() -> None:
    named = inspect_named_schemas(
        {"answer": Answer},
        spec=NamedSchemaSpec(schema_key="kind", payload_key="data"),
    )

    result = StructuredParser(named).parse(
        '{"kind": "answer", "data": {"value": 9}}'
    )

    assert result.value == Answer(value=9)


def test_named_arrays_report_a_common_schema_name() -> None:
    parser = StructuredParser({"answer": Answer, "label": Label}, multiple=True)

    same = parser.parse('[{"schema": "label", "payload": {"name": "a"}}]')
    mixed = parser.parse(
        '[{"schema": "label", "payload": {"name": "a"}},'
        ' {"schema": "answer", "payload": {"value": 1}}]'
    )

    assert same.schema_name == "label"
    assert mixed.value == [Label(name="a"), Answer(value=1)]
    assert mixed.schema_name is None


def test_parse_payload_skips_envelope_handling() -> None:
    parser = StructuredParser(Answer, envelope=EnvelopeSpec())

    result = parser.parse_payload(' {"value": 4} ')

    assert result.value == Answer(value=4)
    assert result.raw == ' {"value": 4} '
    assert result.envelope_spans == ()


def test_inputs_must_be_strings() -> None:
    parser = StructuredParser(Answer)

    with pytest.raises(TypeError):
        parser.parse(b"{}")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        parser.parse_payload(None)  # type: ignore[arg-type]


def test_conflicting_options_are_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        StructuredParser({"a": Answer}, multiple=True, multiple_envelopes=True)
    with pytest.raises(SchemaError, match="requires named schemas"):
        StructuredParser(Answer, multiple_envelopes=True)
    with pytest.raises(SchemaError, match="JSON Schema document"):
        StructuredParser({"type": "object"})
    with pytest.raises(EnvelopeError, match="tag-style"):
        StructuredParser(
            {"a": Answer},
            multiple_envelopes=True,
            envelope=EnvelopeSpec("[[", "]]"),
        )


def test_unsupported_schema_targets_raise_schema_errors() -> None:
    with pytest.raises(SchemaError, match="Cannot introspect"):
        StructuredParser(object())


def test_parser_exposes_its_configuration() -> None:
    config = ParserConfig(max_input_chars=10)
    parser = StructuredParser(Answer, config=config, multiple=True)

    assert parser.config is config
    assert parser.multiple
    assert not parser.multiple_envelopes
    assert parser.envelope is None
    assert isinstance(parser.schema, SchemaInfo)
    assert parser.schema.name == "Answer"


def test_strip_envelopes_returns_the_natural_language_text() -> None:
    parser = StructuredParser(Answer, envelope=EnvelopeSpec())

    assert (
        parser.strip_envelopes('Hi <xstructured>{"value": 1}</xstructured> bye')
        == "Hi  bye"
    )
    assert (
        parser.strip_envelopes('Hi <xstructured>{"value": 1} trailing') == "Hi "
    )
    assert parser.strip_envelopes("no envelope") == "no envelope"
    assert parser.strip_envelopes("") == ""
    assert StructuredParser(Answer).strip_envelopes(
        "<xstructured>{}</xstructured>"
    ) == ("<xstructured>{}</xstructured>")
