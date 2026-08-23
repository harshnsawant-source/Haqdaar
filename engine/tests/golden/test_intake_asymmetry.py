"""A declaration can rule a scheme out. It can never rule one in.

The strict rule — a declaration settles only what the corpus says a declaration
settles — was applied symmetrically, and that was wrong. A 34-year-old unmarried woman
was told to "bring your death certificate and this unlocks Indira Gandhi National Widow
Pension Scheme". You do not need a death certificate to establish that you are not a
widow, or an Aadhaar to establish that you are not seventy.

The honest rule is one-directional:

    declaration that would SATISFY a clause -> UNKNOWN, go and get the document
    declaration that FAILS a clause         -> FALSE, she is ruled out, cited to her

This file holds that line in both directions, and proves the safety property: the
asymmetry only ever removes claims.
"""

from datetime import date

import pytest

from haqdaar.corpus.loader import load_corpus
from haqdaar.corpus.schema import (
    CategoryBound,
    Clause,
    ClauseGroup,
    RuleType,
    Satisfy,
    Scheme,
    VerificationStatus,
)
from haqdaar.eligibility.evaluate import evaluate_corpus, evaluate_scheme
from haqdaar.eligibility.verdict import Status
from haqdaar.guard.gate import gate_all
from haqdaar.profile.intake import build_intake_profile, load_intake
from haqdaar.render.render import render_card


@pytest.fixture(scope="module")
def spec(corpus_dir):
    return load_intake(corpus_dir / "intake.yaml")


def test_a_declaration_that_fails_a_requirement_rules_the_scheme_out(
    spec, welfare_schemes_dir, today
):
    """The reported bug, pinned."""
    schemes = load_corpus(welfare_schemes_dir)
    profile = build_intake_profile(
        spec, {"age": 34, "marital_status": "UNMARRIED"}, schemes=schemes
    )
    verdicts = evaluate_corpus(schemes, profile)
    by_status = {v.scheme_id: v.status for v in verdicts}

    assert by_status["avvc"] is Status.NOT_ELIGIBLE
    assert by_status["ignwps"] is Status.NOT_ELIGIBLE

    by_id = {s.scheme_id: s for s in schemes}
    results = {r.verdict.scheme_id: r for r in gate_all(verdicts, schemes, today=today)}

    avvc = render_card(results["avvc"], by_id["avvc"], today=today)
    assert avvc.lines[1] == "The rule says 70 and above. Your age is 34."

    ignwps = render_card(results["ignwps"], by_id["ignwps"], today=today)
    assert ignwps.lines[1] == "The rule says widow. Your marital status is unmarried."

    # And nobody is sent for a paper that belongs to a scheme they are ruled out of.
    for card in (avvc, ignwps):
        assert not any("Bring your" in line for line in card.lines)


def test_a_declaration_that_would_satisfy_a_requirement_still_blocks(
    spec, welfare_schemes_dir
):
    """The other direction is unchanged. She cannot claim on her own word."""
    schemes = load_corpus(welfare_schemes_dir)
    profile = build_intake_profile(
        spec, {"age": 60, "marital_status": "WIDOW"}, schemes=schemes
    )
    ignwps = next(
        v for v in evaluate_corpus(schemes, profile) if v.scheme_id == "ignwps"
    )
    assert ignwps.status is Status.BLOCKED_ON_DOCUMENT
    assert "husband_death_certificate" in ignwps.unlocking_docs


