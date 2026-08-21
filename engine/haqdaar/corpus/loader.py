"""Load and validate scheme YAML.

`strict=True` returns only VERIFIED schemes. It is a live tripwire, not decoration:
`tests/unit/test_corpus_loader.py` asserts strict mode currently yields zero schemes,
and that test starts passing differently the day the content lane lands real rules.
Nothing unverified can reach a strict consumer by accident.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from haqdaar.corpus.schema import Scheme, VerificationStatus


class CorpusError(Exception):
    """Raised when a corpus file is unreadable or fails schema validation."""


def load_scheme(path: str | Path) -> Scheme:
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise CorpusError(f"{path.name}: cannot read — {exc}") from exc
    if not isinstance(raw, dict):
        raise CorpusError(f"{path.name}: expected a mapping at the top level")
    try:
        return Scheme.model_validate(raw)
    except Exception as exc:
        raise CorpusError(f"{path.name}: {exc}") from exc


def load_corpus(directory: str | Path, *, strict: bool = False) -> list[Scheme]:
    """Load every *.yaml in `directory`, sorted by scheme_id.

    strict=True drops PROVISIONAL schemes rather than presenting unverified rules.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise CorpusError(f"{directory}: not a directory")

    schemes = [load_scheme(p) for p in sorted(directory.glob("*.yaml"))]

    ids = [s.scheme_id for s in schemes]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise CorpusError(f"duplicate scheme_id(s): {sorted(duplicates)}")

    if strict:
        schemes = [
            s for s in schemes if s.verification_status is VerificationStatus.VERIFIED
        ]
    return sorted(schemes, key=lambda s: s.scheme_id)
