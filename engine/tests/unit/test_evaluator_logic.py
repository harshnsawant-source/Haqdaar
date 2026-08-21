"""Evaluator logic against synthetic schemes.

Rule types the day-1 corpus does not contain (income_threshold, exclusion,
external_dataset) are exercised here with synthetic fixtures rather than by inventing
corpus clauses to test them. Fake rules do not go in the corpus, not even for tests.
"""

import pytest
from pydantic import ValidationError

from haqdaar.corpus.schema import (
    Clause,
    ClauseGroup,
    RuleType,
    Satisfy,
    Scheme,
    VerificationStatus,
)
from haqdaar.eligibility.evaluate import evaluate_scheme
from haqdaar.eligibility.verdict import (
    Evaluation,
    GroupResult,
    Predicate,
    Status,
    derive_status,
    kleene,
)
from haqdaar.profile.schema import CitizenProfile, ProfileField

VERIFY = "[VERIFY AT SOURCE]"


def clause(clause_id: str, **kwargs) -> Clause:
    kwargs.setdefault("clause_text", f"{VERIFY} synthetic test clause")
    kwargs.setdefault("verification_status", VerificationStatus.PROVISIONAL)
    kwargs.setdefault("verify_note", "synthetic")
    return Clause(clause_id=clause_id, **kwargs)


def scheme(*groups: ClauseGroup, scheme_id: str = "synthetic") -> Scheme:
    return Scheme(
        scheme_id=scheme_id,
        name="Synthetic",
        authority="test",
        benefit="test",
        source_url="https://example.invalid/",
        retrieved_on="2026-08-21",
        verification_status=VerificationStatus.PROVISIONAL,
        verify_note="synthetic",
        clause_groups=list(groups),
    )


def profile(**values) -> CitizenProfile:
    return CitizenProfile(
        profile_id="synthetic",
        fields={
            key: ProfileField(value=value, document_id="doc", source_field=key)
            for key, value in values.items()
        },
    )


# --- Kleene truth tables -------------------------------------------------------

@pytest.mark.parametrize(
    "values,expected",
    [
        ([Evaluation.TRUE, Evaluation.TRUE], Evaluation.TRUE),
        ([Evaluation.TRUE, Evaluation.UNKNOWN], Evaluation.UNKNOWN),
        ([Evaluation.TRUE, Evaluation.FALSE], Evaluation.FALSE),
        ([Evaluation.UNKNOWN, Evaluation.FALSE], Evaluation.FALSE),
    ],
)
def test_kleene_all(values, expected):
    assert kleene(Satisfy.ALL, values) is expected


@pytest.mark.parametrize(
    "values,expected",
    [
        ([Evaluation.TRUE, Evaluation.UNKNOWN], Evaluation.TRUE),
        ([Evaluation.FALSE, Evaluation.TRUE], Evaluation.TRUE),
        ([Evaluation.FALSE, Evaluation.UNKNOWN], Evaluation.UNKNOWN),
        ([Evaluation.FALSE, Evaluation.FALSE], Evaluation.FALSE),
    ],
)
def test_kleene_any(values, expected):
    assert kleene(Satisfy.ANY, values) is expected


# --- Rule types not present in the day-1 corpus --------------------------------

def test_income_threshold_at_the_boundary_is_inclusive():
    group = ClauseGroup(
        group_id="g",
        satisfy=Satisfy.ALL,
        clauses=[
            clause(
                "INC",
                rule_type=RuleType.INCOME_THRESHOLD,
                profile_field="applicant.income",
                bound={"max_value": 21000, "period": "ANNUAL"},
                verifiable_from=["income_certificate"],
            )
        ],
    )
    assert (
        evaluate_scheme(scheme(group), profile(**{"applicant.income": 21000})).status
        is Status.ELIGIBLE
    )
    assert (
        evaluate_scheme(scheme(group), profile(**{"applicant.income": 21001})).status
        is Status.NOT_ELIGIBLE
    )


