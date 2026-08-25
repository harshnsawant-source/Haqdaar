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
    PACKAGE_ROOT / "action",  # form fill is slot-mapping; no model writes a filed value
    PACKAGE_ROOT / "render",  # rendering is slot-fill; no model runs after the verdict
    PACKAGE_ROOT / "retrieval",  # routing is lexical; no embedding service
    PACKAGE_ROOT / "profile" / "schema.py",
    PACKAGE_ROOT / "profile" / "intake.py",  # answers in, profile out; no model
]

FORBIDDEN_ROOTS = {
    # our own model lane
    "haqdaar.llm",
    # the input boundary: OCR/extraction may not be reached from the verdict path
    "haqdaar.profile.ocr",
    "haqdaar.profile.extract",
    "pytesseract",
    "PIL",
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
    assert {
        "evaluate.py",
        "verdict.py",
        "aggregate.py",
        "triggers.py",
        "gate.py",
        "render.py",
        "route.py",
        "fill.py",
        "track.py",
        "intake.py",
    } <= names


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: p.name)
def test_no_model_or_network_import(path: Path):
    for module in _imported_roots(path):
        head = module.split(".")[0]
        assert module not in FORBIDDEN_ROOTS and head not in FORBIDDEN_ROOTS, (
            f"{path.relative_to(PACKAGE_ROOT)} imports {module} — the deterministic "
            "lane must not reach a model or a network"
        )


def test_importing_the_evaluator_does_not_load_the_model_lane():
    """Import the evaluator into a clean interpreter and assert the model lane stays out.

    The purge below MUST be restored. Without the restore, every test module that runs
    after this one holds references to the pre-purge classes while the engine hands
    back freshly re-imported ones, so `x is SomeEnum.MEMBER` starts returning False for
    reasons that have nothing to do with the code under test. That cost real debugging
    time on 2026-08-26; the snapshot is not optional tidiness.
    """
    snapshot = {m: mod for m, mod in sys.modules.items() if m.startswith("haqdaar")}
    try:
        for name in snapshot:
            del sys.modules[name]

        import haqdaar.eligibility.evaluate  # noqa: F401

        loaded = {m for m in sys.modules if m.startswith("haqdaar.llm")}
        assert loaded == set()
    finally:
        for name in [m for m in sys.modules if m.startswith("haqdaar")]:
            del sys.modules[name]
        sys.modules.update(snapshot)


# --- the extraction boundary is one-way --------------------------------------

EXTRACTION_MODULES = [
    PACKAGE_ROOT / "profile" / "ocr.py",
    PACKAGE_ROOT / "profile" / "extract.py",
]

#: Extraction may read the profile schema (it produces one) and nothing else of ours.
ALLOWED_FROM_EXTRACTION = {"haqdaar.profile", "haqdaar.profile.schema", "haqdaar.profile.ocr"}


def test_extraction_modules_exist():
    assert all(p.is_file() for p in EXTRACTION_MODULES)


@pytest.mark.parametrize("path", EXTRACTION_MODULES, ids=lambda p: p.name)
def test_extraction_cannot_reach_the_verdict_path(path: Path):
    """One-way boundary.

    The deterministic lane must not import extraction (asserted above), and extraction
    must not import the evaluator, Guard, renderer or action layer. If extraction could
    reach them it could influence a verdict, and the model/OCR boundary would stop
    meaning anything.
    """
    for module in _imported_roots(path):
        if not module.startswith("haqdaar"):
            continue
        assert module in ALLOWED_FROM_EXTRACTION, (
            f"{path.name} imports {module} — extraction is the input boundary and "
            "must not reach the verdict path"
        )


def test_the_deterministic_lane_and_extraction_do_not_overlap():
    lane = {p.resolve() for p in _python_files()}
    extraction = {p.resolve() for p in EXTRACTION_MODULES}
    assert lane.isdisjoint(extraction)
