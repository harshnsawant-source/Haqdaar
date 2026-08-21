"""Golden verdict tests — the two that gate day 1.

These assert whole verdicts, not just statuses. A red golden test means no deploy
(design doc s7). Clause text is PROVISIONAL today, so these will legitimately fail the
day the content lane lands real wording — read every diff before updating them.
"""

from pathlib import Path

import pytest

from haqdaar.corpus.loader import load_corpus, load_scheme
from haqdaar.eligibility.aggregate import best_unlock
from haqdaar.eligibility.evaluate import evaluate_corpus, evaluate_scheme
from haqdaar.eligibility.verdict import ApprovalStatus, Evaluation, Status
from haqdaar.guard.triggers import Scope, TriggerId, validate


@pytest.fixture
def stand_up_india(schemes_dir: Path):
    return load_scheme(schemes_dir / "stand-up-india.yaml")


@pytest.fixture
def nsfdc(schemes_dir: Path):
    return load_scheme(schemes_dir / "nsfdc-term-loan.yaml")


def test_standup_india_eligible(stand_up_india, entrepreneur_profile):
    """The proof chain: every predicate TRUE, every TRUE backed by a document."""
    verdict = evaluate_scheme(stand_up_india, entrepreneur_profile)

    assert verdict.scheme_id == "stand-up-india"
    assert verdict.status is Status.ELIGIBLE
    assert verdict.unlocking_docs == []

    by_id = {p.clause_id: p for p in verdict.predicates}
    assert set(by_id) == {"SUI-C1", "SUI-C2", "SUI-C3", "SUI-C4"}

    # Every predicate resolves TRUE for this persona.
    assert all(p.evaluation is Evaluation.TRUE for p in verdict.predicates)

    # And every resolved predicate points at a real value in a real document. This is
    # the invariant the whole design rests on.
    for predicate in verdict.predicates:
        assert predicate.evidence is not None
        assert predicate.evidence.document_id
        assert predicate.source_url == "https://www.standupmitra.in/"

    assert by_id["SUI-C1"].evidence.document_id == "caste_certificate"
    assert by_id["SUI-C1"].evidence.extracted_value == "SC"
    assert by_id["SUI-C4"].evidence.extracted_value == 1500000

    # The ANY group is satisfied; the ALL group is satisfied.
    groups = {g.group_id: g.evaluation for g in verdict.group_results}
    assert groups == {
        "applicant-category": Evaluation.TRUE,
        "enterprise-conditions": Evaluation.TRUE,
    }


def test_nsfdc_eligible_with_a_separate_approval_refusal(nsfdc, entrepreneur_profile):
    """The primary demo beat, and the day-2 correction to it.

    On day 1 this scheme collapsed to UNVERIFIABLE, because the appraisal clause sat
    inside the eligibility group. That hid the entitlement we can actually prove. Now
    eligibility resolves on its own and the refusal is scoped to approval:

        "You are entitled to apply, and here is the clause that says so. Whether the
         bank sanctions it is the bank's decision, and I will not promise it."
    """
    verdict = evaluate_scheme(nsfdc, entrepreneur_profile)

    assert verdict.scheme_id == "nsfdc-term-loan"
    assert verdict.status is Status.ELIGIBLE  # the proof she keeps
    assert verdict.unlocking_docs == []

    by_id = {p.clause_id: p for p in verdict.predicates}
    assert set(by_id) == {"NSF-C1", "NSF-C2"}

    # The caste clause resolves, with evidence.
    assert by_id["NSF-C1"].evaluation is Evaluation.TRUE
    assert by_id["NSF-C1"].evidence.document_id == "caste_certificate"

    # The discretionary clause is permanently unsettleable: no document, ever.
    appraisal = by_id["NSF-C2"]
    assert appraisal.evaluation is Evaluation.UNKNOWN
    assert appraisal.evidence is None
    assert appraisal.verifiable_from == []
    assert appraisal.is_settleable is False
    assert appraisal.decided_by == "the lending institution's credit appraisal"

    # The refusal, reported beside the eligibility rather than on top of it.
    assert verdict.approval is not None
    assert verdict.approval.status is ApprovalStatus.UNVERIFIABLE
    assert verdict.approval.deciders == ["the lending institution's credit appraisal"]
    assert verdict.approval.clause_ids == ["NSF-C2"]
    assert verdict.approval.unlocking_docs == []  # nothing to fetch; it is not hers

    # T1 fires on approval only. Eligibility is untouched.
    findings = validate(verdict)
    assert [(f.trigger, f.scope) for f in findings] == [
        (TriggerId.T1_UNSUPPORTED_PREDICATE, Scope.APPROVAL)
    ]

    # The important negative: nothing resolved without evidence behind it.
    for predicate in verdict.predicates:
        if predicate.evaluation is not Evaluation.UNKNOWN:
            assert predicate.evidence is not None


def test_one_document_unlocks_both_schemes(schemes_dir, entrepreneur_02_profile):
    """The "one document away" beat, computed off the real provisional corpus.

    entrepreneur-02 has a project report and Aadhaar but no caste certificate. That
    single paper is the sole blocker on both schemes, which is what makes the headline
    true rather than merely plausible.
    """
    schemes = load_corpus(schemes_dir)
    verdicts = evaluate_corpus(schemes, entrepreneur_02_profile)

    assert {v.scheme_id: v.status for v in verdicts} == {
        "nsfdc-term-loan": Status.BLOCKED_ON_DOCUMENT,
        "stand-up-india": Status.BLOCKED_ON_DOCUMENT,
    }
    for v in verdicts:
        assert v.unlocking_docs == ["caste_certificate"]
        assert validate(v)

    option = best_unlock(verdicts)
    assert option is not None
    assert option.document_id == "caste_certificate"
    assert option.unlocks == ["nsfdc-term-loan", "stand-up-india"]
    assert option.unlock_count == 2
    assert option.contributes_to == []

    # Her eligibility is blocked on paperwork; the bank's discretion is still separate.
    nsfdc_verdict = next(v for v in verdicts if v.scheme_id == "nsfdc-term-loan")
    assert nsfdc_verdict.approval.status is ApprovalStatus.UNVERIFIABLE
