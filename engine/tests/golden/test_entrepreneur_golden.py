"""Golden verdict tests — the two that gate day 1.

These assert whole verdicts, not just statuses. A red golden test means no deploy
(design doc s7). Clause text is PROVISIONAL today, so these will legitimately fail the
day the content lane lands real wording — read every diff before updating them.
"""

from pathlib import Path

import pytest

from haqdaar.corpus.loader import load_scheme
from haqdaar.eligibility.evaluate import evaluate_scheme
from haqdaar.eligibility.verdict import Evaluation, Status


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


def test_nsfdc_unverifiable_on_discretionary(nsfdc, entrepreneur_profile):
    """The refusal, produced by the mechanism rather than by a prompt."""
    verdict = evaluate_scheme(nsfdc, entrepreneur_profile)

    assert verdict.scheme_id == "nsfdc-term-loan"
    assert verdict.status is Status.UNVERIFIABLE

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

    # Nothing to send her to fetch — that is what separates this from BLOCKED.
    assert verdict.unlocking_docs == []

    # The important negative: nothing resolved without evidence behind it.
    for predicate in verdict.predicates:
        if predicate.evaluation is not Evaluation.UNKNOWN:
            assert predicate.evidence is not None
