"""The third vertical, end to end. Same engine, a third folder.

Added 2026-08-26. Entrepreneur was the first corpus, welfare the second, and this is the
third, built without touching a single file under engine/haqdaar/. That is the platform
claim: a vertical is a corpus folder plus an intake section, not a code path.

The strongest assertion in this file is the last one. It walks every module in the engine
and fails if any of them contains the word "student", because the day one does, the claim
that verticals are data stops being true and nobody would otherwise notice.

Both schemes belong to the Ministry of Social Justice & Empowerment, which is also the
ministry that owns problem statement SIH26092.

    pre-matric-sc   ELIGIBLE      proof from her caste and income certificates
    top-class-sc    NOT_ELIGIBLE  it funds students entering a full time course; she
                                  told us she has not secured admission, and that is
                                  enough to rule her out without any document
"""

from pathlib import Path

import pytest

from haqdaar.corpus.loader import load_corpus
from haqdaar.corpus.schema import GroupKind, VerificationStatus
from haqdaar.eligibility.evaluate import evaluate_corpus
from haqdaar.eligibility.verdict import ApprovalStatus, Evaluation, Status
from haqdaar.guard.gate import gate_all
from haqdaar.guard.triggers import Scope, TriggerId
from haqdaar.render.render import render_card


@pytest.fixture(scope="session")
def student_schemes_dir(corpus_dir: Path) -> Path:
    return corpus_dir / "student" / "schemes"


@pytest.fixture(scope="session")
def student_profile(corpus_dir: Path):
    from haqdaar.profile.schema import CitizenProfile

    return CitizenProfile.model_validate_json(
        (corpus_dir / "student" / "personas" / "student-01.json").read_text(
            encoding="utf-8"
        )
    )


def _run(student_schemes_dir, student_profile, today):
    schemes = load_corpus(student_schemes_dir)
    verdicts = evaluate_corpus(schemes, student_profile)
    results = {r.verdict.scheme_id: r for r in gate_all(verdicts, schemes, today=today)}
    return schemes, verdicts, results


def test_the_whole_student_arc(student_schemes_dir, student_profile, today):
    _, verdicts, _ = _run(student_schemes_dir, student_profile, today)
    assert {v.scheme_id: v.status for v in verdicts} == {
        "pre-matric-sc": Status.ELIGIBLE,
        "top-class-sc": Status.NOT_ELIGIBLE,
        # Added 2026-08-30 with the NSFDC Educational Loan Scheme, which SIH26092
        # names alongside the two credit products.
        #
        # NOT_ELIGIBLE, and the route there is the point. She is SC and under the Rs
        # 5.00 lakh ceiling, so both money clauses hold; what rules her out is her own
        # declaration that she has not secured admission to a full-time course, which
        # is the same field that rules out Top Class. A declaration can rule a scheme
        # OUT and can never rule one IN, so she is told why instead of being sent to
        # fetch a college admission letter a class 10 pupil has no reason to have.
        #
        # This assertion read ELIGIBLE for a few hours on 2026-08-30, while the scheme
        # existed but nothing in it tested whether she was studying at all.
        "nsfdc-educational-loan": Status.NOT_ELIGIBLE,
    }


def test_the_positive_match_proves_itself_from_documents(
    student_schemes_dir, student_profile, today
):
    _, _, results = _run(student_schemes_dir, student_profile, today)
    verdict = results["pre-matric-sc"].verdict

    assert verdict.status is Status.ELIGIBLE
    assert verdict.unlocking_docs == []

    by_id = {p.clause_id: p for p in verdict.predicates}
    assert by_id["PREMAT-C1"].evidence.document_id == "caste_certificate"
    assert by_id["PREMAT-C2"].evidence.document_id == "income_certificate"
    assert by_id["PREMAT-C3"].evidence.document_id == "bonafide_certificate"

    # The exclusion resolves TRUE for eligibility purposes because she is NOT in the
    # excluded set. The raw declared value stays visible in the evidence either way.
    assert by_id["PREMAT-X1"].evaluation is Evaluation.TRUE
    assert by_id["PREMAT-X1"].evidence.extracted_value == "false"

    # Nothing resolved without a document behind it. The invariant the design rests on.
    for predicate in verdict.predicates:
        if predicate.evaluation is not Evaluation.UNKNOWN:
            assert predicate.evidence is not None, predicate.clause_id


def test_the_refusal_reads_as_a_sentence_and_names_the_reason(
    student_schemes_dir, student_profile, today
):
    """She is at school, so she is ruled out of a scholarship for college entrants.

    Two things are being asserted. First, that she is RULED OUT rather than sent to
    fetch a college admission letter she has no reason to own: that is the intake
    asymmetry working on the real corpus, since a declaration can rule a scheme out
    even where it could never rule one in.

    Second, that the sentence is English. A boolean clause used to render through the
    range-shaped template as "The rule says true. Your admission secured is false.",
    on the one card whose headline promises "here is exactly why".
    """
    schemes, _, results = _run(student_schemes_dir, student_profile, today)
    scheme = next(s for s in schemes if s.scheme_id == "top-class-sc")
    card = render_card(results["top-class-sc"], scheme, today=today)

    assert card.status is Status.NOT_ELIGIBLE
    assert card.lines[0] == "Not this one, and here is exactly why."
    assert card.lines[1] == (
        "This one requires having secured admission to a full time course. "
        "You told me no."
    )
    # The old shape must not come back.
    assert "is false" not in card.text()
    assert "says true" not in card.text()

    # Ruled out on her own word, and the word is cited.
    failing = next(
        p
        for p in results["top-class-sc"].verdict.predicates
        if p.evaluation is Evaluation.FALSE
    )
    assert failing.clause_id == "TOPCL-C3"
    assert failing.evidence.document_id == "self_declaration"


