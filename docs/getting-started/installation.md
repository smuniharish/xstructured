# Installation

=== "pip"

    ```bash
    pip install xstructured
    ```

=== "uv"

    ```bash
    uv add xstructured
    ```

## Requirements

| Requirement | Version |
| --- | --- |
| Python | 3.12, 3.13, 3.14, or 3.15 |
| `langchain-core` | 1.7.6 or newer, below 2 |
| `pydantic` | 2.14.3 or newer, below 3 |

These are the only runtime dependencies of the core package. `xstructured`
never calls a model provider itself; install the provider package you use, such
as `langchain-openai`.

## Optional extras

| Extra | Installs | Enables |
| --- | --- | --- |
| `agents` | `langchain` | `xstructured.agents.XStructuredMiddleware` for `create_agent` |
| `deepagents` | `deepagents` | The middleware with `create_deep_agent` |
| `langgraph` | `langgraph` | Wrappers inside LangGraph nodes |
| `otel` | `opentelemetry-api` | `xstructured.otel.OpenTelemetryObserver` |
| `all` | All of the above | Everything |

```bash
pip install "xstructured[agents,otel]"
```

`import xstructured` never imports an optional dependency; only the
`xstructured.agents` and `xstructured.otel` submodules need their extras.

## Verify the installation

```python
import xstructured

print(xstructured.__version__)
```

## Working on the repository

The repository uses [uv](https://docs.astral.sh/uv/). `uv sync` installs the
package with every extra, the development tools, and the example dependencies:

```bash
git clone https://github.com/smuniharish/xstructured.git
cd xstructured
uv sync
```

See [Contributing](../contributing.md) for the full development workflow.
