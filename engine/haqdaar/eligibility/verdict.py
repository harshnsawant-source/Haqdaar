"""The verdict object and the single definition of the status roll-up.

Guard doc s2, design doc s4. Two things live here on purpose:

* The evidence invariant is enforced at construction. A Predicate cannot be built
  TRUE or FALSE without evidence pointing at a real extracted value. It is not a rule
  someone has to remember at 2am on 29 Aug; the type refuses.

* `derive_status` is the ONLY definition of the roll-up. Day 2's guard/triggers.py
  validates the verdict it produces — it does not reimplement this table. Two copies
  of this drifting apart is the most plausible way this project ships a wrong verdict.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from haqdaar.corpus.schema import Satisfy, VerificationStatus


class Evaluation(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class Status(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    UNVERIFIABLE = "UNVERIFIABLE"
    BLOCKED_ON_DOCUMENT = "BLOCKED_ON_DOCUMENT"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Evidence(_Frozen):
    document_id: str
    field: str
    extracted_value: bool | int | float | str


class Predicate(_Frozen):
    """One rule clause, evaluated against one profile.

    `evaluation` answers "is this clause satisfied for eligibility purposes". For an
    exclusion clause that is the inverse of the raw match: a citizen who *is* in the
    excluded set yields FALSE. The raw matched value stays in `evidence` either way,
    so the proof trail shows what was actually read from the document.
    """

    clause_id: str
    group_id: str
    clause_text: str
    source_url: str
    retrieved_on: date
    evaluation: Evaluation
    evidence: Evidence | None = None
    #: Empty means no citizen-obtainable document can ever settle this clause.
    verifiable_from: list[str] = Field(default_factory=list)
    decided_by: str | None = None

    @model_validator(mode="after")
    def _evidence_invariant(self) -> Predicate:
        if self.evaluation is not Evaluation.UNKNOWN and self.evidence is None:
            raise ValueError(
                f"{self.clause_id}: {self.evaluation.value} requires evidence — a "
                "predicate may only resolve from a real extracted value"
            )
        return self

    @property
    def is_settleable(self) -> bool:
        """False when no document the citizen could fetch would ever resolve this."""
        return bool(self.verifiable_from)


class GroupResult(_Frozen):
    group_id: str
    satisfy: Satisfy
    evaluation: Evaluation


class Verdict(_Frozen):
    scheme_id: str
    status: Status
    verification_status: VerificationStatus
    predicates: list[Predicate]
    group_results: list[GroupResult]
    #: Documents that would flip an UNKNOWN predicate, deduplicated, order preserved.
    unlocking_docs: list[str] = Field(default_factory=list)
    staleness_flag: bool = False


def kleene(satisfy: Satisfy, values: list[Evaluation]) -> Evaluation:
    """Three-valued group roll-up.

    UNKNOWN is a first-class value that propagates; it is not a null to be coerced.
    That propagation is the refusal.

    ALL: any FALSE -> FALSE, else any UNKNOWN -> UNKNOWN, else TRUE
    ANY: any TRUE  -> TRUE,  else any UNKNOWN -> UNKNOWN, else FALSE
    """
    if satisfy is Satisfy.ALL:
        if Evaluation.FALSE in values:
            return Evaluation.FALSE
        return Evaluation.UNKNOWN if Evaluation.UNKNOWN in values else Evaluation.TRUE
    if Evaluation.TRUE in values:
        return Evaluation.TRUE
    return Evaluation.UNKNOWN if Evaluation.UNKNOWN in values else Evaluation.FALSE


def derive_status(
    group_results: list[GroupResult], predicates: list[Predicate]
) -> Status:
    """Roll group results up to one scheme status.

    Precedence, and why:

    1. Any group FALSE -> NOT_ELIGIBLE. A proven no beats an unproven maybe, and it is
       information the citizen can act on ("the rule says 70, you qualify in 2036").
    2. Else any unresolved predicate that no document can settle -> UNVERIFIABLE. This
       outranks BLOCKED because sending someone to fetch a paper that cannot help is
       exactly the harm the Guard exists to prevent.
    3. Else any unresolved predicate -> BLOCKED_ON_DOCUMENT.
    4. Else ELIGIBLE.

    Steps 2 and 3 only consider predicates inside groups that are themselves UNKNOWN.
    An ANY group already satisfied by one TRUE member is settled; its other UNKNOWN
    members are not missing evidence, they are simply unneeded.
    """
    if any(g.evaluation is Evaluation.FALSE for g in group_results):
        return Status.NOT_ELIGIBLE

    unresolved_groups = {
        g.group_id for g in group_results if g.evaluation is Evaluation.UNKNOWN
    }
    blocking = [
        p
        for p in predicates
        if p.evaluation is Evaluation.UNKNOWN and p.group_id in unresolved_groups
    ]
    if any(not p.is_settleable for p in blocking):
        return Status.UNVERIFIABLE
    if blocking:
        return Status.BLOCKED_ON_DOCUMENT
    return Status.ELIGIBLE


def collect_unlocking_docs(
    group_results: list[GroupResult], predicates: list[Predicate]
) -> list[str]:
    """Documents that would flip an UNKNOWN predicate in an unresolved group."""
    unresolved_groups = {
        g.group_id for g in group_results if g.evaluation is Evaluation.UNKNOWN
    }
    docs: list[str] = []
    for predicate in predicates:
        if predicate.evaluation is not Evaluation.UNKNOWN:
            continue
        if predicate.group_id not in unresolved_groups:
            continue
        for doc in predicate.verifiable_from:
            if doc not in docs:
                docs.append(doc)
    return docs