def test_exclusion_inverts_polarity_but_keeps_the_evidence():
    group = ClauseGroup(
        group_id="g",
        satisfy=Satisfy.ALL,
        clauses=[
            clause(
                "EXC",
                rule_type=RuleType.EXCLUSION,
                profile_field="applicant.taxpayer",
                bound={"values": ["true"]},
                verifiable_from=["itr"],
            )
        ],
    )
    excluded = evaluate_scheme(scheme(group), profile(**{"applicant.taxpayer": True}))
    assert excluded.status is Status.NOT_ELIGIBLE
    # The verdict still shows what was read from the document.
    assert excluded.predicates[0].evidence.extracted_value is True

    allowed = evaluate_scheme(scheme(group), profile(**{"applicant.taxpayer": False}))
    assert allowed.status is Status.ELIGIBLE


def test_category_matching_survives_case_and_booleans():
    """Regression: str(True) is "True", so a boolean never matched a lowercase bound.

    An extracted "sc" and a corpus "SC" are the same category. A confident FALSE
    caused by a capital letter is a wrong answer, not a strict one.
    """
    group = ClauseGroup(
        group_id="g",
        satisfy=Satisfy.ALL,
        clauses=[
            clause(
                "CAT",
                rule_type=RuleType.ENUMERATED_CATEGORY,
                profile_field="applicant.social_category",
                bound={"values": ["SC", "ST"]},
                verifiable_from=["caste_certificate"],
            ),
            clause(
                "FLAG",
                rule_type=RuleType.ENUMERATED_CATEGORY,
                profile_field="household.bpl",
                bound={"values": ["true"]},
                verifiable_from=["bpl_ration_card"],
            ),
        ],
    )
    verdict = evaluate_scheme(
        scheme(group),
        profile(**{"applicant.social_category": " sc ", "household.bpl": True}),
    )
    assert verdict.status is Status.ELIGIBLE


def test_external_dataset_never_reads_the_profile():
    """PM-JAY's SECC-2011 shape: unsettleable even when a matching field exists."""
    group = ClauseGroup(
        group_id="g",
        satisfy=Satisfy.ALL,
        clauses=[clause("SECC", rule_type=RuleType.EXTERNAL_DATASET)],
    )
    verdict = evaluate_scheme(scheme(group), profile(**{"household.secc": "listed"}))
    assert verdict.status is Status.UNVERIFIABLE
    assert verdict.predicates[0].evaluation is Evaluation.UNKNOWN
    assert verdict.unlocking_docs == []


def test_missing_field_blocks_on_the_named_document():
    group = ClauseGroup(
        group_id="g",
        satisfy=Satisfy.ALL,
        clauses=[
            clause(
                "BPL",
                rule_type=RuleType.ENUMERATED_CATEGORY,
                profile_field="household.bpl",
                bound={"values": ["true"]},
                verifiable_from=["bpl_ration_card"],
            )
        ],
    )
    verdict = evaluate_scheme(scheme(group), profile())
    assert verdict.status is Status.BLOCKED_ON_DOCUMENT
    assert verdict.unlocking_docs == ["bpl_ration_card"]


def test_low_confidence_field_is_treated_as_unread():
    group = ClauseGroup(
        group_id="g",
        satisfy=Satisfy.ALL,
        clauses=[
            clause(
                "CAT",
                rule_type=RuleType.ENUMERATED_CATEGORY,
                profile_field="applicant.social_category",
                bound={"values": ["SC"]},
                verifiable_from=["caste_certificate"],
            )
        ],
    )
    smudged = CitizenProfile(
        profile_id="p",
        fields={
            "applicant.social_category": ProfileField(
                value="SC",
                document_id="caste_certificate",
                source_field="category",
                confidence=0.4,
            )
        },
    )
    assert evaluate_scheme(scheme(group), smudged).status is Status.BLOCKED_ON_DOCUMENT


def test_type_mismatch_refuses_rather_than_denying():
    """A number expected, a word found. Bias to refuse, never a confident no."""
    group = ClauseGroup(
        group_id="g",
        satisfy=Satisfy.ALL,
        clauses=[
            clause(
                "AGE",
                rule_type=RuleType.NUMERIC_BOUND,
                profile_field="applicant.age",
                bound={"min": 18, "max": 65},
                verifiable_from=["aadhaar"],
            )
        ],
    )
    verdict = evaluate_scheme(scheme(group), profile(**{"applicant.age": "sixty"}))
    assert verdict.status is Status.BLOCKED_ON_DOCUMENT
    assert verdict.predicates[0].evaluation is Evaluation.UNKNOWN


