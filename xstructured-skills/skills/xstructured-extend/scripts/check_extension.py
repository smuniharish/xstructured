"""Check a JsonDecoder, RecoveryStrategy, or Observer against its contract, without pytest.

Imports a factory, detects which extension point its product subclasses, runs
every test of the matching contract from `xstructured.testing`, and reports
one line per promise:

    python scripts/check_extension.py myapp.parsing:LenientDecoder
    python scripts/check_extension.py myapp.metrics:make_observer --json

The factory is a class or a callable that takes no arguments and returns a
new instance. Run it from the project root, or pass --path. Injectors and
extractors need sample inputs; test them with their contract classes in pytest.

Exit codes: 0 every promise holds, 1 a promise is broken, 2 the factory
cannot be imported or does not build a supported extension point.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from importlib import import_module
from pathlib import Path
from typing import Any


def load_factory(spec: str) -> Any:
    module_name, separator, attribute = spec.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError(f"expected MODULE:FACTORY, got {spec!r}")
    target: Any = import_module(module_name)
    for part in attribute.split("."):
        target = getattr(target, part)
    if not callable(target):
        raise TypeError(f"{spec} is not callable")
    return target


def contract_for(factory: Any) -> tuple[str, type]:
    from xstructured import JsonDecoder, Observer, RecoveryStrategy
    from xstructured.testing import (
        JsonDecoderContract,
        ObserverContract,
        RecoveryStrategyContract,
    )

    sample = factory()
    if isinstance(sample, JsonDecoder):

        class Decoder(JsonDecoderContract):
            def make_decoder(self) -> JsonDecoder:
                return factory()

        return "JsonDecoder", Decoder
    if isinstance(sample, RecoveryStrategy):

        class Strategy(RecoveryStrategyContract):
            def make_strategy(self) -> RecoveryStrategy:
                return factory()

        return "RecoveryStrategy", Strategy
    if isinstance(sample, Observer):

        class Telemetry(ObserverContract):
            def make_observer(self) -> Observer:
                return factory()

        return "Observer", Telemetry
    raise TypeError(
        f"the factory returned {type(sample).__name__}, not a JsonDecoder, "
        "RecoveryStrategy, or Observer"
    )


def run_contract(contract: type) -> list[dict[str, Any]]:
    results = []
    for name in sorted(
        name for name in dir(contract) if name.startswith("test_")
    ):
        try:
            getattr(contract(), name)()
        except AssertionError as error:
            results.append({"test": name, "passed": False, "error": str(error)})
        except (
            Exception
        ) as error:  # report every broken promise, then the summary
            detail = "".join(traceback.format_exception_only(error)).strip()
            results.append({"test": name, "passed": False, "error": detail})
        else:
            results.append({"test": name, "passed": True, "error": None})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "factory", help="MODULE:FACTORY returning a new instance"
    )
    parser.add_argument(
        "--json", action="store_true", help="print one JSON object to stdout"
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="directory to import from (default: cwd)",
    )
    arguments = parser.parse_args()
    sys.path.insert(0, str(arguments.path.resolve()))
    try:
        kind, contract = contract_for(load_factory(arguments.factory))
    except Exception as error:
        message = (
            f"cannot load {arguments.factory}: {type(error).__name__}: {error}"
        )
        if arguments.json:
            print(
                json.dumps(
                    {"ok": False, "error": message, "kind": None, "results": []}
                )
            )
        else:
            print(message, file=sys.stderr)
        return 2
    results = run_contract(contract)
    failed = [result for result in results if not result["passed"]]
    if arguments.json:
        report = {
            "ok": not failed,
            "error": None,
            "kind": kind,
            "results": results,
        }
        print(json.dumps(report, indent=2))
    else:
        article = "an" if kind[0] in "AEIOU" else "a"
        print(f"Checking {article} {kind}")
        for result in results:
            line = f"{'PASS' if result['passed'] else 'FAIL'}  {result['test']}"
            print(
                line + (f"\n      {result['error']}" if result["error"] else "")
            )
        print(
            f"All {len(results)} promises hold."
            if not failed
            else f"{len(failed)} of {len(results)} promises broken."
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
