"""Properties of the streaming protocol, including a stateful test of StreamDecoder."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    precondition,
    rule,
)
from pydantic import BaseModel

from tests.support import ChunkRunnable, chunked
from xstructured import (
    EnvelopeSpec,
    StreamDecoder,
    StreamEventKind,
    StructuredParser,
    with_xstructured_output,
)

Kind = StreamEventKind
TEXT = st.text(alphabet=st.characters(exclude_categories=("Cs",)), max_size=40)
PROSE = TEXT.filter(lambda text: "<xstructured>" not in text)
WIDTHS = st.lists(st.integers(min_value=1, max_value=8), max_size=40)


class Message(BaseModel):
    text: str


@given(value=TEXT, before=PROSE, after=TEXT, widths=WIDTHS)
def test_events_preserve_every_character_in_order(
    value: str, before: str, after: str, widths: list[int]
) -> None:
    payload = Message(text=value).model_dump_json()
    document = before + EnvelopeSpec().wrap(payload) + after
    decoder = StreamDecoder(StructuredParser(Message))
    events = [
        event
        for chunk in chunked(document, widths)
        for event in decoder.feed(chunk)
    ]
    decoder.finalize()

    kinds = [event.kind for event in events]
    assert [event.sequence for event in events] == list(range(len(events)))
    assert (
        kinds.count(Kind.STRUCTURED_START)
        == kinds.count(Kind.STRUCTURED_END)
        == 1
    )
    start, end = (
        kinds.index(Kind.STRUCTURED_START),
        kinds.index(Kind.STRUCTURED_END),
    )
    assert "".join(e.text or "" for e in events[:start]) == before
    assert "".join(e.text or "" for e in events[start + 1 : end]) == payload
    assert "".join(e.text or "" for e in events[end + 1 :]) == after
    assert events[end].structured == Message(text=value)
    assert decoder.text == before + after


@given(value=TEXT, before=PROSE, after=TEXT, widths=WIDTHS)
def test_stream_and_invoke_agree(
    value: str, before: str, after: str, widths: list[int]
) -> None:
    document = (
        before
        + EnvelopeSpec().wrap(Message(text=value).model_dump_json())
        + after
    )
    runnable = ChunkRunnable(chunked(document, widths))
    wrapper = with_xstructured_output(runnable, Message)

    invoked = wrapper.invoke("q")
    streamed = list(wrapper.stream("q"))[-1].result

    assert streamed is not None
    assert (streamed.structured, streamed.content, streamed.raw_text) == (
        invoked.structured,
        invoked.content,
        invoked.raw_text,
    )


class DecoderMachine(RuleBasedStateMachine):
    """Feed a fixed document in random pieces and check invariants after every step."""

    document = (
        'Intro "quoted" <xstructured>{"text": "a </xstructured> b \\" c"}'
        "</xstructured> outro"
    )

    def __init__(self) -> None:
        super().__init__()
        self.decoder = StreamDecoder(StructuredParser(Message))
        self.offset = 0
        self.text = ""

    @precondition(lambda self: self.offset < len(self.document))
    @rule(width=st.integers(min_value=0, max_value=12))
    def feed(self, width: int) -> None:
        chunk = self.document[self.offset : self.offset + width]
        self.offset += len(chunk)
        for event in self.decoder.feed(chunk):
            if event.kind is Kind.TEXT_DELTA:
                self.text += event.text or ""

    @precondition(lambda self: self.offset == len(self.document))
    @rule()
    def finish(self) -> None:
        self.decoder.finalize()
        assert self.decoder.result.value == Message(
            text='a </xstructured> b " c'
        )
        assert self.text == 'Intro "quoted"  outro'

    @invariant()
    def released_text_is_a_prefix_of_the_natural_text(self) -> None:
        assert 'Intro "quoted"  outro'.startswith(self.decoder.text)
        assert self.decoder.text == self.text


TestDecoderMachine = DecoderMachine.TestCase