def test_eligibility_and_the_award_stay_separate(
    student_schemes_dir, student_profile, today
):
    """Top Class caps awards per institution and allocates them down a merit list.

    A third domain, a third structurally identical approval refusal: a bank's credit
    appraisal, a channelising agency's verification, and now a queue whose length the
    student cannot see. None of them is an eligibility question and none of them is
    allowed to suppress one.
    """
    schemes, _, _ = _run(student_schemes_dir, student_profile, today)
    scheme = next(s for s in schemes if s.scheme_id == "top-class-sc")

    approval_groups = scheme.groups_of(GroupKind.APPROVAL)
    assert [g.group_id for g in approval_groups] == ["slot-allocation"]

    clause = approval_groups[0].clauses[0]
    assert clause.decided_by == "the institution, against the slots allotted to it"
    # No document a student carries settles a merit list she cannot see.
    assert clause.verifiable_from == []


def test_the_slot_refusal_does_not_hide_a_provable_entitlement(
    student_schemes_dir, student_profile, today
):
    """The approval split, asserted on the corpus rather than on a synthetic scheme.

    Even where the award is uncertain, the eligibility verdict is computed and reported
    on its own terms. Here she fails eligibility on the year rule, so what matters is
    that the APPROVAL clause is what produced the T1 finding and NOT the eligibility.
    """
    _, _, results = _run(student_schemes_dir, student_profile, today)
    findings = results["top-class-sc"].findings

    scopes = {(f.trigger, f.scope) for f in findings}
    assert (TriggerId.T1_UNSUPPORTED_PREDICATE, Scope.APPROVAL) in scopes
    assert (TriggerId.T1_UNSUPPORTED_PREDICATE, Scope.ELIGIBILITY) not in scopes

    approval = results["top-class-sc"].verdict.approval
    assert approval is not None
    assert approval.status is ApprovalStatus.UNVERIFIABLE
    assert approval.unlocking_docs == []  # nothing to fetch; it is not hers to settle


def test_every_student_scheme_is_verified_against_official_sources(
    student_schemes_dir,
):
    """A new vertical does not get to skip the rule the other two follow."""
    schemes = load_corpus(student_schemes_dir)
    assert len(schemes) == 3
    for scheme in schemes:
        assert scheme.verification_status is VerificationStatus.VERIFIED
        assert scheme.source_url.startswith("https://")
        for clause in scheme.clauses():
            assert "[VERIFY AT SOURCE]" not in clause.clause_text, clause.clause_id
            assert clause.verify_note

    # All three are VERIFIED, so strict mode drops none of them.
    assert len(load_corpus(student_schemes_dir, strict=True)) == 3


def test_no_rendered_student_card_hedges(
    student_schemes_dir, student_profile, today
):
    from haqdaar.render.render import BANNED_PHRASES

    schemes, _, results = _run(student_schemes_dir, student_profile, today)
    for scheme in schemes:
        text = render_card(results[scheme.scheme_id], scheme, today=today).text().lower()
        for phrase in BANNED_PHRASES:
            assert phrase not in text, (scheme.scheme_id, phrase)


# --- the claim itself -------------------------------------------------------


def test_the_engine_does_not_know_what_a_student_is():
    """The platform claim, enforced rather than asserted in a README.

    Three verticals now share one engine. If a future change teaches engine code the
    word "student", verticals have stopped being data and this test is the only thing
    that would say so. `haqdaar/api/app.py` is exempt for one line: PERSONAS is the
    demo-fixture index, and naming a fixture is not the same as branching on a domain.
    """
    engine_root = Path(__file__).resolve().parents[2] / "haqdaar"
    offenders = []
    for path in sorted(engine_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            if "student" not in line.lower():
                continue
            if path.name == "app.py" and '"student-01"' in line:
                continue  # the fixture index, not a code path
            if path.name == "labels.py":
                # Presentation only: a display-name table with no control flow in it.
                # "bonafide student certificate" is what the document is called, and
                # naming a document is not branching on a domain.
                continue
            offenders.append(f"{path.relative_to(engine_root)}:{number}: {line.strip()}")

    assert not offenders, (
        "engine code mentions 'student'; a vertical must stay a corpus folder:\n"
        + "\n".join(offenders)
    )


def test_a_school_pupil_is_not_offered_a_professional_course_loan(
    student_schemes_dir, student_profile, today
):
    """The regression this file exists to hold.

    The NSFDC Educational Loan Scheme funds "regular full-time professional /
    technical" courses. When it was first added, its only eligibility clauses were the
    SC category and the Rs 5.00 lakh income ceiling, so a class 10 school pupil with no
    college admission resolved ELIGIBLE for a course loan of up to Rs 40 lakh. Nothing
    in the scheme asked whether she was studying at that level at all.

    The fix was to split the source sentence: the limb about HER, pursuing a full-time
    course, is eligibility and reads a declaration she has already made; the limb about
    the INSTITUTION, whether the course is recognised and government-approved, stays in
    approval where no document she holds could settle it.
    """
    _, verdicts, _ = _run(student_schemes_dir, student_profile, today)
    loan = next(v for v in verdicts if v.scheme_id == "nsfdc-educational-loan")

    assert loan.status is Status.NOT_ELIGIBLE
    # Ruled out on the admission declaration, not on money.
    by_id = {p.clause_id: p.evaluation for p in loan.predicates}
    assert by_id["ELS-C3"] is not Evaluation.TRUE, by_id["ELS-C3"]
    assert by_id["ELS-C1"] is Evaluation.TRUE
    assert by_id["ELS-C2"] is Evaluation.TRUE
