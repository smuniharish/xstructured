# Troubleshooting

Use the repository examples and issue-driven checks before changing parsing or
schema behavior:

- [LangChain integration](https://xstructured.readthedocs.io/en/latest/integrations/langchain/)
- [Why xstructured?](https://xstructured.readthedocs.io/en/latest/integrations/why-xstructured/)
- [Examples](https://github.com/smuniharish/xstructured/tree/master/examples)
- [Tests](https://github.com/smuniharish/xstructured/tree/master/tests)

## Common problems

### The model output is surrounded by prose or markdown fences

This is expected in imperfect providers. Use the built-in recovery and parsing
logic rather than slicing the response by hand. Prefer `StructuredParser` or
`with_xstructured_output` to handle fences and surrounding prose conservatively.

### The application is losing the natural-language answer

The availability of both `text` and `structured` is part of the API. Keep the
`XStructuredResult` and avoid discarding the original model response unless the
workflow explicitly only needs the structured object.

### The response is malformed or partially missing

Validate the actual raw model output and retry with explicit repair rules only
when the application genuinely allows repair. Do not silently change schema or
bypass validation.

### The agent graph returns state dicts rather than plain message data

Wrap the final message at the boundary, not the entire graph state. This is the
pattern shown in the repository's `create_agent` examples.

### The parsing is too permissive or too strict

Tighten or relax `ParserConfig` and the recovery policy deliberately, then test
against realistic model output and schema failures. Keep the security and
correctness tradeoff visible in the application.
