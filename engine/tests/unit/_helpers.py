"""Shared synthetic verdict builders for the trigger tests.

Not collected by pytest (the filename does not match test_*).
"""

from haqdaar.eligibility.verdict import (
    ApprovalNote,
    Evaluation,
    Evidence,
    GroupResult,
    Predicate,
    Status,
    Verdict,
)


def predicate(
    clause_id: str,
    group_id: str,
    evaluation: Evaluation,
    *,
    verifiable_from: list[str] | None = None,
    decided_by: str | None = None,
) -> Predicate:
    evidence = (
        None
        if evaluation is Evaluation.UNKNOWN
        else Evidence(document_id="doc", field="f", extracted_value="v")
    )
    return Predicate(
        clause_id=clause_id,
        group_id=group_id,
        clause_text="[VERIFY AT SOURCE] synthetic",
        source_url="https://example.invalid/",
        retrieved_on="2026-08-21",
        evaluation=evaluation,
        evidence=evidence,
        verifiable_from=verifiable_from or [],
        decided_by=decided_by,
    )


def verdict(
    predicates: list[Predicate],
    groups: list[GroupResult],
    status: Status,
    approval: ApprovalNote | None = None,
    *,
    scheme_id: str = "synthetic",
    unlocking_docs: list[str] | None = None,
) -> Verdict:
    return Verdict(
        scheme_id=scheme_id,
        status=status,
        verification_status="PROVISIONAL",
        predicates=predicates,
        group_results=groups,
        approval=approval,
        unlocking_docs=unlocking_docs or [],
    )
