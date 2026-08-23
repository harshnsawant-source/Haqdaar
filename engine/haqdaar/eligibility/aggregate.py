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

from haqdaar.eligibility.verdict import Evaluation, Status, Verdict, kleene


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
        for document in verdict.unlocking_docs:
            target = unlocks if _would_clear(verdict, document) else contributes
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


def _would_clear(verdict: Verdict, document: str) -> bool:
    """Would supplying `document` — and nothing else — leave this scheme with no gaps?

    Replays the scheme's own group logic with one change: every unresolved predicate
    that `document` could settle is assumed to come back in the citizen's favour. If
    every eligibility group then resolves TRUE, the document closes the scheme on its
    own and counts as an unlock. If any group is still unresolved, it does not.

    Why this is not the same as "the only document listed":
      * An ANY group ("income under the ceiling OR on the BPL list") is satisfied by
        EITHER document, so each one clears the scheme alone even though two are
        listed. The previous rule under-claimed here.
      * An ALL group needing two different documents is cleared by NEITHER alone, and
        this must keep saying so. Sending someone across a district for a paper that
        changes nothing is the harm the whole aggregator exists to avoid.

    THE ONE OPTIMISTIC ASSUMPTION, stated plainly: we assume the document says what
    the citizen needs it to say. A BPL card only helps if she is actually listed. So
    this answers "which paper could settle this", not "which paper will make you
    eligible" — the same assumption the sole-document case always made, now applied
    consistently rather than only when one document happened to be listed. The
    renderer's wording ("bring X and this unlocks N") inherits that meaning.
    """
    by_group: dict[str, list[Evaluation]] = {}
    for predicate in verdict.predicates:
        if predicate.group_id not in {g.group_id for g in verdict.eligibility_groups()}:
            continue  # approval conditions are not hers to settle with paperwork
        if predicate.evaluation is Evaluation.UNKNOWN and document in predicate.verifiable_from:
            resolved = Evaluation.TRUE
        else:
            resolved = predicate.evaluation
        by_group.setdefault(predicate.group_id, []).append(resolved)

    for group in verdict.eligibility_groups():
        members = by_group.get(group.group_id)
        if not members:
            continue
        if kleene(group.satisfy, members) is not Evaluation.TRUE:
            return False
    return True


def best_unlock(verdicts: list[Verdict]) -> UnlockOption | None:
    """The single document worth putting on screen, or None if none unlocks anything.

    Returns None rather than a document that merely contributes. "You are one document
    away" must be true when we say it.
    """
    for option in aggregate_unlocks(verdicts):
        if option.is_sole_blocker:
            return option
    return None
