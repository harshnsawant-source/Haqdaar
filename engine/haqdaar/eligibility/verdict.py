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

from haqdaar.corpus.schema import GroupKind, Satisfy, Scheme, VerificationStatus


class Evaluation(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class Status(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    UNVERIFIABLE = "UNVERIFIABLE"
    BLOCKED_ON_DOCUMENT = "BLOCKED_ON_DOCUMENT"


class ApprovalStatus(str, Enum):
    """The downstream discretionary question, answered separately from eligibility."""

    SETTLED = "SETTLED"
    NOT_MET = "NOT_MET"
    UNVERIFIABLE = "UNVERIFIABLE"
    BLOCKED_ON_DOCUMENT = "BLOCKED_ON_DOCUMENT"


class SchemeWindow(str, Enum):
    """Whether the scheme itself is open, independent of who is asking.

    This is deliberately NOT a `Status`. A citizen can be provably eligible under the
    published rules of a scheme that has closed; those are two different facts and
    collapsing them would repeat exactly the mistake the approval split exists to
    prevent. Eligibility answers "do the rules entitle you". This answers "is the
    door open".
    """

    OPEN = "OPEN"
    LAPSED = "LAPSED"
    NOT_YET_OPEN = "NOT_YET_OPEN"


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
    kind: GroupKind = GroupKind.ELIGIBILITY


class ApprovalNote(_Frozen):
    """A discretionary step, reported beside eligibility and never inside it.

    "You are entitled to apply, and here is the proof. Whether the bank sanctions it
    is the bank's decision and I will not pretend otherwise."
    """

    status: ApprovalStatus
    #: Who actually decides, from the clause's decided_by. Renders as a slot.
    deciders: list[str] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)
    clause_ids: list[str] = Field(default_factory=list)
    #: Documents that would settle an approval clause, if any ever could.
    unlocking_docs: list[str] = Field(default_factory=list)


class WindowNote(_Frozen):
    """The scheme's operating window, reported beside eligibility and never inside it.

    "The rules would entitle you, and here is the proof. The scheme's sanctioned
    period ended on this date, so I will not send you to apply for it."
    """

    state: SchemeWindow
    valid_from: date | None = None
    valid_until: date | None = None
    #: Verbatim source wording that states the window, so a closure is cited.
    validity_text: str | None = None


class Verdict(_Frozen):
    scheme_id: str
    #: Eligibility only. Approval never changes this value.
    status: Status
    verification_status: VerificationStatus
    predicates: list[Predicate]
    group_results: list[GroupResult]
    #: Documents that would flip an UNKNOWN predicate, deduplicated, order preserved.
    unlocking_docs: list[str] = Field(default_factory=list)
    staleness_flag: bool = False
    #: None when the scheme has no APPROVAL group.
    approval: ApprovalNote | None = None
    #: None when the scheme declares no operating window. Set by the Guard gate, which
    #: is the only place that knows what day it is.
    window: WindowNote | None = None
    #: False when another eligible scheme subsumes this one (resolve_interactions).
    claimable: bool = True
    subsumed_by_scheme: str | None = None
    #: Shared key for schemes that stack, so benefits are not counted twice.
    stack_group_id: str | None = None

    def eligibility_groups(self) -> list[GroupResult]:
        return [g for g in self.group_results if g.kind is GroupKind.ELIGIBILITY]

    def predicates_in(self, group_ids: set[str]) -> list[Predicate]:
        return [p for p in self.predicates if p.group_id in group_ids]


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


def derive_approval(
    group_results: list[GroupResult], predicates: list[Predicate]
) -> ApprovalNote | None:
    """Roll APPROVAL groups up separately from eligibility.

    Returns None when the scheme has no approval conditions. Otherwise it answers the
    approval question on its own terms, leaving `Verdict.status` free to report the
    eligibility we *can* prove.
    """
    approval_groups = [g for g in group_results if g.kind is GroupKind.APPROVAL]
    if not approval_groups:
        return None

    group_ids = {g.group_id for g in approval_groups}
    members = [p for p in predicates if p.group_id in group_ids]

    if any(g.evaluation is Evaluation.FALSE for g in approval_groups):
        status = ApprovalStatus.NOT_MET
    elif all(g.evaluation is Evaluation.TRUE for g in approval_groups):
        status = ApprovalStatus.SETTLED
    else:
        unresolved = {
            g.group_id for g in approval_groups if g.evaluation is Evaluation.UNKNOWN
        }
        blocking = [
            p
            for p in members
            if p.evaluation is Evaluation.UNKNOWN and p.group_id in unresolved
        ]
        status = (
            ApprovalStatus.UNVERIFIABLE
            if any(not p.is_settleable for p in blocking)
            else ApprovalStatus.BLOCKED_ON_DOCUMENT
        )

    deciders: list[str] = []
    for predicate in members:
        if predicate.decided_by and predicate.decided_by not in deciders:
            deciders.append(predicate.decided_by)

    return ApprovalNote(
        status=status,
        deciders=deciders,
        group_ids=sorted(group_ids),
        clause_ids=[p.clause_id for p in members],
        unlocking_docs=collect_unlocking_docs(approval_groups, members),
    )


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


def derive_window(scheme: Scheme, *, today: date) -> WindowNote | None:
    """Where `today` falls in the scheme's own operating window.

    Returns None when the scheme declares no window, which is the honest default: not
    knowing whether a scheme is open is different from knowing it is open, and this
    function will not invent the difference. A scheme with no declared window renders
    exactly as it did before this existed.

    `today` is injected rather than read from the clock for the same reason T5 does it:
    a golden test must not start failing because the calendar moved.
    """
    if scheme.valid_from is None and scheme.valid_until is None:
        return None
    if scheme.valid_until is not None and today > scheme.valid_until:
        state = SchemeWindow.LAPSED
    elif scheme.valid_from is not None and today < scheme.valid_from:
        state = SchemeWindow.NOT_YET_OPEN
    else:
        state = SchemeWindow.OPEN
    return WindowNote(
        state=state,
        valid_from=scheme.valid_from,
        valid_until=scheme.valid_until,
        validity_text=scheme.validity_text,
    )