# --- Status precedence ---------------------------------------------------------

def test_proven_no_outranks_unproven_maybe():
    """NOT_ELIGIBLE beats UNVERIFIABLE: the citizen can act on a proven no."""
    verdict = evaluate_scheme(
        scheme(
            ClauseGroup(
                group_id="age",
                satisfy=Satisfy.ALL,
                clauses=[
                    clause(
                        "AGE",
                        rule_type=RuleType.NUMERIC_BOUND,
                        profile_field="applicant.age",
                        bound={"min": 70},
                        verifiable_from=["aadhaar"],
                    )
                ],
            ),
            ClauseGroup(
                group_id="secc",
                satisfy=Satisfy.ALL,
                clauses=[clause("SECC", rule_type=RuleType.EXTERNAL_DATASET)],
            ),
        ),
        profile(**{"applicant.age": 60}),
    )
    assert verdict.status is Status.NOT_ELIGIBLE


def test_unverifiable_outranks_blocked():
    """Never send someone to fetch a paper that cannot settle the question."""
    verdict = evaluate_scheme(
        scheme(
            ClauseGroup(
                group_id="bpl",
                satisfy=Satisfy.ALL,
                clauses=[
                    clause(
                        "BPL",
                        rule_type=RuleType.ENUMERATED_CATEGORY,
                        profile_field="household.bpl",
                        bound={"values": ["true"]},
                        verifiable_from=["bpl_ration_card"],
                    )
                ],
            ),
            ClauseGroup(
                group_id="secc",
                satisfy=Satisfy.ALL,
                clauses=[clause("SECC", rule_type=RuleType.EXTERNAL_DATASET)],
            ),
        ),
        profile(),
    )
    assert verdict.status is Status.UNVERIFIABLE


def test_satisfied_any_group_does_not_block_on_its_unknown_members():
    """The subtle one.

    An ANY group already satisfied by one TRUE member is settled. Its other UNKNOWN
    members are not missing evidence, they are unneeded — and must not drag the whole
    scheme to BLOCKED or UNVERIFIABLE.
    """
    verdict = evaluate_scheme(
        scheme(
            ClauseGroup(
                group_id="category",
                satisfy=Satisfy.ANY,
                clauses=[
                    clause(
                        "WOMAN",
                        rule_type=RuleType.ENUMERATED_CATEGORY,
                        profile_field="applicant.gender",
                        bound={"values": ["FEMALE"]},
                        verifiable_from=["aadhaar"],
                    ),
                    clause(
                        "CASTE",
                        rule_type=RuleType.ENUMERATED_CATEGORY,
                        profile_field="applicant.social_category",
                        bound={"values": ["SC", "ST"]},
                        verifiable_from=["caste_certificate"],
                    ),
                ],
            )
        ),
        profile(**{"applicant.gender": "FEMALE"}),
    )
    assert verdict.status is Status.ELIGIBLE
    assert verdict.unlocking_docs == []


def test_derive_status_is_the_single_definition():
    """Day 2's guard consumes this table; it must not reimplement it."""
    groups = [
        GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)
    ]
    predicates = [
        Predicate(
            clause_id="c",
            group_id="g",
            clause_text="x",
            source_url="https://example.invalid/",
            retrieved_on="2026-08-21",
            evaluation=Evaluation.UNKNOWN,
            verifiable_from=[],
        )
    ]
    assert derive_status(groups, predicates) is Status.UNVERIFIABLE


# --- The evidence invariant is enforced by the type ----------------------------

def test_predicate_cannot_resolve_without_evidence():
    with pytest.raises(ValidationError, match="requires evidence"):
        Predicate(
            clause_id="c",
            group_id="g",
            clause_text="x",
            source_url="https://example.invalid/",
            retrieved_on="2026-08-21",
            evaluation=Evaluation.TRUE,
            evidence=None,
        )
