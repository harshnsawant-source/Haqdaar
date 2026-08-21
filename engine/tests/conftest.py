from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "corpus"


@pytest.fixture(scope="session")
def corpus_dir() -> Path:
    return CORPUS_DIR


@pytest.fixture(scope="session")
def schemes_dir(corpus_dir: Path) -> Path:
    return corpus_dir / "schemes"


@pytest.fixture(scope="session")
def entrepreneur_profile():
    from haqdaar.profile.schema import load_profile

    return load_profile(CORPUS_DIR / "personas" / "entrepreneur-01.json")


@pytest.fixture(scope="session")
def entrepreneur_02_profile():
    """No caste certificate — the "one document away" persona."""
    from haqdaar.profile.schema import load_profile

    return load_profile(CORPUS_DIR / "personas" / "entrepreneur-02.json")
