"""T2: the citizen could go and get the document that settles this.

Blocked, not refused. Different colour, different sentence, different next step.
Conflating T2 with T1 destroys both beats (guard doc s3).
"""

import pytest

from haqdaar.corpus.schema import GroupKind, Satisfy
from haqdaar.eligibility.verdict import (
    ApprovalNote,
    ApprovalStatus,
    Evaluation,
    GroupResult,
    Status,
    Verdict,
)
from _helpers import predicate, verdict
from haqdaar.guard.triggers import (
    GuardViolation,
    Scope,
    TriggerId,
    check,
    t1_unsupported_predicate,
    t2_missing_but_obtainable,
    validate,
)


def test_fires_on_a_missing_but_obtainable_document():
    v = verdict(
        [predicate("BPL", "g", Evaluation.UNKNOWN, verifiable_from=["ration_card"])],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.BLOCKED_ON_DOCUMENT,
    )
    findings = t2_missing_but_obtainable(v)
    assert len(findings) == 1
    assert findings[0].trigger is TriggerId.T2_MISSING_BUT_OBTAINABLE
    assert findings[0].scope is Scope.ELIGIBILITY
    assert findings[0].documents == ["ration_card"]
    assert validate(v) == findings


def test_deduplicates_documents_across_clauses():
    v = verdict(
        [
            predicate("A", "g", Evaluation.UNKNOWN, verifiable_from=["caste", "aadhaar"]),
            predicate("B", "g", Evaluation.UNKNOWN, verifiable_from=["caste"]),
        ],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.BLOCKED_ON_DOCUMENT,
    )
    assert t2_missing_but_obtainable(v)[0].documents == ["caste", "aadhaar"]


def test_t1_and_t2_are_mutually_exclusive_per_clause():
    """A clause is either fetchable or it is not. Never both."""
    v = verdict(
        [
            predicate("SECC", "g", Evaluation.UNKNOWN),
            predicate("BPL", "g", Evaluation.UNKNOWN, verifiable_from=["ration_card"]),
        ],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.UNVERIFIABLE,
    )
    t1_clauses = {c for f in t1_unsupported_predicate(v) for c in f.clause_ids}
    t2_clauses = {c for f in t2_missing_but_obtainable(v) for c in f.clause_ids}
    assert t1_clauses == {"SECC"}
    assert t2_clauses == {"BPL"}
    assert t1_clauses.isdisjoint(t2_clauses)

    # Both fire, and UNVERIFIABLE wins: never send her for a paper that cannot help.
    assert {f.trigger for f in check(v)} == {
        TriggerId.T1_UNSUPPORTED_PREDICATE,
        TriggerId.T2_MISSING_BUT_OBTAINABLE,
    }
    assert validate(v)


def test_does_not_fire_inside_a_satisfied_any_group():
    v = verdict(
        [
            predicate("WOMAN", "cat", Evaluation.TRUE, verifiable_from=["aadhaar"]),
            predicate("CASTE", "cat", Evaluation.UNKNOWN, verifiable_from=["caste"]),
        ],
        [GroupResult(group_id="cat", satisfy=Satisfy.ANY, evaluation=Evaluation.TRUE)],
        Status.ELIGIBLE,
    )
    assert t2_missing_but_obtainable(v) == []


def test_approval_scope_blocked_does_not_touch_eligibility():
    v = verdict(
        [
            predicate("E1", "elig", Evaluation.TRUE, verifiable_from=["aadhaar"]),
            predicate("A1", "appr", Evaluation.UNKNOWN, verifiable_from=["appraisal"]),
        ],
        [
            GroupResult(
                group_id="elig", satisfy=Satisfy.ALL, evaluation=Evaluation.TRUE
            ),
            GroupResult(
                group_id="appr",
                satisfy=Satisfy.ALL,
                evaluation=Evaluation.UNKNOWN,
                kind=GroupKind.APPROVAL,
            ),
        ],
        Status.ELIGIBLE,
        approval=ApprovalNote(status=ApprovalStatus.BLOCKED_ON_DOCUMENT),
    )
    findings = t2_missing_but_obtainable(v)
    assert [f.scope for f in findings] == [Scope.APPROVAL]
    assert v.status is Status.ELIGIBLE
    assert validate(v) == findings


def test_validate_rejects_blocked_status_with_nothing_blocking_it():
    v = verdict(
        [predicate("E1", "g", Evaluation.TRUE, verifiable_from=["aadhaar"])],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.TRUE)],
        Status.BLOCKED_ON_DOCUMENT,
    )
    with pytest.raises(GuardViolation, match="no unresolved eligibility predicate"):
        validate(v)
