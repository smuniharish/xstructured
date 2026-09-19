# Installation

```bash
pip install xstructured
```

or with [uv](https://docs.astral.sh/uv/):

```bash
uv add xstructured
```

`xstructured` depends only on `langchain-core` and `pydantic`; it does not
pull in `langchain`, a specific model provider, or `deepagents`. To run the
example scripts against a real `create_agent` agent (and, optionally, a
`deepagents` deep agent), install this repository's `examples`
[dependency group](https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups):

```bash
uv sync --group examples
```

## Requirements

- Python 3.11 or newer.
- `langchain-core` 1.x.
- `pydantic` 2.9 or newer.
