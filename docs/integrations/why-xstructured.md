# Why xstructured?

LangChain and LangGraph already provide model integrations, composition, agents, graph
state, persistence, callbacks, and provider-native structured output. `xstructured` adds
one thing on top: a response contract in which a single model response carries readable
prose **and** validated data, with predictable behavior when the model's formatting is
imperfect.

## Use it when

**You need prose and data from the same response.**
A support assistant explains a decision to the user while your code acts on a validated
`Decision`. Native structured output returns only the structured value.

**You wrap something that is not a bare chat model.**
Existing chains, custom Runnables, and agent graphs gain a typed result at their boundary
without being rebuilt.

**You stream to a user interface.**
Text appears as it is generated, and the structured payload is validated the moment it
completes, from the same stream.

**You use several providers or models.**
One envelope-based contract works with any model that follows instructions, including
models without native structured-output support.

**Model formatting is imperfect.**
Fenced JSON and chatty preambles are recovered conservatively and observably
(`recovered=True`), and malformed output can be repaired within a fixed budget.

**Untrusted output must be bounded.**
Size and nesting limits, strict JSON decoding, and typed exceptions are built in.

**You need traceable contracts.**
Schema fingerprints in result metadata identify exactly which response contract
produced a cached or logged value.

## Prefer native features when

- the provider's native structured output (or `with_structured_output`) already returns
  exactly the value you need, and you do not need prose alongside it;
- you build an agent and only need its final structured answer:
  `create_agent(response_format=...)` handles that natively;
- constrained decoding, where the provider guarantees schema-valid output, is a hard
  requirement.

## Comparison

| Capability | Native structured output | `JsonOutputParser` / `PydanticOutputParser` | xstructured |
| --- | :---: | :---: | :---: |
| Prose and data in one response | — | — | ✓ |
| Works with any Runnable or model | provider-dependent | ✓ | ✓ |
| Streams text and structured events | — | partial JSON | ✓ |
| Rejects truncated or ambiguous JSON | ✓ | — | ✓ |
| Rejects duplicate keys and `NaN` | provider-dependent | — | ✓ |
| Size and nesting limits | — | — | ✓ |
| Bounded, opt-in repair | — | — | ✓ |
| Schema fingerprints | — | — | ✓ |

The [benchmarks](../benchmarks.md) measure the parser rows of this table.
