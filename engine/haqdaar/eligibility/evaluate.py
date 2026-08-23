"""The deterministic evaluator. Code decides eligibility — no model, no vector search.

This module is the only writer of `Predicate.evaluation` (design doc s1, s4). It reads
typed bounds from the corpus and typed facts from the profile and compares them. It
imports nothing from haqdaar.llm and nothing that touches a network; a test asserts it.

DECISION MADE (day 2): approval is not eligibility
--------------------------------------------------
Discretionary APPROVAL is a separate question from ELIGIBILITY, and the split is now
structural rather than a note.

`ClauseGroup.kind` is ELIGIBILITY or APPROVAL. `Verdict.status` rolls up ELIGIBILITY
groups only; APPROVAL groups roll up into `Verdict.approval` beside it. So a genuinely
eligible entrepreneur reads ELIGIBLE with her full proof chain, plus a separate refusal
on approval naming the bank as the decider — instead of collapsing to UNVERIFIABLE with
the entitlement we could have proven hidden behind a caveat.

The corpus schema enforces it: a discretionary clause inside an ELIGIBILITY group is
rejected at load time. The trap is unrepresentable, not merely documented.
"""

from __future__ import annotations

from haqdaar.corpus.schema import (
    UNSETTLEABLE_RULE_TYPES,
    CategoryBound,
    Clause,
    ClauseGroup,
    GroupKind,
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
    Status,
    Verdict,
    collect_unlocking_docs,
    derive_approval,
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

    # The evidence must come from a document this clause actually accepts.
    #
    # `verifiable_from` is the corpus's statement of what proves a clause
    # (01-DEMO-CORPUS.md s8). Without this check any document could settle any clause,
    # which was harmless while every fixture happened to cite an appropriate document —
    # and becomes the whole ballgame once a citizen can DECLARE facts about herself. A
    # declaration is proof of what she says; it is not proof of what a caste
    # certificate, a BPL card or a 7/12 extract says. Those clauses stay UNKNOWN and
    # land on BLOCKED_ON_DOCUMENT, which is the honest answer: here is what you are
    # entitled to on your own account, and here is the paper you need for the rest.
    if field.document_id not in clause.verifiable_from:
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
                kind=group.kind,
                evaluation=kleene(
                    group.satisfy, [p.evaluation for p in group_predicates]
                ),
            )
        )

    # Eligibility is decided by ELIGIBILITY groups alone. An approval condition never
    # suppresses an entitlement we can prove.
    eligibility_groups = [g for g in group_results if g.kind is GroupKind.ELIGIBILITY]
    eligibility_ids = {g.group_id for g in eligibility_groups}
    eligibility_predicates = [p for p in predicates if p.group_id in eligibility_ids]

    return Verdict(
        scheme_id=scheme.scheme_id,
        status=derive_status(eligibility_groups, eligibility_predicates),
        verification_status=scheme.verification_status,
        predicates=predicates,
        group_results=group_results,
        unlocking_docs=collect_unlocking_docs(
            eligibility_groups, eligibility_predicates
        ),
        staleness_flag=False,  # T5 lands on day 3
        approval=derive_approval(group_results, predicates),
    )


def evaluate_corpus(schemes: list[Scheme], profile: CitizenProfile) -> list[Verdict]:
    """Evaluate a whole corpus, then resolve how the schemes interact."""
    return resolve_interactions(
        [evaluate_scheme(scheme, profile) for scheme in schemes], schemes
    )


def resolve_interactions(
    verdicts: list[Verdict], schemes: list[Scheme]
) -> list[Verdict]:
    """Apply subsumed_by and stacks_with across a whole verdict set.

    Two separate jobs (design doc s5 guarantee 6):

    * `subsumed_by` — a scheme absorbed by another the citizen already qualifies for is
      marked not separately claimable. Instance in the welfare reveal vertical: IGNWPS
      is reached *through* SGNAY, so listing both as independent Rs 1,500 benefits
      would be wrong, and a judge who knows Maharashtra would catch it.
    * `stacks_with` — schemes that pay together share a `stack_group_id` so a later
      renderer can group them instead of adding their benefits twice.

    Benefit *amounts* are not summed here, because `Scheme.benefit` is prose today and
    no numeric amount has been sourced. Grouping is what the corpus can honestly
    support; totalling would mean inventing figures.
    """
    by_id = {s.scheme_id: s for s in schemes}
    eligible = {
        v.scheme_id
        for v in verdicts
        if v.status is Status.ELIGIBLE and v.scheme_id in by_id
    }

    stack_group = _stack_groups(schemes)
    resolved: list[Verdict] = []
    for verdict in verdicts:
        scheme = by_id.get(verdict.scheme_id)
        absorber = None
        if scheme is not None:
            absorber = next((s for s in scheme.subsumed_by if s in eligible), None)
        resolved.append(
            verdict.model_copy(
                update={
                    "claimable": absorber is None,
                    "subsumed_by_scheme": absorber,
                    "stack_group_id": stack_group.get(verdict.scheme_id),
                }
            )
        )
    return resolved


def _stack_groups(schemes: list[Scheme]) -> dict[str, str]:
    """Connected components over stacks_with, keyed by the lowest scheme_id.

    The relation is treated as symmetric: if A stacks with B then B stacks with A,
    whether or not the corpus author wrote it on both sides.
    """
    known = {s.scheme_id for s in schemes}
    adjacency: dict[str, set[str]] = {s.scheme_id: set() for s in schemes}
    for scheme in schemes:
        for other in scheme.stacks_with:
            if other in known:
                adjacency[scheme.scheme_id].add(other)
                adjacency[other].add(scheme.scheme_id)

    groups: dict[str, str] = {}
    for scheme_id in sorted(adjacency):
        if scheme_id in groups or not adjacency[scheme_id]:
            continue
        component: set[str] = set()
        pending = [scheme_id]
        while pending:
            current = pending.pop()
            if current in component:
                continue
            component.add(current)
            pending.extend(adjacency[current] - component)
        key = min(component)
        for member in component:
            groups[member] = key
    return groups
