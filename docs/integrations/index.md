# Integrations

`xstructured` integrates with the LangChain ecosystem at the `Runnable`
level, so it works with anything that exposes LangChain's standard
`invoke`/`ainvoke`/`batch`/`abatch`/`stream`/`astream` interface.

- **[LangChain](langchain.md)** -- the primary integration:
  `with_xstructured_output` wraps a chat model, `create_agent` agent, or
  any other `Runnable`.
- **[Deep Agents](deepagents.md)** -- an optional integration for
  [`deepagents`](https://github.com/langchain-ai/deepagents)'s
  `create_deep_agent`, using the same wrapping pattern as `create_agent`.

Neither `langchain` (the agent-construction package) nor `deepagents` is a
required dependency of `xstructured` -- only `langchain-core` is. Both
integrations are demonstrated as env-gated scripts under
[`examples/`](../examples/index.md) rather than as installable extras,
since there is no `xstructured`-owned integration code beyond the
`RunnableLambda` adapter pattern shown there.
