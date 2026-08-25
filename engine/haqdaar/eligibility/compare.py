"""Side-by-side comparison of schemes, as structure and never as a verdict.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It does not pick a winner. The obvious feature request is "show the best fit for your
profile", and that is the one thing this module refuses, for the same reason the
renderer refuses "you may qualify": a ranking is a claim, and this project only makes
claims it can prove from a clause.

Two schemes a citizen is provably eligible for are BOTH hers. Which is worth more
depends on facts nobody here holds: what the benefit is actually worth to her, how long
each office takes, whether the money arrives this quarter or next, whether she can
travel to the filing office. Answering that with a confident arrow would be inventing
the most important number on the screen.

So comparison returns facts side by side, ordered by what she can act on, and lets a
person decide. The ordering is the same actionability ordering the results list already
uses, and it is described in `ACTIONABILITY` below so a reader can see there is no
scoring behind it.

Every value here is copied from the corpus or from a verdict. Nothing is computed,
summarised or phrased.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from haqdaar.corpus.schema import GroupKind, Scheme, VerificationStatus
from haqdaar.eligibility.verdict import SchemeWindow, Status, Verdict

#: How useful an outcome is to act on, best first. Not a score and not a confidence:
#: an entitlement you can claim outranks a paper you can fetch, which outranks a rule
#: nobody can settle, which outranks a door that is shut to you.
ACTIONABILITY = {
    Status.ELIGIBLE: 0,
    Status.BLOCKED_ON_DOCUMENT: 1,
    Status.UNVERIFIABLE: 2,
    Status.NOT_ELIGIBLE: 3,
}

#: A comparison wider than this stops being readable on a phone, and the point of the
#: feature is a decision, not a spreadsheet.
MAX_SCHEMES = 4


class ComparisonError(Exception):
    """The comparison could not be built. Never returned as a partial table."""


class ComparedScheme(BaseModel):
    """One column. Every field is copied, never derived."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme_id: str
    name: str
    authority: str
    benefit: str
    source_url: str
    retrieved_on: str
    verification_status: VerificationStatus
    portal_url: str | None = None
    filing_office: str | None = None

    #: OPEN | LAPSED | NOT_YET_OPEN, or None when the scheme declares no window.
    window_state: str | None = None

    #: The eligibility clauses, verbatim, so the columns can be read against each other.
    eligibility_clauses: list[str] = Field(default_factory=list)
    #: Documents any eligibility clause accepts as proof, deduplicated, order preserved.
    documents_accepted: list[str] = Field(default_factory=list)
    #: Who decides the downstream question, when the scheme has one. Empty means the
    #: scheme's own rules settle it end to end.
    decided_by: list[str] = Field(default_factory=list)

    #: Present only when a profile was supplied. None means "not evaluated", which is a
    #: different thing from "evaluated and unknown" and must not be collapsed into it.
    status: Status | None = None
    unlocking_docs: list[str] = Field(default_factory=list)
    stack_group_id: str | None = None


class Comparison(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schemes: list[ComparedScheme] = Field(default_factory=list)
    #: Scheme ids that are two halves of one payment rather than two benefits. Grouped
    #: from the corpus's own `stacks_with`, so a comparison cannot double-count.
    stacked_groups: list[list[str]] = Field(default_factory=list)


def _ordered(dedupe: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in dedupe:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def compare(
    schemes: list[Scheme], verdicts: list[Verdict] | None = None
) -> Comparison:
    """Build a side-by-side view of two to four schemes.

    `verdicts` is optional. Without it the comparison is a plain fact table, which is
    what a citizen browsing before she has answered anything should see. With it, each
    column also carries her real status, and the columns are ordered by what she can
    act on.
    """
    if not 2 <= len(schemes) <= MAX_SCHEMES:
        raise ComparisonError(
            f"compare two to {MAX_SCHEMES} schemes; got {len(schemes)}"
        )

    ids = [s.scheme_id for s in schemes]
    if len(set(ids)) != len(ids):
        raise ComparisonError(f"duplicate scheme(s) in comparison: {sorted(ids)}")

    by_id = {v.scheme_id: v for v in verdicts or []}
    if verdicts is not None:
        missing = sorted(set(ids) - set(by_id))
        if missing:
            # A column with no verdict beside columns that have one would read as
            # "nothing found for this scheme", which is a claim we did not make.
            raise ComparisonError(f"no verdict supplied for: {missing}")

    columns: list[ComparedScheme] = []
    for scheme in schemes:
        verdict = by_id.get(scheme.scheme_id)
        eligibility = scheme.groups_of(GroupKind.ELIGIBILITY)
        approval = scheme.groups_of(GroupKind.APPROVAL)

        columns.append(
            ComparedScheme(
                scheme_id=scheme.scheme_id,
                name=scheme.name,
                authority=scheme.authority,
                benefit=scheme.benefit,
                source_url=scheme.source_url,
                retrieved_on=scheme.retrieved_on.isoformat(),
                verification_status=scheme.verification_status,
                portal_url=scheme.portal_url,
                filing_office=scheme.filing_office,
                # Only the Guard gate is told what day it is, so without a verdict the
                # honest answer is "not evaluated" rather than a window computed off
                # this process's clock.
                window_state=(
                    verdict.window.state.value
                    if verdict is not None and verdict.window is not None
                    else None
                ),
                eligibility_clauses=[
                    c.clause_text for g in eligibility for c in g.clauses
                ],
                documents_accepted=_ordered(
                    [d for g in eligibility for c in g.clauses for d in c.verifiable_from]
                ),
                decided_by=_ordered(
                    [c.decided_by for g in approval for c in g.clauses if c.decided_by]
                ),
                status=verdict.status if verdict is not None else None,
                unlocking_docs=list(verdict.unlocking_docs) if verdict else [],
                stack_group_id=verdict.stack_group_id if verdict else None,
            )
        )

    if verdicts is not None:
        columns.sort(key=_actionability)

    return Comparison(schemes=columns, stacked_groups=_stacked(schemes))


def _actionability(column: ComparedScheme) -> tuple[int, int, str]:
    """Sort key: what she can act on first. Still not a score.

    The window is part of it. Two schemes can both be ELIGIBLE while one of them shut
    last year, and sorting those level would put a closed door above an open one purely
    on alphabetical order. That is how Stand-Up India sorted above NSFDC before this
    existed. A scheme you cannot apply to is the least actionable thing on the table,
    whatever its verdict says about you.
    """
    shut = column.window_state in {SchemeWindow.LAPSED.value, SchemeWindow.NOT_YET_OPEN.value}
    return (ACTIONABILITY[column.status], 1 if shut else 0, column.scheme_id)


def _stacked(schemes: list[Scheme]) -> list[list[str]]:
    """Group schemes the corpus says are two halves of one payment.

    IGNWPS and SGNAY are the case this exists for: a Maharashtra widow's Rs 1,500 is
    Rs 300 central topped up by Rs 1,200 state, not two separate Rs 1,500 benefits.
    A comparison table is exactly where someone would otherwise add them up.
    """
    present = {s.scheme_id for s in schemes}
    groups: list[list[str]] = []
    seen: set[str] = set()

    for scheme in schemes:
        if scheme.scheme_id in seen:
            continue
        partners = sorted(set(scheme.stacks_with) & present)
        if not partners:
            continue
        group = sorted({scheme.scheme_id, *partners})
        seen.update(group)
        groups.append(group)

    return groups
