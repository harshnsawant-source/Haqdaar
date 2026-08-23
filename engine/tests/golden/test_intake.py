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
        schemes=schemes
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


def test_saying_you_hold_the_card_is_not_evidence_either(spec, welfare_schemes_dir):
    """Ticking "I have a BPL ration card" changes nothing.

    An earlier version filed her stated BPL status against the card she said she held,
    and the card then read "Proven from your BPL ration card" about a card nobody had
    seen. Saying you have a document is not evidence of what it says. Only reading it
    is, which is what the upload path does.
    """
    schemes = load_corpus(welfare_schemes_dir)
    profile = build_intake_profile(
        spec, {**SUNITA_ANSWERS, "bpl": True}, schemes=schemes
    )
    assert profile.fields["household.bpl"].document_id == "self_declaration"

    ignwps = next(
        v for v in evaluate_corpus(schemes, profile) if v.scheme_id == "ignwps"
    )
    assert ignwps.status is Status.BLOCKED_ON_DOCUMENT
    assert "bpl_ration_card" in ignwps.unlocking_docs


def test_a_declaration_settles_what_the_corpus_says_it_settles(
    spec, welfare_schemes_dir
):
    """PM-KISAN's exclusions are collected on the applicant's own account."""
    schemes = load_corpus(welfare_schemes_dir)
    profile = build_intake_profile(
        spec, SUNITA_ANSWERS, schemes=schemes
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


def test_intake_reproduces_the_document_independent_subset(
    spec, welfare_schemes_dir, sunita_profile
):
    """Intake matches her fixture exactly wherever a declaration is enough.

    It deliberately does NOT match everywhere. Her fixture carries values read from an
    Aadhaar, a death certificate and a 7/12 extract; intake carries her word. Where the
    corpus accepts her word the two agree clause for clause. Where it wants a
    certificate the fixture resolves and intake blocks — which is the whole point.

    An earlier version of this test asserted full equality. It could only pass because
    intake was crediting documents nobody had read.
    """
    schemes = load_corpus(welfare_schemes_dir)
    declared = build_intake_profile(spec, SUNITA_ANSWERS, schemes=schemes)

    from_intake = {v.scheme_id: v for v in evaluate_corpus(schemes, declared)}
    from_fixture = {v.scheme_id: v for v in evaluate_corpus(schemes, sunita_profile)}

    for scheme_id, verdict in from_intake.items():
        golden = {p.clause_id: p for p in from_fixture[scheme_id].predicates}
        for predicate in verdict.predicates:
            if predicate.evidence is None:
                continue  # blocked on a document she has not shown us
            # Where her word sufficed, it agrees with the read document exactly.
            assert predicate.evaluation is golden[predicate.clause_id].evaluation
            assert predicate.evidence.document_id == "self_declaration"

    # And the whole set resolves to answers, never to silence.
    assert {v.status for v in from_intake.values()} <= {
        Status.BLOCKED_ON_DOCUMENT,
        Status.UNVERIFIABLE,
        Status.NOT_ELIGIBLE,
    }


def test_intake_alone_never_produces_eligible_for_a_certificate_gated_scheme(
    spec, welfare_schemes_dir, schemes_dir
):
    """Both verticals behave identically. They did not before.

    Welfare was already strict; entrepreneur credited an unseen caste certificate and
    rendered NSFDC ELIGIBLE. Same engine, two behaviours — now one.
    """
    for directory, answers in (
        (welfare_schemes_dir, SUNITA_ANSWERS),
        (
            schemes_dir,
            {"gender": "FEMALE", "social_category": "SC", "venture_type": "GREENFIELD"},
        ),
    ):
        schemes = load_corpus(directory)
        profile = build_intake_profile(spec, answers, schemes=schemes)
        for verdict in evaluate_corpus(schemes, profile):
            assert verdict.status is not Status.ELIGIBLE, verdict.scheme_id


def test_intake_fields_are_marked_declared(spec, welfare_schemes_dir):
    """Never passed off as something we read."""
    schemes = load_corpus(welfare_schemes_dir)
    profile = build_intake_profile(
        spec, SUNITA_ANSWERS, schemes=schemes
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
    # Strict: her word settles what the corpus lets it settle and nothing else, so
    # every certificate-gated scheme asks for the paper instead of resolving.
    assert {c["scheme_id"]: c["status"] for c in body["cards"]} == {
        "pm-kisan": "BLOCKED_ON_DOCUMENT",
        "ignwps": "BLOCKED_ON_DOCUMENT",
        "sgnay": "BLOCKED_ON_DOCUMENT",
        "pmjay": "UNVERIFIABLE",
        "avvc": "BLOCKED_ON_DOCUMENT",
    }
    assert all(f["origin"] == "DECLARED" for f in body["fields"])
    assert all(f["document_id"] == "self_declaration" for f in body["fields"])

    # Documents she says she holds are echoed as a routing hint, never as evidence.
    assert [d["value"] for d in body["documents_held"]] == SUNITA_DOCUMENTS
    assert {d["value"] for d in body["ready_to_upload"]} == {
        "aadhaar",
        "husband_death_certificate",
        "land_record_7_12",
    }


def test_the_proven_from_line_can_never_name_an_unseen_document(client):
    """The specific assertion: "Proven from your X" must be earned.

    Intake carries her word, so the only document any intake card may cite is the
    self-declaration itself. If a certificate name ever appears after "Proven from", we
    are telling a citizen we read a paper we have never seen — which is the exact claim
    a judge would go after, and they would be right.
    """
    import re

    from haqdaar.render.labels import document_label

    proven = re.compile(r"Proven from your (.+)\.$")
    for vertical, answers in (
        ("welfare", {**SUNITA_ANSWERS, "bpl": True}),
        (
            "entrepreneur",
            {
                "gender": "FEMALE",
                "social_category": "SC",
                "venture_type": "GREENFIELD",
                "loan_amount": 1500000,
            },
        ),
    ):
        body = client.post(
            "/api/intake",
            json={
                "vertical": vertical,
                "answers": answers,
                # She claims every document. It must still change nothing.
                "documents_held": [
                    "aadhaar",
                    "caste_certificate",
                    "bpl_ration_card",
                    "land_record_7_12",
                    "husband_death_certificate",
                    "project_report",
                ],
            },
        ).json()

        cited = 0
        for card in body["cards"]:
            for line in card["lines"]:
                match = proven.match(line)
                if match is None:
                    continue
                assert match.group(1) == document_label("self_declaration"), (
                    f"{vertical}/{card['scheme_id']}: claims to have read "
                    f"{match.group(1)!r}, which nobody uploaded"
                )
            # And no citation cites anything else either.
            for citation in card["citations"]:
                if citation["document_id"]:
                    cited += 1
                    assert citation["document_id"] == "self_declaration"

        # Guard against this test passing because there was nothing to check.
        assert cited > 0, f"{vertical}: no evidenced citations, test proved nothing"


def test_a_rendered_intake_card_names_the_declaration_not_a_certificate(spec):
    """Positive control for the "Proven from" line.

    The HTTP test above scans real cards, but strict intake currently produces no
    ELIGIBLE card in either vertical — so its "Proven from" scan has nothing to match
    and proves nothing on its own. This forces the case: a synthetic scheme whose only
    clause a declaration genuinely settles, rendered, so the sentence actually appears.
    It must name the declaration and never a certificate.
    """
    from datetime import date

    from haqdaar.corpus.schema import (
        CategoryBound,
        Clause,
        ClauseGroup,
        RuleType,
        Satisfy,
        Scheme,
        VerificationStatus,
    )
    from haqdaar.eligibility.evaluate import evaluate_scheme
    from haqdaar.guard.gate import gate
    from haqdaar.render.render import render_card

    declarable = Scheme(
        scheme_id="synthetic-declarable",
        name="Synthetic Declarable Scheme",
        authority="test",
        benefit="test",
        source_url="https://example.invalid/",
        retrieved_on=date(2026, 8, 21),
        verification_status=VerificationStatus.PROVISIONAL,
        verify_note="synthetic",
        clause_groups=[
            ClauseGroup(
                group_id="g",
                satisfy=Satisfy.ALL,
                clauses=[
                    Clause(
                        clause_id="D1",
                        clause_text="[VERIFY AT SOURCE] The applicant declares no income tax.",
                        rule_type=RuleType.ENUMERATED_CATEGORY,
                        profile_field="applicant.paid_income_tax",
                        bound=CategoryBound(values=["false"]),
                        verifiable_from=["self_declaration"],
                        verification_status=VerificationStatus.PROVISIONAL,
                        verify_note="synthetic",
                    )
                ],
            )
        ],
    )

    profile = build_intake_profile(
        spec, {"paid_income_tax": False}, schemes=[declarable]
    )
    verdict = evaluate_scheme(declarable, profile)
    assert verdict.status is Status.ELIGIBLE  # so the line actually renders

    card = render_card(
        gate(verdict, declarable, today=date(2026, 8, 22)),
        declarable,
        today=date(2026, 8, 22),
    )
    proven_lines = [line for line in card.lines if line.startswith("Proven from")]
    assert proven_lines == ["Proven from your self-declaration."]


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
