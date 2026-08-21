"""T1: nothing the citizen can ever produce would settle this clause."""

import pytest

from haqdaar.corpus.schema import GroupKind, Satisfy
from haqdaar.eligibility.verdict import (
    ApprovalNote,
    ApprovalStatus,
    Evaluation,
    Evidence,
    GroupResult,
    Predicate,
    Status,
    Verdict,
)
from _helpers import predicate, verdict
from haqdaar.guard.triggers import (
    GuardViolation,
    Scope,
    TriggerId,
    t1_unsupported_predicate,
    validate,
)


def test_fires_on_an_unsettleable_eligibility_clause():
    """The welfare-reveal shape: SECC 2011, which no citizen can look up."""
    v = verdict(
        [predicate("SECC", "g", Evaluation.UNKNOWN)],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.UNVERIFIABLE,
    )
    findings = t1_unsupported_predicate(v)
    assert len(findings) == 1
    assert findings[0].trigger is TriggerId.T1_UNSUPPORTED_PREDICATE
    assert findings[0].scope is Scope.ELIGIBILITY
    assert findings[0].clause_ids == ["SECC"]


def test_approval_scope_leaves_eligibility_alone():
    """The primary demo beat. She is ELIGIBLE with proof; only approval refuses."""
    v = verdict(
        [
            predicate("NSF-C1", "elig", Evaluation.TRUE, verifiable_from=["caste"]),
            predicate("NSF-C2", "sanction", Evaluation.UNKNOWN, decided_by="the bank"),
        ],
        [
            GroupResult(
                group_id="elig", satisfy=Satisfy.ALL, evaluation=Evaluation.TRUE
            ),
            GroupResult(
                group_id="sanction",
                satisfy=Satisfy.ALL,
                evaluation=Evaluation.UNKNOWN,
                kind=GroupKind.APPROVAL,
            ),
        ],
        Status.ELIGIBLE,
        approval=ApprovalNote(
            status=ApprovalStatus.UNVERIFIABLE, deciders=["the bank"]
        ),
    )
    findings = t1_unsupported_predicate(v)
    assert [f.scope for f in findings] == [Scope.APPROVAL]
    assert findings[0].deciders == ["the bank"]
    # The whole point: eligibility is untouched and still says ELIGIBLE.
    assert v.status is Status.ELIGIBLE
    assert validate(v) == findings


def test_does_not_fire_on_a_settleable_clause():
    v = verdict(
        [predicate("BPL", "g", Evaluation.UNKNOWN, verifiable_from=["ration_card"])],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.BLOCKED_ON_DOCUMENT,
    )
    assert t1_unsupported_predicate(v) == []


def test_does_not_fire_inside_a_satisfied_any_group():
    """An unneeded UNKNOWN is not a refusal reason."""
    v = verdict(
        [
            predicate("WOMAN", "cat", Evaluation.TRUE, verifiable_from=["aadhaar"]),
            predicate("SECC", "cat", Evaluation.UNKNOWN),
        ],
        [GroupResult(group_id="cat", satisfy=Satisfy.ANY, evaluation=Evaluation.TRUE)],
        Status.ELIGIBLE,
    )
    assert t1_unsupported_predicate(v) == []


def test_validate_rejects_a_status_that_contradicts_the_trigger():
    """A verdict claiming ELIGIBLE over an unsettleable clause must never render."""
    v = verdict(
        [predicate("SECC", "g", Evaluation.UNKNOWN)],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.ELIGIBLE,
    )
    with pytest.raises(GuardViolation, match="contradicts"):
        validate(v)


def test_validate_rejects_approval_findings_without_an_approval_note():
    v = verdict(
        [predicate("NSF-C2", "sanction", Evaluation.UNKNOWN, decided_by="the bank")],
        [
            GroupResult(
                group_id="sanction",
                satisfy=Satisfy.ALL,
                evaluation=Evaluation.UNKNOWN,
                kind=GroupKind.APPROVAL,
            )
        ],
        Status.ELIGIBLE,
        approval=None,
    )
    with pytest.raises(GuardViolation, match="no approval note"):
        validate(v)
