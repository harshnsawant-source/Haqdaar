"""The deterministic evaluator. Code decides eligibility — no model, no vector search.

This module is the only writer of `Predicate.evaluation` (design doc s1, s4). It reads
typed bounds from the corpus and typed facts from the profile and compares them. It
imports nothing from haqdaar.llm and nothing that touches a network; a test asserts it.

DECISION TO MAKE, recorded before it can be forgotten
-----------------------------------------------------
Discretionary APPROVAL is a separate question from ELIGIBILITY.

On day 1, NSFDC collapses to UNVERIFIABLE because its discretionary sanction clause sits
inside an ALL group. That is correct for the mechanism test and only for the mechanism
test. The REAL corpus must not bury discretionary clauses inside eligibility ALL groups:
if it does, genuinely eligible entrepreneurs render UNVERIFIABLE and the eligibility we
could have proven is hidden behind a caveat about the bank.

Eligibility must stay determinable. Surface discretionary approval as a separate
caveat/refusal alongside a resolved eligibility verdict, not as a poison pill inside it.
The likely shape is a group-level kind (ELIGIBILITY vs APPROVAL) evaluated separately,
but that is a real design decision and it is not being made on day 1. See corpus/README.
"""

from __future__ import annotations

from haqdaar.corpus.schema import (
    UNSETTLEABLE_RULE_TYPES,
    CategoryBound,
    Clause,
    ClauseGroup,
    IncomeBound,
    NumericBound,
    RuleType,
    Scheme,
)
from haqdaar.eligibility.verdict import (
    Evaluation,
    Evidence,
    GroupResult,
    Predicate,
    Verdict,
    collect_unlocking_docs,
    derive_status,
    kleene,
)
from haqdaar.profile.schema import CitizenProfile, ProfileField

_INVERSE = {
    Evaluation.TRUE: Evaluation.FALSE,
    Evaluation.FALSE: Evaluation.TRUE,
    Evaluation.UNKNOWN: Evaluation.UNKNOWN,
}


def _as_number(value: object) -> float | None:
    # bool is a subclass of int; a boolean is never a quantity here.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _as_category(value: object) -> str:
    """Canonical form for category comparison.

    Compared case-insensitively, with booleans canonicalised to true/false. An
    extracted "sc" and a corpus "SC" are the same category; emitting a confident
    FALSE over a capital letter would be exactly the kind of wrong answer this
    engine exists to not give.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip().casefold()


def _match(clause: Clause, field: ProfileField) -> Evaluation:
    """Does the extracted value satisfy the clause's typed bound?

    A type mismatch resolves UNKNOWN rather than FALSE. The floor is biased to refuse:
    a wrongly-confident no is as damaging as a wrongly-confident yes.
    """
    bound = clause.bound
    if isinstance(bound, CategoryBound):
        allowed = {_as_category(v) for v in bound.values}
        return (
            Evaluation.TRUE
            if _as_category(field.value) in allowed
            else Evaluation.FALSE
        )
    if isinstance(bound, IncomeBound):
        number = _as_number(field.value)
        if number is None:
            return Evaluation.UNKNOWN
        return Evaluation.TRUE if number <= bound.max_value else Evaluation.FALSE
    if isinstance(bound, NumericBound):
        number = _as_number(field.value)
        if number is None:
            return Evaluation.UNKNOWN
        if bound.min is not None and number < bound.min:
            return Evaluation.FALSE
        if bound.max is not None and number > bound.max:
            return Evaluation.FALSE
        return Evaluation.TRUE
    return Evaluation.UNKNOWN


def evaluate_clause(
    clause: Clause, profile: CitizenProfile
) -> tuple[Evaluation, Evidence | None]:
    """Evaluate one clause. TRUE/FALSE only ever come back with evidence attached."""
    if clause.rule_type in UNSETTLEABLE_RULE_TYPES:
        # Never reads the profile. Permanently UNKNOWN by construction — this is what
        # makes the refusal structural rather than a judgement call.
        return Evaluation.UNKNOWN, None

    field = profile.get(clause.profile_field or "")
    if field is None:
        return Evaluation.UNKNOWN, None

    result = _match(clause, field)
    if clause.rule_type is RuleType.EXCLUSION:
        result = _INVERSE[result]
    if result is Evaluation.UNKNOWN:
        return result, None

    return result, Evidence(
        document_id=field.document_id,
        field=clause.profile_field or "",
        extracted_value=field.value,
    )


def build_predicate(
    scheme: Scheme, group: ClauseGroup, clause: Clause, profile: CitizenProfile
) -> Predicate:
    """One evaluated clause, carrying its scheme-level provenance."""
    evaluation, evidence = evaluate_clause(clause, profile)
    return Predicate(
        clause_id=clause.clause_id,
        group_id=group.group_id,
        clause_text=clause.clause_text,
        source_url=scheme.source_url,
        retrieved_on=scheme.retrieved_on,
        evaluation=evaluation,
        evidence=evidence,
        verifiable_from=list(clause.verifiable_from),
        decided_by=clause.decided_by,
    )


def evaluate_scheme(scheme: Scheme, profile: CitizenProfile) -> Verdict:
    """Evaluate every clause of one scheme against one profile."""
    predicates: list[Predicate] = []
    group_results: list[GroupResult] = []

    for group in scheme.clause_groups:
        group_predicates = [
            build_predicate(scheme, group, clause, profile) for clause in group.clauses
        ]
        predicates.extend(group_predicates)
        group_results.append(
            GroupResult(
                group_id=group.group_id,
                satisfy=group.satisfy,
                evaluation=kleene(
                    group.satisfy, [p.evaluation for p in group_predicates]
                ),
            )
        )

    return Verdict(
        scheme_id=scheme.scheme_id,
        status=derive_status(group_results, predicates),
        verification_status=scheme.verification_status,
        predicates=predicates,
        group_results=group_results,
        unlocking_docs=collect_unlocking_docs(group_results, predicates),
        staleness_flag=False,  # T5 lands on day 3
    )


def evaluate_corpus(schemes: list[Scheme], profile: CitizenProfile) -> list[Verdict]:
    """Evaluate a whole corpus. Scheme interactions resolve on day 2 (design doc s8)."""
    return [evaluate_scheme(scheme, profile) for scheme in schemes]
