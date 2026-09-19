# Why xstructured?

LangChain and LangGraph already provide the foundations: model invocation,
`Runnable` composition, agents, tools, graph state, persistence, callbacks,
and provider-native structured output. Use those features directly when they
match the response contract your application needs.

The distinction is simple:

- **LangChain/LangGraph** decide how a model, chain, agent, or graph runs.
- **Pydantic** defines and validates your data.
- **xstructured** defines one response contract containing both readable
  prose and validated typed data, then adapts that contract to a Runnable.

Each example below states what the ecosystem already provides, the additional
application need, and the small xstructured layer that addresses it.

## Ten practical use cases

### 1. Human explanation plus a machine decision

**Already available:** LangChain can return a Pydantic object through
provider-native structured output or an agent `output_schema`.

**Application need:** A user also needs to read the explanation from the same
response, while software needs a validated decision.

**xstructured solution:** The result exposes both `result.text` and
`result.structured`.

```python
class Decision(BaseModel):
    outcome: Literal["approve", "review", "reject"]
    reason_code: str

chain = with_xstructured_output(model, Decision)
result = chain.invoke("Review this request and explain your decision.")
print(result.text)
print(result.structured.outcome)
```

### 2. A response contract for an existing Runnable

**Already available:** LangChain composes prompts, retrievers, routers, and
custom `Runnable`s.

**Application need:** The existing chain is not an agent and should not be
rewritten just to add a structured response boundary.

**xstructured solution:** Wrap the existing Runnable without changing its
internal composition.

```python
chain = prompt | retriever | model
answer_chain = with_xstructured_output(chain, AnswerSchema)
result = answer_chain.invoke(question)
```

### 3. An adapter for an already-built agent or graph

**Already available:** `create_agent` and LangGraph compiled graphs own state,
tools, transitions, and execution.

**Application need:** An existing graph returns message state, but the
application needs a typed response without redesigning the graph.

**xstructured solution:** Adapt the final message at the graph boundary and
leave orchestration unchanged.

```python
def final_message(messages):
    state = agent.invoke({"messages": list(messages)})
    return state["messages"][-1]

typed_agent = with_xstructured_output(
    RunnableLambda(final_message),
    Incident,
)
```

### 4. Streaming prose and structured events together

**Already available:** LangChain and LangGraph expose streaming primitives for
tokens, messages, updates, and custom events.

**Application need:** A UI should render prose immediately and also know when
the structured object starts, completes, and is safe to use.

**xstructured solution:** Emit ordered text, structured lifecycle, and final
result events from the same response stream.

```python
for event in typed_agent.stream(messages):
    if event.kind is StreamEventKind.TEXT_DELTA:
        print(event.text, end="")
    elif event.kind is StreamEventKind.RESULT:
        save_for_workflow(event.result.structured)
```

### 5. One extraction contract across model providers

**Already available:** LangChain offers provider integrations and provider-
native structured-output methods where supported.

**Application need:** The application wants one response format even when
models or providers differ in structured-output capabilities.

**xstructured solution:** Apply the same envelope and Pydantic validation
after any Runnable that returns text or a message.

```python
extractor = with_xstructured_output(any_provider_model, ProductRecord)
record = extractor.invoke("Extract the product details from this text.")
```

### 6. Valid JSON surrounded by ordinary model formatting

**Already available:** LangChain JSON and Pydantic parsers validate correctly
formatted parser output.

**Application need:** Some models place valid JSON in a Markdown fence or
surround it with a short explanation.

**xstructured solution:** Perform conservative, observable recovery for
harmless formatting while retaining Pydantic as the authority.

```python
parser = StructuredParser(
    ContactInfo,
    config=ParserConfig(recovery=RecoveryConfig(enabled=True)),
)
contact = parser.parse(model_text).value
```

### 7. Explicit limits for untrusted model output

**Already available:** LangChain provides execution controls and callback
hooks; Pydantic validates values after parsing.

**Application need:** A service also needs bounds on response size and JSON
complexity before accepting model-generated content.

**xstructured solution:** Configure input, envelope, payload, and nesting
limits, with explicit failures for unsafe JSON forms.

```python
safe = StructuredParser(
    Event,
    config=ParserConfig(
        max_input_chars=100_000,
        max_payload_chars=40_000,
        max_nesting_depth=32,
    ),
)
```

### 8. Bounded repair after a parse failure

**Already available:** LangChain supports retries and composing a second
Runnable.

**Application need:** A malformed response may be repairable, but automatic
repair must not add hidden model calls or retry forever.

**xstructured solution:** Opt in to a separate repair Runnable with an
explicit attempt limit; the repaired payload must pass the same validation.

```python
typed = with_xstructured_output(
    model,
    Invoice,
    repair=repair_model,
    repair_config=RepairConfig(max_attempts=2),
)
```

### 9. Named typed variants at one boundary

**Already available:** LangGraph can route to different nodes and LangChain
can compose different chains.

**Application need:** A classifier may return one of several typed outcomes,
while callers still want one stable response interface.

**xstructured solution:** Register named Pydantic schemas and inspect the
selected variant from the result.

```python
typed = with_xstructured_output(
    model,
    schemas={"finding": Finding, "recommendation": Recommendation},
)
result = typed.invoke(request)
print(result.schema_name, result.structured)
```

### 10. Traceable schema identity

**Already available:** LangChain callbacks and LangSmith-compatible tracing
can record Runnable executions when configured.

**Application need:** Operations teams need to identify which response schema
was active when a cached, logged, or rejected result was produced.

**xstructured solution:** Expose a deterministic schema fingerprint in result
metadata so application telemetry can correlate response contracts.

```python
result = typed.invoke(request)
fingerprint = result.metadata["schema_fingerprint"]
logger.info("structured_response", extra={"schema": fingerprint})
```

## When native capabilities are the better choice

Prefer LangChain or LangGraph directly when:

- the provider supports the exact structured-only response you need;
- you do not need natural-language text in the same generation;
- `create_agent(output_schema=...)` already matches the application;
- provider-native constrained decoding is a hard requirement; or
- the graph should expose only its native state and no response adapter.

`xstructured` does not replace model integrations, agent orchestration, graph
state, tools, persistence, callbacks, or constrained decoding. It adds a
focused response-protocol boundary where those capabilities alone do not
provide the combination of prose, typed data, extraction, recovery, and
streaming semantics the application requires.