def test_a_declaration_can_never_manufacture_an_eligible(
    spec, welfare_schemes_dir, schemes_dir
):
    """The safety property.

    The asymmetry only ever converts UNKNOWN to FALSE. It produces no TRUE, so no
    group can newly resolve TRUE and no scheme can become ELIGIBLE because of it. A
    card can only move from BLOCKED to NOT_ELIGIBLE.

    Answered maximally in her own favour, across both corpora.
    """
    answers = {
        "age": 60,
        "gender": "FEMALE",
        "marital_status": "WIDOW",
        "social_category": "SC",
        "landholding": 0.8,
        "annual_income": 10000,
        "bpl": True,
        "venture_type": "GREENFIELD",
        "loan_amount": 1500000,
        "paid_income_tax": False,
        "government_employee": False,
        "constitutional_post": False,
        "registered_professional": False,
        "institutional_landholder": False,
        "monthly_pension": 0,
    }
    for directory in (welfare_schemes_dir, schemes_dir):
        schemes = load_corpus(directory)
        profile = build_intake_profile(spec, answers, schemes=schemes)
        for verdict in evaluate_corpus(schemes, profile):
            assert verdict.status is not Status.ELIGIBLE, verdict.scheme_id


def _exclusion_scheme() -> Scheme:
    return Scheme(
        scheme_id="synthetic-exclusion",
        name="Synthetic",
        authority="test",
        benefit="test",
        source_url="https://example.invalid/",
        retrieved_on=date(2026, 8, 21),
        verification_status=VerificationStatus.PROVISIONAL,
        verify_note="synthetic",
        clause_groups=[
            ClauseGroup(
                group_id="g",
                satisfy=Satisfy.ALL,
                clauses=[
                    Clause(
                        clause_id="X",
                        clause_text="[VERIFY AT SOURCE] Income tax payers are excluded.",
                        rule_type=RuleType.EXCLUSION,
                        profile_field="applicant.paid_income_tax",
                        bound=CategoryBound(values=["true"]),
                        # Only an ITR clears this one — not her word.
                        verifiable_from=["itr"],
                        verification_status=VerificationStatus.PROVISIONAL,
                        verify_note="synthetic",
                    )
                ],
            )
        ],
    )


def test_a_declaration_cannot_clear_an_exclusion_the_corpus_wants_proof_for(spec):
    """The exclusion interaction, which is where an asymmetry could go wrong.

    The rule is stated on the clause's contribution to eligibility, with the exclusion
    already inverted, and that is what makes it come out right:

      "I did not pay tax"  -> would CLEAR the exclusion, a claim in her favour, so it
                              still needs the document the corpus asks for
      "I did pay tax"      -> an admission against interest, and rules her out at once
    """
    scheme = _exclusion_scheme()

    clean = build_intake_profile(spec, {"paid_income_tax": False}, schemes=[scheme])
    assert evaluate_scheme(scheme, clean).status is Status.BLOCKED_ON_DOCUMENT

    admits = build_intake_profile(spec, {"paid_income_tax": True}, schemes=[scheme])
    assert evaluate_scheme(scheme, admits).status is Status.NOT_ELIGIBLE


def test_no_not_eligible_card_promises_a_reason_and_gives_none(
    spec, welfare_schemes_dir, today
):
    """"Here is exactly why" must always be followed by the why.

    Category rules had no bound description, so a NOT_ELIGIBLE card rendered its
    headline and stopped. A promised reason with no reason is worse than silence, and
    the asymmetry made those cards common.
    """
    schemes = load_corpus(welfare_schemes_dir)
    by_id = {s.scheme_id: s for s in schemes}
    checked = 0

    for answers in (
        {"age": 34, "marital_status": "UNMARRIED"},
        {"age": 60, "marital_status": "WIDOW"},
        {"age": 90, "marital_status": "DIVORCED"},
        {"age": 20, "marital_status": "MARRIED", "annual_income": 900000},
    ):
        profile = build_intake_profile(spec, answers, schemes=schemes)
        verdicts = evaluate_corpus(schemes, profile)
        for result in gate_all(verdicts, schemes, today=today):
            if result.verdict.status is not Status.NOT_ELIGIBLE:
                continue
            card = render_card(result, by_id[result.verdict.scheme_id], today=today)
            assert len(card.lines) >= 2, f"{card.scheme_id}: headline with no reason"
            assert card.lines[1].startswith("The rule says ")
            checked += 1

    assert checked > 0, "no NOT_ELIGIBLE card was produced — test proved nothing"
