"""Guided intake, and the evidence semantics that make it safe.

The product promise is "tell us your situation and we tell you what you qualify for".
Intake is the front door for that. What it must never become is a way to talk the
engine into an entitlement: a citizen's word settles what the corpus says her word
settles, and not one clause more.
"""

import os

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from haqdaar.corpus.loader import load_corpus  # noqa: E402
from haqdaar.eligibility.evaluate import evaluate_corpus  # noqa: E402
from haqdaar.eligibility.verdict import Evaluation, Status  # noqa: E402
from haqdaar.profile.intake import (  # noqa: E402
    build_intake_profile,
    load_intake,
    self_declarable_fields,
)
from haqdaar.profile.schema import FieldOrigin, load_profile  # noqa: E402
from haqdaar.render.render import BANNED_PHRASES  # noqa: E402


@pytest.fixture(scope="module")
def spec(corpus_dir):
    return load_intake(corpus_dir / "intake.yaml")


@pytest.fixture(scope="module")
def client(corpus_dir):
    os.environ["HAQDAAR_CORPUS"] = str(corpus_dir)
    os.environ["HAQDAAR_TODAY"] = "2026-08-22"
    from haqdaar.api.app import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


#: Sunita's fixture, restated as things she would say at an intake desk.
SUNITA_ANSWERS = {
    "age": 60,
    "gender": "FEMALE",
    "marital_status": "WIDOW",
    "landholding": 0.8,
    "paid_income_tax": False,
    "government_employee": False,
    "constitutional_post": False,
    "registered_professional": False,
    "institutional_landholder": False,
    "monthly_pension": 0,
}
SUNITA_DOCUMENTS = ["aadhaar", "husband_death_certificate", "land_record_7_12"]


# --- anti-drift: every declarable clause has a question ---------------------


def test_every_self_declarable_field_has_an_intake_question(
    spec, schemes_dir, welfare_schemes_dir
):
    """Adding a scheme must not leave a clause a citizen cannot answer.

    If the corpus says a self-declaration settles a clause, intake has to ask about it
    — otherwise she is entitled to settle it on her own account and has no way to say
    so, and the engine blocks her for a paper she does not need.
    """
    schemes = load_corpus(schemes_dir) + load_corpus(welfare_schemes_dir)
    declarable = self_declarable_fields(schemes)
    assert declarable, "no self-declarable clauses at all — has the corpus changed?"

    missing = declarable - spec.answerable_fields()
    assert missing == set(), (
        f"intake.yaml has no question for {sorted(missing)}, which the corpus says a "
        "self-declaration can settle"
    )


def test_every_intake_question_maps_somewhere_real(spec):
    for question in spec.questions():
        if question.type == "documents":
            assert question.documents
            continue
        assert question.profile_field
        assert "." in question.profile_field  # a namespaced profile path


# --- the test that protects the thesis --------------------------------------


def test_a_declaration_does_not_settle_a_certificate_gated_clause(
    spec, welfare_schemes_dir
):
    """Saying "I am on the BPL list" does NOT make it so.

    IGNWPS requires BPL status, evidenced by a BPL ration card. A citizen who declares
    it but holds no card must stay BLOCKED_ON_DOCUMENT — never ELIGIBLE. If this ever
    goes green as ELIGIBLE, the engine has started taking someone's word for a
    government record, and everything the project claims about proof is gone.
    """
    schemes = load_corpus(welfare_schemes_dir)
    profile = build_intake_profile(
        spec,
        {**SUNITA_ANSWERS, "bpl": True},
        schemes=schemes,
        documents_held=SUNITA_DOCUMENTS,  # note: no bpl_ration_card
    )

    # The declaration IS recorded — we do not discard what she told us.
    assert profile.fields["household.bpl"].value is True
    assert profile.fields["household.bpl"].document_id == "self_declaration"

    ignwps = next(
        v for v in evaluate_corpus(schemes, profile) if v.scheme_id == "ignwps"
    )
    assert ignwps.status is Status.BLOCKED_ON_DOCUMENT
    assert ignwps.status is not Status.ELIGIBLE
    assert "bpl_ration_card" in ignwps.unlocking_docs

    bpl_clause = next(p for p in ignwps.predicates if p.clause_id == "IGNWPS-C3")
    assert bpl_clause.evaluation is Evaluation.UNKNOWN
    assert bpl_clause.evidence is None


def test_holding_the_card_does_settle_it(spec, welfare_schemes_dir):
    """The other half: with the card, the same declaration resolves."""
    schemes = load_corpus(welfare_schemes_dir)
    profile = build_intake_profile(
        spec,
        {**SUNITA_ANSWERS, "bpl": True},
        schemes=schemes,
        documents_held=[*SUNITA_DOCUMENTS, "bpl_ration_card"],
    )
    assert profile.fields["household.bpl"].document_id == "bpl_ration_card"

    ignwps = next(
        v for v in evaluate_corpus(schemes, profile) if v.scheme_id == "ignwps"
    )
    assert ignwps.status is Status.ELIGIBLE


