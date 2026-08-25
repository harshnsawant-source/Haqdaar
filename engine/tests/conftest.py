from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "corpus"

#: Fixed "today" for every test. The clock is never read in the deterministic lane, so
#: a golden test cannot start failing because the calendar moved.
TODAY = date(2026, 8, 26)


@pytest.fixture(scope="session")
def today() -> date:
    return TODAY


@pytest.fixture(scope="session")
def corpus_dir() -> Path:
    return CORPUS_DIR


@pytest.fixture(scope="session")
def schemes_dir(corpus_dir: Path) -> Path:
    """The primary (entrepreneur) vertical."""
    return corpus_dir / "entrepreneur" / "schemes"


@pytest.fixture(scope="session")
def welfare_schemes_dir(corpus_dir: Path) -> Path:
    """The reveal vertical."""
    return corpus_dir / "welfare" / "schemes"


def _profile(vertical: str, name: str):
    from haqdaar.profile.schema import load_profile

    return load_profile(CORPUS_DIR / vertical / "personas" / f"{name}.json")


@pytest.fixture(scope="session")
def entrepreneur_profile():
    return _profile("entrepreneur", "entrepreneur-01")


@pytest.fixture(scope="session")
def entrepreneur_02_profile():
    """No caste certificate — the "one document away" persona."""
    return _profile("entrepreneur", "entrepreneur-02")


@pytest.fixture(scope="session")
def sunita_profile():
    """Reveal vertical: 60, widow, small farmer, rural Maharashtra."""
    return _profile("welfare", "sunita")
