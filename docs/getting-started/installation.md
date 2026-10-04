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
| Python | 3.12, 3.13, or 3.14 |
| `langchain-core` | 1.6.6 or newer, below 2 |
| `pydantic` | 2.13.5 or newer, below 3 |

These are the only runtime dependencies. `xstructured` never calls a model provider
itself; install the integration you use, for example `langchain` for
`init_chat_model` and `create_agent`, or a provider package such as `langchain-openai`.

## Verify the installation

```python
import xstructured

print(xstructured.__version__)
```

## Working on the repository

The repository uses [uv](https://docs.astral.sh/uv/). `uv sync` installs the package with
the development tools and the example dependencies (LangChain, LangGraph,
`langchain-openai`, and Deep Agents):

```bash
git clone https://github.com/smuniharish/xstructured.git
cd xstructured
uv sync
```

See [Contributing](../contributing.md) for the full development workflow.
