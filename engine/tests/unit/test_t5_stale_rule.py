"""T5 — the rule may have moved since we transcribed it.

Flagged, never blocked. The answer still shows, with a banner. T5 is a statement about
our corpus, not about the citizen, so suppressing the answer would punish her for our
transcription date.
"""

from datetime import date

import pytest
from _helpers import predicate, verdict

from haqdaar.corpus.schema import (
    CategoryBound,
    Clause,
    ClauseGroup,
    RuleType,
    Satisfy,
    Scheme,
    VerificationStatus,
)
from haqdaar.eligibility.verdict import Evaluation, GroupResult, Status
from haqdaar.guard.gate import gate
from haqdaar.guard.triggers import TriggerId, t5_stale_rule


def scheme(*, retrieved_on: date, last_amended: date | None = None) -> Scheme:
    return Scheme(
        scheme_id="synthetic",
        name="Synthetic",
        authority="test",
        benefit="test",
        source_url="https://example.invalid/",
        retrieved_on=retrieved_on,
        last_amended=last_amended,
        verification_status=VerificationStatus.PROVISIONAL,
        verify_note="synthetic",
        clause_groups=[
            ClauseGroup(
                group_id="g",
                satisfy=Satisfy.ALL,
                clauses=[
                    Clause(
                        clause_id="C",
                        clause_text="[VERIFY AT SOURCE] synthetic",
                        rule_type=RuleType.ENUMERATED_CATEGORY,
                        profile_field="applicant.x",
                        bound=CategoryBound(values=["y"]),
                        verifiable_from=["doc"],
                        verification_status=VerificationStatus.PROVISIONAL,
                        verify_note="synthetic",
                    )
                ],
            )
        ],
    )


TODAY = date(2026, 8, 22)


def test_fresh_rule_does_not_flag():
    assert t5_stale_rule(scheme(retrieved_on=date(2026, 8, 21)), today=TODAY) is None


def test_amended_after_we_read_it_flags():
    """The AVVC shape: the source records a change after our transcription date."""
    finding = t5_stale_rule(
        scheme(retrieved_on=date(2024, 1, 1), last_amended=date(2024, 10, 1)),
        today=date(2024, 10, 2),
    )
    assert finding is not None
    assert finding.trigger is TriggerId.T5_STALE_RULE
    assert finding.retrieved_on == "2024-01-01"
    assert finding.last_amended == "2024-10-01"


def test_amended_before_we_read_it_does_not_flag():
    """We read the page after the change, so our transcription already reflects it."""
    assert (
        t5_stale_rule(
            scheme(retrieved_on=date(2026, 8, 21), last_amended=date(2024, 10, 1)),
            today=TODAY,
        )
        is None
    )


def test_read_too_long_ago_flags_even_without_an_amendment():
    finding = t5_stale_rule(
        scheme(retrieved_on=date(2025, 1, 1)), today=TODAY, window_days=180
    )
    assert finding is not None
    assert finding.last_amended is None


def test_window_boundary_is_exclusive():
    read_on = date(2026, 2, 22)  # exactly 181 days before TODAY
    assert t5_stale_rule(scheme(retrieved_on=read_on), today=TODAY, window_days=181) is None
    assert t5_stale_rule(scheme(retrieved_on=read_on), today=TODAY, window_days=180) is not None


def test_staleness_flags_the_verdict_without_changing_its_status():
    """The citizen still gets her answer. She just also gets told to check the date."""
    v = verdict(
        [predicate("C", "g", Evaluation.TRUE, verifiable_from=["doc"])],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.TRUE)],
        Status.ELIGIBLE,
        scheme_id="synthetic",
    )
    result = gate(v, scheme(retrieved_on=date(2025, 1, 1)), today=TODAY)
    assert result.verdict.status is Status.ELIGIBLE
    assert result.verdict.staleness_flag is True
    assert [f.trigger for f in result.findings] == [TriggerId.T5_STALE_RULE]


def test_fresh_rule_leaves_the_flag_down():
    v = verdict(
        [predicate("C", "g", Evaluation.TRUE, verifiable_from=["doc"])],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.TRUE)],
        Status.ELIGIBLE,
        scheme_id="synthetic",
    )
    result = gate(v, scheme(retrieved_on=date(2026, 8, 21)), today=TODAY)
    assert result.verdict.staleness_flag is False
    assert result.findings == []


def test_gate_refuses_a_mismatched_scheme():
    v = verdict(
        [predicate("C", "g", Evaluation.TRUE, verifiable_from=["doc"])],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.TRUE)],
        Status.ELIGIBLE,
        scheme_id="a-different-scheme",
    )
    with pytest.raises(Exception, match="verdict is for"):
        gate(v, scheme(retrieved_on=TODAY), today=TODAY)
