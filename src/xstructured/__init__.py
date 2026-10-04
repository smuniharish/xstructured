"""Schema-guided structured output for LangChain v1 Runnables and agents.

``xstructured`` turns one model response into natural-language text plus a value
validated by Pydantic v2. Wrap any Runnable with `with_xstructured_output`, or use
`StructuredParser` and `StreamDecoder` directly on text you already have.
"""

from importlib.metadata import version as _version

from .core import (
    EnvelopeError,
    LimitExceededError,
    ParseError,
    ParserConfig,
    ParseResult,
    RecoveryConfig,
    RecoveryError,
    RepairConfig,
    RepairError,
    SchemaError,
    XStructuredError,
    XStructuredResult,
)
from .envelope import EnvelopeScanner, EnvelopeSpec, EnvelopeState, ScanEvent
from .langchain import XStructuredRunnable, with_xstructured_output
from .parser import StructuredParser
from .schema import (
    NamedSchemas,
    NamedSchemaSpec,
    NamedSchemaTargets,
    SchemaInfo,
    SchemaTarget,
    canonical_schema_json,
    fingerprint_schema,
    inspect_named_schemas,
    inspect_schema,
    schema_instructions,
)
from .streaming import StreamDecoder, StreamEvent, StreamEventKind

__version__ = _version("xstructured")

__all__ = [
    "EnvelopeError",
    "EnvelopeScanner",
    "EnvelopeSpec",
    "EnvelopeState",
    "LimitExceededError",
    "NamedSchemaSpec",
    "NamedSchemaTargets",
    "NamedSchemas",
    "ParseError",
    "ParseResult",
    "ParserConfig",
    "RecoveryConfig",
    "RecoveryError",
    "RepairConfig",
    "RepairError",
    "ScanEvent",
    "SchemaError",
    "SchemaInfo",
    "SchemaTarget",
    "StreamDecoder",
    "StreamEvent",
    "StreamEventKind",
    "StructuredParser",
    "XStructuredError",
    "XStructuredResult",
    "XStructuredRunnable",
    "__version__",
    "canonical_schema_json",
    "fingerprint_schema",
    "inspect_named_schemas",
    "inspect_schema",
    "schema_instructions",
    "with_xstructured_output",
]
