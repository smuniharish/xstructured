# Integrations

`xstructured` attaches to LangChain in three ways and depends only on
`langchain-core`; the agent middleware and OpenTelemetry observer come with
optional extras.

| Attach mode | Use it for | Extra |
| --- | --- | --- |
| `with_xstructured_output(runnable, schema)` | Chat models, chains, and any Runnable; repair and structured streaming | none |
| `XStructuredMiddleware(schema)` | `create_agent` and `create_deep_agent` agents | `agents` |
| `XStructuredOutputParser(schema)` | The last step of a `prompt \| model \| parser` chain | none |

<div class="grid cards" markdown>

-   :material-link-variant: __[LangChain Runnables](langchain.md)__

    Chat models, chains, the output parser, batching, and tracing.

-   :material-robot-outline: __[Agents and Deep Agents](agents.md)__

    `XStructuredMiddleware` for `create_agent` and `create_deep_agent`.

-   :material-graph-outline: __[LangGraph](langgraph.md)__

    Validated values in graph state and routing on typed fields.

-   :material-chart-timeline-variant: __[OpenTelemetry](opentelemetry.md)__

    One span per call, with sizes, counts, and flags as attributes.

-   :material-help-circle-outline: __[Why xstructured?](why-xstructured.md)__

    When it helps, and when LangChain's native structured output is the better choice.

</div>
