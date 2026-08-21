"""subsumed_by / stacks_with resolution across a verdict set.

Driven by a real corpus fact (01-DEMO-CORPUS.md s2): IGNWPS is reached *through* SGNAY
in Maharashtra, so listing both as independent Rs 1,500 benefits would be wrong and a
judge who knows the state would catch it.
"""

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
from haqdaar.eligibility.evaluate import _stack_groups, resolve_interactions
from haqdaar.eligibility.verdict import Evaluation, GroupResult, Status


def scheme(scheme_id: str, *, subsumed_by=(), stacks_with=()) -> Scheme:
    return Scheme(
        scheme_id=scheme_id,
        name=scheme_id,
        authority="test",
        benefit="test",
        source_url="https://example.invalid/",
        retrieved_on="2026-08-21",
        verification_status=VerificationStatus.PROVISIONAL,
        verify_note="synthetic",
        subsumed_by=list(subsumed_by),
        stacks_with=list(stacks_with),
        clause_groups=[
            ClauseGroup(
                group_id="g",
                satisfy=Satisfy.ALL,
                clauses=[
                    Clause(
                        clause_id=f"{scheme_id}-C1",
                        clause_text="[VERIFY AT SOURCE] synthetic",
                        rule_type=RuleType.ENUMERATED_CATEGORY,
                        profile_field="applicant.x",
                        bound=CategoryBound(values=["y"]),
                        verification_status=VerificationStatus.PROVISIONAL,
                        verify_note="synthetic",
                    )
                ],
            )
        ],
    )


def eligible(scheme_id: str):
    return verdict(
        [predicate("C", "g", Evaluation.TRUE, verifiable_from=["doc"])],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.TRUE)],
        Status.ELIGIBLE,
        scheme_id=scheme_id,
    )


def test_subsumed_scheme_is_not_separately_claimable():
    resolved = resolve_interactions(
        [eligible("sgnay"), eligible("ignwps")],
        [scheme("sgnay"), scheme("ignwps", subsumed_by=["sgnay"])],
    )
    by_id = {v.scheme_id: v for v in resolved}
    assert by_id["sgnay"].claimable is True
    assert by_id["ignwps"].claimable is False
    assert by_id["ignwps"].subsumed_by_scheme == "sgnay"


def test_subsumption_only_applies_when_the_absorber_is_eligible():
    """If she does not qualify for the absorbing scheme, the other still stands."""
    blocked_absorber = verdict(
        [predicate("C", "g", Evaluation.UNKNOWN, verifiable_from=["bpl"])],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.BLOCKED_ON_DOCUMENT,
        scheme_id="sgnay",
        unlocking_docs=["bpl"],
    )
    resolved = resolve_interactions(
        [blocked_absorber, eligible("ignwps")],
        [scheme("sgnay"), scheme("ignwps", subsumed_by=["sgnay"])],
    )
    by_id = {v.scheme_id: v for v in resolved}
    assert by_id["ignwps"].claimable is True
    assert by_id["ignwps"].subsumed_by_scheme is None


def test_stacking_schemes_share_a_group_key():
    resolved = resolve_interactions(
        [eligible("sgnay"), eligible("ignwps")],
        [scheme("sgnay", stacks_with=["ignwps"]), scheme("ignwps")],
    )
    keys = {v.scheme_id: v.stack_group_id for v in resolved}
    assert keys["sgnay"] == keys["ignwps"] == "ignwps"  # lowest id keys the component


def test_stacking_is_symmetric_even_if_written_on_one_side():
    groups = _stack_groups([scheme("a", stacks_with=["b"]), scheme("b")])
    assert groups == {"a": "a", "b": "a"}


def test_unrelated_schemes_have_no_stack_group():
    resolved = resolve_interactions(
        [eligible("a"), eligible("b")], [scheme("a"), scheme("b")]
    )
    assert all(v.stack_group_id is None for v in resolved)


def test_stacks_with_an_unknown_scheme_is_ignored():
    """A dangling reference in the corpus must not crash the engine mid-demo."""
    resolved = resolve_interactions([eligible("a")], [scheme("a", stacks_with=["ghost"])])
    assert resolved[0].stack_group_id is None
