"""Schema-guided structured output for LangChain v1 Runnables and agents.

``xstructured`` turns one model response into natural-language text plus a value
validated by Pydantic v2. Wrap any Runnable with `with_xstructured_output`, add
`XStructuredMiddleware` (``xstructured.agents``) to an agent, or use
`StructuredParser` and `StreamDecoder` directly on text you already have. Every
behavior is customizable through the abstract base classes in
`xstructured.contracts`.
"""

from importlib.metadata import version as _version

from .contracts import (
    AttributeValue,
    InstructionInjector,
    InstructionRenderer,
    JsonDecoder,
    Observation,
    Observer,
    OutputTextExtractor,
    RecoveryStrategy,
    RepairPromptBuilder,
)
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
from .langchain import (
    CONTEXT_KEY,
    INSTRUCTIONS_MESSAGE_ID,
    DefaultRepairPrompt,
    MessageInstructionInjector,
    MessageTextExtractor,
    XStructuredOutputParser,
    XStructuredRunnable,
    with_xstructured_output,
)
from .parser import (
    ConservativeRecovery,
    JsonSafetyError,
    StrictJsonDecoder,
    StructuredParser,
)
from .schema import (
    DefaultInstructionRenderer,
    NamedSchemas,
    NamedSchemaSpec,
    NamedSchemaTargets,
    SchemaInfo,
    SchemaOptions,
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
    "CONTEXT_KEY",
    "INSTRUCTIONS_MESSAGE_ID",
    "AttributeValue",
    "ConservativeRecovery",
    "DefaultInstructionRenderer",
    "DefaultRepairPrompt",
    "EnvelopeError",
    "EnvelopeScanner",
    "EnvelopeSpec",
    "EnvelopeState",
    "InstructionInjector",
    "InstructionRenderer",
    "JsonDecoder",
    "JsonSafetyError",
    "LimitExceededError",
    "MessageInstructionInjector",
    "MessageTextExtractor",
    "NamedSchemaSpec",
    "NamedSchemaTargets",
    "NamedSchemas",
    "Observation",
    "Observer",
    "OutputTextExtractor",
    "ParseError",
    "ParseResult",
    "ParserConfig",
    "RecoveryConfig",
    "RecoveryError",
    "RecoveryStrategy",
    "RepairConfig",
    "RepairError",
    "RepairPromptBuilder",
    "ScanEvent",
    "SchemaError",
    "SchemaInfo",
    "SchemaOptions",
    "SchemaTarget",
    "StreamDecoder",
    "StreamEvent",
    "StreamEventKind",
    "StrictJsonDecoder",
    "StructuredParser",
    "XStructuredError",
    "XStructuredOutputParser",
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
