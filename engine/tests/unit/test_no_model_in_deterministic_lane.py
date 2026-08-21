"""Prove "no model involved" instead of asserting it.

The deterministic lane (corpus, profile schema, eligibility) must not reach a model or
a network. This walks the import graph statically, so it holds even for code paths no
test happens to execute.
"""

import ast
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "haqdaar"

DETERMINISTIC_LANE = [
    PACKAGE_ROOT / "corpus",
    PACKAGE_ROOT / "eligibility",  # includes evaluate.py, verdict.py, aggregate.py
    PACKAGE_ROOT / "guard",
    PACKAGE_ROOT / "profile" / "schema.py",
]

FORBIDDEN_ROOTS = {
    # our own model lane
    "haqdaar.llm",
    # anything that could reach the network
    "http",
    "httpx",
    "requests",
    "urllib",
    "socket",
    "aiohttp",
    # model SDKs
    "anthropic",
    "openai",
    "google",
    "ollama",
    "transformers",
    "torch",
}


def _python_files() -> list[Path]:
    files: list[Path] = []
    for target in DETERMINISTIC_LANE:
        if target.is_dir():
            files.extend(sorted(target.rglob("*.py")))
        else:
            files.append(target)
    return files


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module)
    return roots


def test_deterministic_lane_has_files_to_check():
    # Guards against the test silently passing because the glob found nothing.
    names = {p.name for p in _python_files()}
    assert {"evaluate.py", "verdict.py", "aggregate.py", "triggers.py"} <= names


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: p.name)
def test_no_model_or_network_import(path: Path):
    for module in _imported_roots(path):
        head = module.split(".")[0]
        assert module not in FORBIDDEN_ROOTS and head not in FORBIDDEN_ROOTS, (
            f"{path.relative_to(PACKAGE_ROOT)} imports {module} — the deterministic "
            "lane must not reach a model or a network"
        )


def test_importing_the_evaluator_does_not_load_the_model_lane():
    for name in [m for m in sys.modules if m.startswith("haqdaar")]:
        del sys.modules[name]

    import haqdaar.eligibility.evaluate  # noqa: F401

    loaded = {m for m in sys.modules if m.startswith("haqdaar.llm")}
    assert loaded == set()
