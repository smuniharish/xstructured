# Architecture

`xstructured` sits between a LangChain `Runnable` and your application. The
wrapped runnable continues to do its work; the library separates a model's
natural-language response from the structured payload, validates the latter as a
Pydantic model, and returns both together.

The repository's docs describe the boundary clearly:

- [Architecture overview](https://xstructured.readthedocs.io/en/latest/architecture/overview/)
- [LangChain integration](https://xstructured.readthedocs.io/en/latest/integrations/langchain/)
- [Why xstructured?](https://xstructured.readthedocs.io/en/latest/integrations/why-xstructured/)

## Public behavior

The public behavior is intentionally small:

1. `schema_instructions` can add schema guidance when an input supports it.
2. `StructuredParser` separates text from a JSON-like payload.
3. Recovery strips markdown fences and surrounding prose when safe.
4. Validation checks the payload against the target Pydantic model.
5. `XStructuredResult` preserves the text, validated object, raw output, and
   metadata.

## Request lifecycle

For invocation, the wrapped runnable is called with the user's input, the reply
is parsed into prose plus structured JSON, and the JSON is checked against the
schema. For streaming, the same protocol is interpreted incrementally so a UI
can render events in order while retaining a typed object for downstream work.

## Boundaries to preserve

- `xstructured` does not replace LangChain orchestration.
- It does not call a provider itself.
- It is not a new agent framework or parser framework.
- It adds a response contract around an existing runnable, rather than rewriting
  that runnable or the rest of the application.