def test_a_declaration_settles_what_the_corpus_says_it_settles(
    spec, welfare_schemes_dir
):
    """PM-KISAN's exclusions are collected on the applicant's own account."""
    schemes = load_corpus(welfare_schemes_dir)
    profile = build_intake_profile(
        spec, SUNITA_ANSWERS, schemes=schemes, documents_held=SUNITA_DOCUMENTS
    )
    pm_kisan = next(
        v for v in evaluate_corpus(schemes, profile) if v.scheme_id == "pm-kisan"
    )
    exclusions = [p for p in pm_kisan.predicates if p.clause_id.startswith("PMKISAN-X")]
    assert len(exclusions) == 6
    for predicate in exclusions:
        assert predicate.evaluation is Evaluation.TRUE
        assert predicate.evidence.document_id == "self_declaration"


# --- intake reproduces the golden verdicts ----------------------------------


def test_intake_reproduces_sunitas_golden_verdicts(
    spec, welfare_schemes_dir, sunita_profile, today
):
    """Answers equivalent to her fixture give the same statuses and predicates.

    This is what makes intake a real front door rather than a second engine: the same
    person described two ways produces the same verdicts, clause for clause.
    """
    schemes = load_corpus(welfare_schemes_dir)
    declared = build_intake_profile(
        spec, SUNITA_ANSWERS, schemes=schemes, documents_held=SUNITA_DOCUMENTS
    )

    from_intake = {v.scheme_id: v for v in evaluate_corpus(schemes, declared)}
    from_fixture = {v.scheme_id: v for v in evaluate_corpus(schemes, sunita_profile)}

    assert {k: v.status for k, v in from_intake.items()} == {
        k: v.status for k, v in from_fixture.items()
    }
    for scheme_id, verdict in from_intake.items():
        golden = from_fixture[scheme_id]
        assert [(p.clause_id, p.evaluation) for p in verdict.predicates] == [
            (p.clause_id, p.evaluation) for p in golden.predicates
        ], scheme_id
        assert verdict.unlocking_docs == golden.unlocking_docs, scheme_id


def test_intake_fields_are_marked_declared(spec, welfare_schemes_dir):
    """Never passed off as something we read."""
    schemes = load_corpus(welfare_schemes_dir)
    profile = build_intake_profile(
        spec, SUNITA_ANSWERS, schemes=schemes, documents_held=SUNITA_DOCUMENTS
    )
    assert profile.fields
    assert all(f.origin is FieldOrigin.DECLARED for f in profile.fields.values())


def test_an_unanswered_question_stays_unknown(spec, welfare_schemes_dir):
    schemes = load_corpus(welfare_schemes_dir)
    profile = build_intake_profile(
        spec, {"age": None, "marital_status": ""}, schemes=schemes
    )
    assert profile.fields == {}


# --- over the wire ----------------------------------------------------------


def test_the_intake_form_is_served_from_the_corpus(client):
    body = client.get("/api/intake").json()
    assert body["version"] == 1
    assert [s["section_id"] for s in body["sections"]][0] == "about-you"

    documents = next(
        q
        for s in body["sections"]
        for q in s["questions"]
        if q["type"] == "documents"
    )
    # Document names come from the engine's label layer, never derived in the UI.
    assert {"value": "bpl_ration_card", "label": "BPL ration card"} in documents[
        "documents"
    ]


def test_intake_over_http_returns_the_same_cards(client):
    body = client.post(
        "/api/intake",
        json={
            "vertical": "welfare",
            "answers": SUNITA_ANSWERS,
            "documents_held": SUNITA_DOCUMENTS,
        },
    ).json()

    assert body["declared"] is True
    assert "not seen your documents" in body["declared_banner"]
    assert {c["scheme_id"]: c["status"] for c in body["cards"]} == {
        "pm-kisan": "ELIGIBLE",
        "ignwps": "BLOCKED_ON_DOCUMENT",
        "sgnay": "BLOCKED_ON_DOCUMENT",
        "pmjay": "UNVERIFIABLE",
        "avvc": "NOT_ELIGIBLE",
    }
    assert all(f["origin"] == "DECLARED" for f in body["fields"])


def test_intake_output_can_never_hedge(client):
    """The blocklist, asserted on the newest entry point.

    "You may qualify" is exactly the phrasing a self-declared profile would tempt a
    lesser system into. It cannot appear here.
    """
    for vertical, answers in (
        ("welfare", SUNITA_ANSWERS),
        (
            "entrepreneur",
            {"gender": "FEMALE", "social_category": "SC", "venture_type": "GREENFIELD"},
        ),
    ):
        body = client.post(
            "/api/intake",
            json={"vertical": vertical, "answers": answers, "documents_held": []},
        ).json()
        served = " ".join(
            line
            for card in body["cards"]
            for line in [*card["lines"], *card["approval_lines"], *card["banners"]]
        ).lower()
        for phrase in BANNED_PHRASES:
            assert phrase not in served, f"{vertical}: {phrase!r}"
        assert "{" not in served


def test_intake_rejects_an_unknown_vertical(client):
    response = client.post(
        "/api/intake", json={"vertical": "nowhere", "answers": {}}
    )
    assert response.status_code == 404


def test_an_empty_intake_produces_refusals_not_eligibility(client):
    """Someone who answers nothing is entitled to nothing we can prove."""
    body = client.post(
        "/api/intake", json={"vertical": "welfare", "answers": {}}
    ).json()
    assert all(c["status"] != "ELIGIBLE" for c in body["cards"])
