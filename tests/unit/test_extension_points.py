from __future__ import annotations

import ast
from collections.abc import Iterator, Mapping
from typing import Annotated, Any, override

import pytest
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationInfo,
    computed_field,
    field_validator,
)
from pydantic.json_schema import GenerateJsonSchema

from xstructured import (
    ConservativeRecovery,
    DefaultInstructionRenderer,
    DefaultRepairPrompt,
    EnvelopeSpec,
    InstructionRenderer,
    JsonDecoder,
    NamedSchemas,
    OutputTextExtractor,
    ParseError,
    ParserConfig,
    RecoveryConfig,
    RecoveryStrategy,
    SchemaError,
    SchemaInfo,
    SchemaOptions,
    StreamDecoder,
    StrictJsonDecoder,
    StructuredParser,
    inspect_named_schemas,
    inspect_schema,
    schema_instructions,
)
from xstructured.contracts import require_instance
from xstructured.testing import JsonDecoderContract, RecoveryStrategyContract


class Scored(BaseModel):
    score: int

    @field_validator("score")
    @classmethod
    def within_limit(cls, value: int, info: ValidationInfo) -> int:
        limit = (info.context or {}).get("limit")
        if limit is not None and value > limit:
            raise ValueError(f"score must be at most {limit}")
        return value


class Aliased(BaseModel):
    model_config = ConfigDict(populate_by_name=False)

    full_name: str = Field(alias="fullName")


class TestStrictJsonDecoder(JsonDecoderContract):
    def make_decoder(self) -> JsonDecoder:
        return StrictJsonDecoder()


class TestConservativeRecovery(RecoveryStrategyContract):
    def make_strategy(self) -> RecoveryStrategy:
        return ConservativeRecovery()


class LiteralDecoder(JsonDecoder):
    """Accepts Python literals such as single-quoted strings."""

    @override
    def decode(self, text: str, *, max_nesting_depth: int) -> Any:
        try:
            return ast.literal_eval(text)
        except (SyntaxError, ValueError) as exc:
            raise ValueError(str(exc)) from exc


class LastLineRecovery(RecoveryStrategy):
    @override
    def candidates(self, text: str) -> Iterator[str]:
        yield text.strip()
        yield text.strip().splitlines()[-1]


class ShoutingRenderer(DefaultInstructionRenderer):
    @override
    def render(
        self,
        schema: SchemaInfo | NamedSchemas | Mapping[str, Any],
        *,
        envelope: EnvelopeSpec | None,
        multiple: bool,
        multiple_envelopes: bool,
    ) -> str:
        return (
            super()
            .render(
                schema,
                envelope=envelope,
                multiple=multiple,
                multiple_envelopes=multiple_envelopes,
            )
            .upper()
        )


class BareRenderer(InstructionRenderer):
    @override
    def render(
        self,
        schema: SchemaInfo | NamedSchemas | Mapping[str, Any],
        *,
        envelope: EnvelopeSpec | None,
        multiple: bool,
        multiple_envelopes: bool,
    ) -> str:
        return f"Answer as {getattr(schema, 'name', 'JSON')}."


class EchoExtractor(OutputTextExtractor):
    @override
    def text(self, output: Any) -> str:
        if not isinstance(output, str):
            raise TypeError("no text")
        return output


def test_custom_decoders_validate_the_serialized_value() -> None:
    parser = StructuredParser(Scored, decoder=LiteralDecoder())

    parsed = parser.parse("{'score': 3}")

    assert parsed.value == Scored(score=3)
    assert parsed.json_text == '{"score": 3}'
    assert parser.decoder.__class__ is LiteralDecoder


def test_decoder_errors_other_than_value_errors_propagate() -> None:
    class Broken(JsonDecoder):
        @override
        def decode(self, text: str, *, max_nesting_depth: int) -> Any:
            raise RuntimeError("decoder bug")

    with pytest.raises(RuntimeError, match="decoder bug"):
        StructuredParser(Scored, decoder=Broken()).parse('{"score": 1}')


def test_custom_recovery_strategies_choose_the_candidates() -> None:
    config = ParserConfig(recovery=RecoveryConfig(enabled=True))
    parser = StructuredParser(
        Scored, config=config, recovery=LastLineRecovery()
    )

    parsed = parser.parse('Here you go:\n{"score": 4}')

    assert parsed.value == Scored(score=4)
    assert parsed.recovered
    assert isinstance(parser.recovery, LastLineRecovery)


def test_the_default_strategy_and_decoder_are_exposed() -> None:
    parser = StructuredParser(Scored)

    assert repr(parser.recovery) == (
        "ConservativeRecovery(strip_markdown_fences=True, "
        "strip_surrounding_text=True)"
    )
    assert repr(parser.decoder) == "StrictJsonDecoder()"
    assert repr(DefaultRepairPrompt()) == "DefaultRepairPrompt()"


