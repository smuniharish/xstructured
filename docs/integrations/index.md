# Integrations

`xstructured` integrates at the LangChain `Runnable` level, so it works with anything that
implements the standard `invoke`, `batch`, `stream`, and async interface, and it depends
only on `langchain-core`.

<div class="grid cards" markdown>

-   :material-link-variant: __[LangChain Runnables](langchain.md)__

    Chat models, chains, prompt templates, composition, batching, and tracing.

-   :material-robot-outline: __[Agents and Deep Agents](agents.md)__

    `create_agent` and `create_deep_agent` graphs through a small adapter.

-   :material-graph-outline: __[LangGraph](langgraph.md)__

    Validated values in graph state and routing on typed fields.

-   :material-help-circle-outline: __[Why xstructured?](why-xstructured.md)__

    When it helps, and when LangChain's native structured output is the better choice.

</div>
