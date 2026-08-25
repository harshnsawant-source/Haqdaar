"""Intake questions are scoped to the domain the citizen chose.

Someone who clicked "money to start a business" was still being asked about widowhood,
BPL status and landholding; someone who came for a pension was asked whether this is
their first business. Which sections belong to which domain is declared in
corpus/intake.yaml, not split in Python or JSX.
"""

import os

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from haqdaar.api.app import PERSONAS  # noqa: E402
from haqdaar.corpus.loader import load_corpus  # noqa: E402
from haqdaar.profile.intake import load_intake, self_declarable_fields  # noqa: E402


@pytest.fixture(scope="module")
def spec(corpus_dir):
    return load_intake(corpus_dir / "intake.yaml")


@pytest.fixture(scope="module")
def client(corpus_dir):
    os.environ["HAQDAAR_CORPUS"] = str(corpus_dir)
    os.environ["HAQDAAR_TODAY"] = "2026-08-22"
    from haqdaar.api.app import app, PERSONAS

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_every_section_declares_its_verticals(spec):
    """No section may drift into "shown everywhere" by omission."""
    for section in spec.sections:
        assert section.verticals, f"{section.section_id} declares no verticals"
        # Sourced from the engine rather than restated, so adding a vertical does not
        # need this assertion edited. It exists to catch a TYPO in a verticals list,
        # which would silently hide a section from every citizen.
        assert set(section.verticals) <= set(PERSONAS.values()), section.section_id


def test_entrepreneur_intake_omits_the_welfare_questions(spec):
    sections = {s.section_id for s in spec.sections_for("entrepreneur")}
    assert "enterprise" in sections
    assert "about-you" in sections and "documents" in sections
    assert "household" not in sections  # no land, BPL or family income
    assert "declarations" not in sections

    questions = {q.question_id for q in spec.questions("entrepreneur")}
    assert "marital_status" in questions  # still relevant to who she is
    assert "bpl" not in questions
    assert "landholding" not in questions


def test_welfare_intake_omits_the_business_questions(spec):
    sections = {s.section_id for s in spec.sections_for("welfare")}
    assert "household" in sections and "declarations" in sections
    assert "enterprise" not in sections

    questions = {q.question_id for q in spec.questions("welfare")}
    assert "venture_type" not in questions
    assert "loan_amount" not in questions


def test_each_vertical_can_still_answer_everything_it_is_entitled_to_settle(
    spec, schemes_dir, welfare_schemes_dir
):
    """The anti-drift test, per vertical.

    A field the corpus says a declaration settles is useless if the domain that uses it
    never asks the question. Scoping the sections must not have hidden one.
    """
    for vertical, directory in (
        ("entrepreneur", schemes_dir),
        ("welfare", welfare_schemes_dir),
    ):
        declarable = self_declarable_fields(load_corpus(directory))
        missing = declarable - spec.answerable_fields(vertical)
        assert missing == set(), (
            f"{vertical} intake has no question for {sorted(missing)}, which its own "
            "corpus says a declaration can settle"
        )


def test_the_endpoint_scopes_by_vertical(client):
    entrepreneur = client.get(
        "/api/intake", params={"vertical": "entrepreneur"}
    ).json()
    welfare = client.get("/api/intake", params={"vertical": "welfare"}).json()

    assert entrepreneur["vertical"] == "entrepreneur"
    entrepreneur_sections = {s["section_id"] for s in entrepreneur["sections"]}
    welfare_sections = {s["section_id"] for s in welfare["sections"]}

    assert "enterprise" in entrepreneur_sections
    assert "enterprise" not in welfare_sections
    assert "household" in welfare_sections
    assert "household" not in entrepreneur_sections
    # Shared sections appear in both.
    assert {"about-you", "documents"} <= entrepreneur_sections & welfare_sections


def test_the_unscoped_endpoint_still_serves_everything(client, spec):
    """No vertical means the whole set — used by tooling, not by the citizen UI."""
    body = client.get("/api/intake").json()
    assert body["vertical"] is None
    # Every section in the file, regardless of vertical.
    assert len(body["sections"]) == len(spec.sections)


def test_an_unknown_vertical_is_refused(client):
    assert client.get("/api/intake", params={"vertical": "nowhere"}).status_code == 404