def test_renderers_replace_the_instructions() -> None:
    shouted = schema_instructions(Scored, renderer=ShoutingRenderer())
    bare = schema_instructions(Scored, renderer=BareRenderer())

    assert shouted == schema_instructions(Scored).upper()
    assert bare == "Answer as Scored."


def test_extension_points_must_subclass_their_base() -> None:
    with pytest.raises(
        TypeError, match="decoder must be an instance of JsonDecoder"
    ):
        StructuredParser(Scored, decoder=object())  # type: ignore[arg-type]
    with pytest.raises(
        TypeError, match="renderer must be an instance of InstructionRenderer"
    ):
        schema_instructions(Scored, renderer=object())  # type: ignore[arg-type]
    assert require_instance(StrictJsonDecoder(), JsonDecoder, "decoder")


def test_extractors_default_chunk_text_to_text() -> None:
    assert EchoExtractor().chunk_text("chunk") == "chunk"


def test_validation_context_defaults_and_overrides() -> None:
    parser = StructuredParser(
        Scored, schema_options=SchemaOptions(context={"limit": 5})
    )

    assert parser.parse('{"score": 5}').value == Scored(score=5)
    with pytest.raises(ParseError, match="at most 5"):
        parser.parse('{"score": 6}')
    assert parser.parse('{"score": 6}', context={"limit": 9}).value == Scored(
        score=6
    )


def test_stream_decoders_use_the_call_context() -> None:
    parser = StructuredParser(Scored, envelope=EnvelopeSpec())
    decoder = StreamDecoder(parser, context={"limit": 1})

    with pytest.raises(ParseError, match="at most 1"):
        decoder.feed('<xstructured>{"score": 2}</xstructured>')


def test_strict_and_extra_are_applied() -> None:
    lenient = StructuredParser(Scored)
    strict = StructuredParser(Scored, schema_options=SchemaOptions(strict=True))
    forbid = StructuredParser(
        Scored, schema_options=SchemaOptions(extra="forbid")
    )

    assert lenient.parse('{"score": "3", "x": 1}').value == Scored(score=3)
    with pytest.raises(ParseError):
        strict.parse('{"score": "3"}')
    with pytest.raises(ParseError):
        forbid.parse('{"score": 3, "x": 1}')


def test_alias_options_are_applied() -> None:
    by_name = StructuredParser(
        Aliased, schema_options=SchemaOptions(by_alias=False, by_name=True)
    )
    names = inspect_schema(
        Aliased, options=SchemaOptions(json_schema_by_alias=False)
    )

    assert by_name.parse('{"full_name": "Ada"}').value.full_name == "Ada"
    assert "full_name" in names.json_schema["properties"]
    assert "fullName" in inspect_schema(Aliased).json_schema["properties"]


def test_json_schema_generation_options_are_applied() -> None:
    class Titled(GenerateJsonSchema):
        @override
        def generate(self, schema: Any, mode: Any = "validation") -> Any:
            result = super().generate(schema, mode=mode)
            result["x-generator"] = "titled"
            return result

    class Item(BaseModel):
        value: int | str

        @computed_field
        @property
        def label(self) -> str:
            return str(self.value)

    class Box(BaseModel):
        item: Item

    info = inspect_schema(
        Box,
        options=SchemaOptions(
            ref_template="#/components/{model}",
            union_format="primitive_type_array",
            schema_generator=Titled,
            json_schema_mode="serialization",
        ),
    )

    assert info.json_schema["properties"]["item"]["$ref"] == (
        "#/components/Item"
    )
    assert info.json_schema["x-generator"] == "titled"
    item = info.json_schema["$defs"]["Item"]
    assert item["properties"]["value"]["type"] == ["integer", "string"]
    assert "label" in item["properties"]


def test_config_applies_to_annotation_targets() -> None:
    info = inspect_schema(
        list[Annotated[str, Field(min_length=1)]],
        options=SchemaOptions(config=ConfigDict(str_strip_whitespace=True)),
    )

    assert info.validate_json('["  a  "]') == ["a"]


def test_config_cannot_be_applied_to_type_adapters() -> None:
    with pytest.raises(SchemaError, match="existing TypeAdapter"):
        inspect_schema(
            TypeAdapter(int), options=SchemaOptions(config=ConfigDict())
        )


def test_schema_infos_are_rebuilt_only_with_new_options() -> None:
    info = inspect_schema(Scored)
    strict = SchemaOptions(strict=True)

    rebuilt = inspect_schema(info, options=strict)

    assert inspect_schema(info) is info
    assert rebuilt is not info
    assert rebuilt.options is strict
    assert rebuilt.target is Scored


def test_named_schemas_are_rebuilt_with_options() -> None:
    named = inspect_named_schemas({"scored": Scored})
    strict = SchemaOptions(strict=True)

    rebuilt = inspect_named_schemas(named, options=strict)

    assert inspect_named_schemas(named) is named
    assert rebuilt.schemas["scored"].options is strict
    assert rebuilt.spec == named.spec
