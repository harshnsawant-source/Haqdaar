"""Guard triggers: pure functions over the verdict object.

Guard doc s3. Every trigger takes a finished `Verdict` and returns findings. None of
them touch a model, a network, or a profile — they read the verdict and nothing else,
which is what makes them cheap to unit test and impossible to talk out of a refusal.

They do not reimplement `derive_status`. That table has exactly one definition, in
eligibility/verdict.py; the triggers explain *why* a status came out the way it did and
`validate` asserts the two agree. Two copies of the roll-up drifting apart is the most
plausible way this project ships a wrong verdict.

T1 and T2 land on day 2. T3 (retrieval floor), T4 (slot binding) and T5 (staleness)
land on day 3 and get their own modules.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from haqdaar.corpus.schema import GroupKind
from haqdaar.eligibility.verdict import (
    ApprovalStatus,
    Evaluation,
    Predicate,
    Status,
    Verdict,
)


class TriggerId(str, Enum):
    T1_UNSUPPORTED_PREDICATE = "T1"
    T2_MISSING_BUT_OBTAINABLE = "T2"


class Scope(str, Enum):
    """Which question the finding is about. The whole point of the day-2 split."""

    ELIGIBILITY = "ELIGIBILITY"
    APPROVAL = "APPROVAL"


class Finding(BaseModel):
    """Structured, not prose.

    Findings carry ids and values, never citizen-facing sentences. Rendering is
    deterministic slot-fill over human-translated templates (design doc s5 guarantee
    5); a sentence written here would be a hallucination surface.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    trigger: TriggerId
    scope: Scope
    scheme_id: str
    clause_ids: list[str]
    #: T2 only: documents that would settle these clauses.
    documents: list[str] = Field(default_factory=list)
    #: T1 only: who decides, when the clause is discretionary rather than a dataset.
    deciders: list[str] = Field(default_factory=list)


def _unresolved(verdict: Verdict, kind: GroupKind) -> list[Predicate]:
    """UNKNOWN predicates that actually block, in groups of the given kind.

    A satisfied ANY group is settled: its other UNKNOWN members are unneeded, not
    missing, and must not produce a finding. Same rule as `derive_status`.
    """
    unresolved_groups = {
        g.group_id
        for g in verdict.group_results
        if g.kind is kind and g.evaluation is Evaluation.UNKNOWN
    }
    return [
        p
        for p in verdict.predicates
        if p.evaluation is Evaluation.UNKNOWN and p.group_id in unresolved_groups
    ]


def t1_unsupported_predicate(verdict: Verdict) -> list[Finding]:
    """Nothing the citizen can ever produce would settle this clause.

    Two shapes, one mechanism (`verifiable_from: []`):

    * ELIGIBILITY scope — an external dataset the citizen cannot look up. Welfare
      reveal instance: PM-JAY D3, keyed to SECC 2011. Status becomes UNVERIFIABLE.
    * APPROVAL scope — a discretionary decision belonging to someone else. Primary
      demo instance: NSFDC sanction, decided by the lending institution's appraisal.
      Eligibility is unaffected; only the approval question refuses.
    """
    findings: list[Finding] = []
    for kind, scope in (
        (GroupKind.ELIGIBILITY, Scope.ELIGIBILITY),
        (GroupKind.APPROVAL, Scope.APPROVAL),
    ):
        blocked = [p for p in _unresolved(verdict, kind) if not p.is_settleable]
        if not blocked:
            continue
        deciders: list[str] = []
        for predicate in blocked:
            if predicate.decided_by and predicate.decided_by not in deciders:
                deciders.append(predicate.decided_by)
        findings.append(
            Finding(
                trigger=TriggerId.T1_UNSUPPORTED_PREDICATE,
                scope=scope,
                scheme_id=verdict.scheme_id,
                clause_ids=[p.clause_id for p in blocked],
                deciders=deciders,
            )
        )
    return findings


def t2_missing_but_obtainable(verdict: Verdict) -> list[Finding]:
    """The citizen could go and get the document that settles this.

    Blocked, not refused — a different colour on screen and a different sentence. The
    aggregator turns a set of these into "one document unlocks N more."
    """
    findings: list[Finding] = []
    for kind, scope in (
        (GroupKind.ELIGIBILITY, Scope.ELIGIBILITY),
        (GroupKind.APPROVAL, Scope.APPROVAL),
    ):
        blocked = [p for p in _unresolved(verdict, kind) if p.is_settleable]
        if not blocked:
            continue
        documents: list[str] = []
        for predicate in blocked:
            for document in predicate.verifiable_from:
                if document not in documents:
                    documents.append(document)
        findings.append(
            Finding(
                trigger=TriggerId.T2_MISSING_BUT_OBTAINABLE,
                scope=scope,
                scheme_id=verdict.scheme_id,
                clause_ids=[p.clause_id for p in blocked],
                documents=documents,
            )
        )
    return findings


def check(verdict: Verdict) -> list[Finding]:
    """Every day-2 trigger, in trigger order."""
    return t1_unsupported_predicate(verdict) + t2_missing_but_obtainable(verdict)


class GuardViolation(Exception):
    """A verdict whose status contradicts its own predicates. Never render this."""


def validate(verdict: Verdict) -> list[Finding]:
    """Confirm the verdict's status agrees with what the triggers found.

    This is the gate's core assertion. It does not recompute the status; it checks
    consistency, so a future refactor that breaks the roll-up fails loudly here rather
    than quietly showing a citizen the wrong answer.
    """
    findings = check(verdict)
    eligibility = [f for f in findings if f.scope is Scope.ELIGIBILITY]
    triggers = {f.trigger for f in eligibility}

    if TriggerId.T1_UNSUPPORTED_PREDICATE in triggers:
        expected = Status.UNVERIFIABLE
    elif TriggerId.T2_MISSING_BUT_OBTAINABLE in triggers:
        expected = Status.BLOCKED_ON_DOCUMENT
    else:
        expected = None  # ELIGIBLE or NOT_ELIGIBLE; no unresolved eligibility clause

    if expected is not None and verdict.status is not expected:
        raise GuardViolation(
            f"{verdict.scheme_id}: status {verdict.status.value} contradicts "
            f"{sorted(t.value for t in triggers)} — expected {expected.value}"
        )
    if expected is None and verdict.status in (
        Status.UNVERIFIABLE,
        Status.BLOCKED_ON_DOCUMENT,
    ):
        raise GuardViolation(
            f"{verdict.scheme_id}: status {verdict.status.value} with no unresolved "
            "eligibility predicate to justify it"
        )

    approval_scoped = {f.trigger for f in findings if f.scope is Scope.APPROVAL}
    if approval_scoped and verdict.approval is None:
        raise GuardViolation(
            f"{verdict.scheme_id}: approval findings but no approval note"
        )
    if (
        TriggerId.T1_UNSUPPORTED_PREDICATE in approval_scoped
        and verdict.approval is not None
        and verdict.approval.status is not ApprovalStatus.UNVERIFIABLE
    ):
        raise GuardViolation(
            f"{verdict.scheme_id}: approval {verdict.approval.status.value} despite an "
            "unsettleable approval clause"
        )
    return findings
