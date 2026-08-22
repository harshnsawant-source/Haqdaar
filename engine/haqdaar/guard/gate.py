"""The gate: nothing reaches a renderer without passing through here.

Guard doc s1 — a verdict that fails validation cannot be displayed as an answer, and
there is no path around this. The renderer accepts only a `GateResult`, which it cannot
construct itself, so "unvalidated output cannot reach the screen" is enforced by the
type system rather than by everyone remembering to call validate().
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from haqdaar.corpus.schema import Scheme
from haqdaar.eligibility.verdict import Verdict
from haqdaar.guard.triggers import (
    STALENESS_WINDOW_DAYS,
    Finding,
    GuardViolation,
    check,
    t5_stale_rule,
    validate,
)


class GateResult(BaseModel):
    """A verdict that has passed the Guard, plus why it says what it says."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict: Verdict
    findings: list[Finding] = Field(default_factory=list)

    def findings_for(self, *triggers) -> list[Finding]:
        wanted = set(triggers)
        return [f for f in self.findings if f.trigger in wanted]


def gate(
    verdict: Verdict,
    scheme: Scheme,
    *,
    today: date,
    window_days: int = STALENESS_WINDOW_DAYS,
) -> GateResult:
    """Validate a verdict and collect every finding that applies to it.

    Raises GuardViolation if the verdict's status contradicts its own predicates.
    Staleness (T5) is additive: it flags the answer, it never suppresses it.
    """
    if verdict.scheme_id != scheme.scheme_id:
        raise GuardViolation(
            f"verdict is for {verdict.scheme_id}, scheme is {scheme.scheme_id}"
        )

    findings = list(validate(verdict))  # raises on a self-contradicting verdict

    stale = t5_stale_rule(scheme, today=today, window_days=window_days)
    if stale is not None:
        findings.append(stale)

    return GateResult(
        verdict=verdict.model_copy(update={"staleness_flag": stale is not None}),
        findings=findings,
    )


def gate_all(
    verdicts: list[Verdict],
    schemes: list[Scheme],
    *,
    today: date,
    window_days: int = STALENESS_WINDOW_DAYS,
) -> list[GateResult]:
    by_id = {s.scheme_id: s for s in schemes}
    return [
        gate(v, by_id[v.scheme_id], today=today, window_days=window_days)
        for v in verdicts
        if v.scheme_id in by_id
    ]


def unchecked(verdict: Verdict) -> GateResult:
    """Escape hatch for tests only. Never call this from engine or API code."""
    return GateResult(verdict=verdict, findings=list(check(verdict)))
