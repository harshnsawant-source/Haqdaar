"""The unlock aggregator: "one <document> unlocks N more."

Design doc s5 guarantee 7 — computed off the verdict set, never a phrasing a model
chose. Pure functions, no model, no network.

The honesty problem this module exists to solve
-----------------------------------------------
The naive version counts every BLOCKED verdict that mentions a document and reports
"bring your caste certificate and unlock 4 more." That claim is false whenever a scheme
is blocked on *two* documents: fetching one of them unlocks nothing, and we will have
sent someone across a district for a paper that changes their result not at all.

So each document is scored two ways:

* `unlocks` — schemes where this document is the ONLY thing still missing. Fetching it
  resolves them. This is the only number the headline may use.
* `contributes_to` — schemes where it is one of several blockers. Real, but it does not
  unlock anything on its own, and must be phrased as progress rather than a promise.

Ranking is by `unlocks` and ties break alphabetically, so the order is stable on stage
and in golden tests.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from haqdaar.eligibility.verdict import Status, Verdict


class UnlockOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    #: Schemes this document alone would resolve. Safe to promise.
    unlocks: list[str] = Field(default_factory=list)
    #: Schemes where it is one of several missing documents. Progress, not a promise.
    contributes_to: list[str] = Field(default_factory=list)

    @property
    def unlock_count(self) -> int:
        return len(self.unlocks)

    @property
    def is_sole_blocker(self) -> bool:
        return bool(self.unlocks)


def aggregate_unlocks(verdicts: list[Verdict]) -> list[UnlockOption]:
    """Group blocked verdicts by missing document, best first.

    Only BLOCKED_ON_DOCUMENT eligibility is considered. An UNVERIFIABLE scheme is not
    waiting on paperwork, and an approval condition is not the citizen's to settle.
    """
    blocked = [
        v
        for v in verdicts
        if v.status is Status.BLOCKED_ON_DOCUMENT and v.claimable and v.unlocking_docs
    ]

    unlocks: dict[str, list[str]] = {}
    contributes: dict[str, list[str]] = {}
    for verdict in blocked:
        sole_blocker = len(verdict.unlocking_docs) == 1
        for document in verdict.unlocking_docs:
            target = unlocks if sole_blocker else contributes
            target.setdefault(document, []).append(verdict.scheme_id)

    options = [
        UnlockOption(
            document_id=document,
            unlocks=sorted(unlocks.get(document, [])),
            contributes_to=sorted(contributes.get(document, [])),
        )
        for document in sorted(set(unlocks) | set(contributes))
    ]
    return sorted(options, key=lambda o: (-o.unlock_count, o.document_id))


def best_unlock(verdicts: list[Verdict]) -> UnlockOption | None:
    """The single document worth putting on screen, or None if none unlocks anything.

    Returns None rather than a document that merely contributes. "You are one document
    away" must be true when we say it.
    """
    for option in aggregate_unlocks(verdicts):
        if option.is_sole_blocker:
            return option
    return None
