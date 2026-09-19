"""Named multiple schema targets: dispatch, instructions, and fingerprints."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from xstructured import (
    NamedSchemas,
    NamedSchemaSpec,
    StructuredParser,
    fingerprint_schema,
    inspect_named_schemas,
    schema_instructions,
)
from xstructured.core import ParseError, ParserConfig, RecoveryError, SchemaError


class Contact(BaseModel):
    name: str
    email: str


class Ticket(BaseModel):
    priority: str


def test_parser_validates_multiple_payloads_in_one_array() -> None:
    parser: StructuredParser[object] = StructuredParser(
        {"contact": Contact, "ticket": Ticket},
        multiple=True,
    )

    result = parser.parse(
        '<xstructured>['
        '{"schema": "contact", "payload": {"name": "Priya", "email": "p@example.com"}},'
        '{"schema": "ticket", "payload": {"priority": "high"}}'
        ']</xstructured>'
    )

    assert result.value == [
        Contact(name="Priya", email="p@example.com"),
        Ticket(priority="high"),
    ]
    assert result.schema_name is None


def test_parser_multiple_mode_requires_an_array() -> None:
    parser: StructuredParser[object] = StructuredParser(Contact, multiple=True)

    with pytest.raises(RecoveryError) as excinfo:
        parser.parse('{"name": "Priya", "email": "p@example.com"}')
    assert any("JSON array" in attempt for attempt in excinfo.value.attempts)


def test_parser_supports_multiple_separately_named_envelopes() -> None:
    parser: StructuredParser[object] = StructuredParser(
        {"contact": Contact, "ticket": Ticket},
        multiple_envelopes=True,
    )

    result = parser.parse(
        'Analysis:\n'
        '<xstructured name="contact">{"name":"Priya","email":"p@example.com"}</xstructured>\n'
        'Action:\n'
        '<xstructured name="ticket">{"priority":"high"}</xstructured>'
    )

    assert result.value == {
        "contact": Contact(name="Priya", email="p@example.com"),
        "ticket": Ticket(priority="high"),
    }


def test_parser_rejects_duplicate_named_envelopes() -> None:
    parser: StructuredParser[object] = StructuredParser(
        {"contact": Contact},
        multiple_envelopes=True,
    )

    with pytest.raises(ParseError, match="Duplicate named envelope"):
        parser.parse(
            '<xstructured name="contact">{"name":"A","email":"a@example.com"}</xstructured>'
            '<xstructured name="contact">{"name":"B","email":"b@example.com"}</xstructured>'
        )


def test_inspect_named_schemas_requires_at_least_one_target() -> None:
    with pytest.raises(SchemaError, match="At least one"):
        inspect_named_schemas({})


def test_named_schema_spec_rejects_empty_or_equal_keys() -> None:
    with pytest.raises(SchemaError):
        NamedSchemaSpec(schema_key="", payload_key="payload")
    with pytest.raises(SchemaError):
        NamedSchemaSpec(schema_key="same", payload_key="same")


def test_parser_dispatches_to_the_named_schema_and_reports_its_name() -> None:
    parser: StructuredParser[object] = StructuredParser({"contact": Contact, "ticket": Ticket})

    contact_result = parser.parse(
        '{"schema": "contact", "payload": {"name": "Priya", "email": "p@example.com"}}'
    )
    assert contact_result.value == Contact(name="Priya", email="p@example.com")
    assert contact_result.schema_name == "contact"

    ticket_result = parser.parse('{"schema": "ticket", "payload": {"priority": "high"}}')
    assert ticket_result.value == Ticket(priority="high")
    assert ticket_result.schema_name == "ticket"


def test_parser_accepts_a_prebuilt_named_schemas_object() -> None:
    named = inspect_named_schemas({"contact": Contact, "ticket": Ticket})
    assert isinstance(named, NamedSchemas)

    parser: StructuredParser[object] = StructuredParser(named)
    result = parser.parse('{"schema": "ticket", "payload": {"priority": "low"}}')

    assert result.value == Ticket(priority="low")
    assert result.schema_name == "ticket"


def test_parser_rejects_an_unknown_schema_name() -> None:
    parser: StructuredParser[object] = StructuredParser({"contact": Contact, "ticket": Ticket})

    with pytest.raises(RecoveryError):
        parser.parse('{"schema": "bogus", "payload": {}}')


def test_parser_rejects_missing_discriminator_or_payload_keys() -> None:
    parser: StructuredParser[object] = StructuredParser({"contact": Contact})

    with pytest.raises(RecoveryError):
        parser.parse('{"payload": {"name": "Priya", "email": "p@example.com"}}')
    with pytest.raises(RecoveryError):
        parser.parse('{"schema": "contact"}')


def test_named_schema_payload_still_supports_conservative_recovery() -> None:
    parser: StructuredParser[object] = StructuredParser({"contact": Contact})

    result = parser.parse(
        'Here:\n```json\n{"schema": "contact", '
        '"payload": {"name": "Priya", "email": "p@example.com"}}\n```\n'
    )

    assert result.recovered
    assert result.schema_name == "contact"


def test_named_schemas_still_honor_an_envelope() -> None:
    from xstructured import EnvelopeSpec

    parser: StructuredParser[object] = StructuredParser(
        {"contact": Contact},
        envelope=EnvelopeSpec("<result>", "</result>"),
        config=ParserConfig(require_envelope=True),
    )

    result = parser.parse(
        'ignored <result>{"schema": "contact", '
        '"payload": {"name": "Priya", "email": "p@example.com"}}</result> ignored'
    )

    assert result.envelope_found
    assert result.schema_name == "contact"


def test_schema_instructions_list_every_named_schema_and_the_shape() -> None:
    named = inspect_named_schemas({"contact": Contact, "ticket": Ticket})

    instructions = schema_instructions(named, envelope="xstructured")

    assert "inside the `xstructured` envelope" in instructions
    assert '"schema": "<name>"' in instructions
    assert "'contact', 'ticket'" in instructions
    assert 'Schema "contact"' in instructions
    assert 'Schema "ticket"' in instructions
    assert '"email"' in instructions
    assert '"priority"' in instructions


def test_fingerprint_schema_is_stable_and_order_independent_for_named_schemas() -> None:
    first = inspect_named_schemas({"contact": Contact, "ticket": Ticket})
    second = inspect_named_schemas({"ticket": Ticket, "contact": Contact})

    assert fingerprint_schema(first) == fingerprint_schema(second)


def test_fingerprint_schema_differs_when_named_schemas_change() -> None:
    only_contact = inspect_named_schemas({"contact": Contact})
    both = inspect_named_schemas({"contact": Contact, "ticket": Ticket})

    assert fingerprint_schema(only_contact) != fingerprint_schema(both)


def test_fingerprint_schema_differs_from_a_single_schema_target() -> None:
    single = fingerprint_schema(Contact)
    named = fingerprint_schema(inspect_named_schemas({"contact": Contact}))

    assert single != named
