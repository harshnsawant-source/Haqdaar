"""The reveal vertical, end to end. Same engine, different folder.

This file is the platform claim made testable: every assertion below runs through the
same evaluator, Guard, renderer and aggregator as the entrepreneur vertical, with no
branch anywhere that knows what a welfare scheme is.

Sunita's arc mirrors the entrepreneur arc exactly:

    PM-KISAN   ELIGIBLE            proof from her 7/12 land record
    IGNWPS     BLOCKED             one BPL ration card away
    SGNAY      BLOCKED             income certificate OR BPL, and it stacks with IGNWPS
    PM-JAY     UNVERIFIABLE        SECC 2011, which she cannot obtain
    AVVC       NOT_ELIGIBLE        the rule is 70+, she is 60, she qualifies in 2036
"""

from haqdaar.corpus.loader import load_corpus
from haqdaar.eligibility.aggregate import aggregate_unlocks, best_unlock
from haqdaar.eligibility.evaluate import evaluate_corpus
from haqdaar.eligibility.verdict import Evaluation, Status
from haqdaar.guard.gate import gate_all
from haqdaar.render.render import render_card


def _run(welfare_schemes_dir, sunita_profile, today):
    schemes = load_corpus(welfare_schemes_dir)
    verdicts = evaluate_corpus(schemes, sunita_profile)
    results = {r.verdict.scheme_id: r for r in gate_all(verdicts, schemes, today=today)}
    return schemes, verdicts, results


def test_the_whole_welfare_arc(welfare_schemes_dir, sunita_profile, today):
    _, verdicts, _ = _run(welfare_schemes_dir, sunita_profile, today)
    assert {v.scheme_id: v.status for v in verdicts} == {
        "pm-kisan": Status.ELIGIBLE,
        "ignwps": Status.BLOCKED_ON_DOCUMENT,
        "sgnay": Status.BLOCKED_ON_DOCUMENT,
        "pmjay": Status.UNVERIFIABLE,
        "avvc": Status.NOT_ELIGIBLE,
    }


def test_positive_match_is_proven_from_her_land_record(
    welfare_schemes_dir, sunita_profile, today
):
    schemes, _, results = _run(welfare_schemes_dir, sunita_profile, today)
    verdict = results["pm-kisan"].verdict

    landholding = next(p for p in verdict.predicates if p.clause_id == "PMKISAN-C1")
    assert landholding.evaluation is Evaluation.TRUE
    assert landholding.evidence.document_id == "land_record_7_12"
    assert landholding.evidence.extracted_value == 0.8

    # Every exclusion resolved in her favour, each backed by her declaration.
    exclusions = [p for p in verdict.predicates if p.clause_id.startswith("PMKISAN-X")]
    assert len(exclusions) == 6
    for predicate in exclusions:
        assert predicate.evaluation is Evaluation.TRUE  # not excluded
        assert predicate.evidence is not None

    card = render_card(results["pm-kisan"], next(
        s for s in schemes if s.scheme_id == "pm-kisan"), today=today)
    assert card.lines[0] == "You are eligible for PM-KISAN."
    assert "Proven from your 7/12 land record." in card.lines


def test_stacking_groups_ignwps_and_sgnay(welfare_schemes_dir, sunita_profile, today):
    """They are one payment, not two.

    In Maharashtra a widow's Rs 1,500 is IGNWPS topped up *through* SGNAY. Listing two
    independent Rs 1,500 benefits would be wrong and a judge who knows the state would
    catch it (01-DEMO-CORPUS.md s2).
    """
    _, verdicts, _ = _run(welfare_schemes_dir, sunita_profile, today)
    by_id = {v.scheme_id: v for v in verdicts}

    assert by_id["ignwps"].stack_group_id == by_id["sgnay"].stack_group_id
    assert by_id["ignwps"].stack_group_id is not None
    # Nothing else is dragged into the group.
    assert by_id["pm-kisan"].stack_group_id is None
    assert by_id["pmjay"].stack_group_id is None
    # Stacking groups; it does not suppress. Both remain separately claimable.
    assert by_id["ignwps"].claimable is True
    assert by_id["sgnay"].claimable is True


def test_the_one_document_away_beat(welfare_schemes_dir, sunita_profile, today):
    """The BPL ration card, and an honest count.

    CHANGED IN THE DAY 8-9 HARDENING PASS. This test previously asserted
    bpl.unlocks == ["ignwps"] and income.unlocks == [], which encoded the aggregator
    under-claim flagged on day 7: SGNAY's means test is satisfiable by EITHER a BPL
    entry OR an income certificate, so each paper clears it alone, but the old rule
    only counted a document as unlocking when it was the sole entry in unlocking_docs.

    The numbers below are what the corpus actually implies. The demo line moves from
    "unlocks IGNWPS" to "unlocks 2 more schemes", which is a stronger beat AND the
    true one.
    """
    _, verdicts, _ = _run(welfare_schemes_dir, sunita_profile, today)

    options = {o.document_id: o for o in aggregate_unlocks(verdicts)}
    assert set(options) == {"bpl_ration_card", "income_certificate"}

    # A BPL entry satisfies IGNWPS outright and satisfies SGNAY's means test on its own.
    bpl = options["bpl_ration_card"]
    assert bpl.unlocks == ["ignwps", "sgnay"]
    assert bpl.contributes_to == []

    # An income certificate settles SGNAY only — IGNWPS requires the BPL status itself.
    income = options["income_certificate"]
    assert income.unlocks == ["sgnay"]
    assert income.contributes_to == []

    # Ranked by how many schemes each clears, so the BPL card leads.
    assert best_unlock(verdicts).document_id == "bpl_ration_card"
    assert best_unlock(verdicts).unlock_count == 2


def test_the_stale_threshold_is_quoted_not_reinterpreted(
    welfare_schemes_dir, sunita_profile, today
):
    """Judge Q&A Q5: we quote Rs 21,000 as written and never modernise it."""
    _, _, results = _run(welfare_schemes_dir, sunita_profile, today)
    clause = next(
        p for p in results["sgnay"].verdict.predicates if p.clause_id == "SGNAY-C3"
    )
    assert "Rs 21,000" in clause.clause_text
    assert clause.evaluation is Evaluation.UNKNOWN  # she has no income certificate
    assert clause.evidence is None


def test_the_refusal_and_the_not_eligible_beats_still_hold(
    welfare_schemes_dir, sunita_profile, today
):
    schemes, _, results = _run(welfare_schemes_dir, sunita_profile, today)
    by_id = {s.scheme_id: s for s in schemes}

    pmjay = render_card(results["pmjay"], by_id["pmjay"], today=today)
    assert pmjay.lines[0] == "I cannot confirm this one, and I will not guess."

    avvc = render_card(results["avvc"], by_id["avvc"], today=today)
    assert avvc.lines == [
        "Not this one, and here is exactly why.",
        "The rule says 70 and above. Your age is 60.",
        "You become eligible in 2036.",
    ]


def test_every_welfare_scheme_is_still_provisional(welfare_schemes_dir):
    """Standing rule. The reveal vertical gets no exemption."""
    schemes = load_corpus(welfare_schemes_dir)
    assert len(schemes) == 5
    for scheme in schemes:
        assert scheme.verification_status.value == "PROVISIONAL"
        for clause in scheme.clauses():
            assert "[VERIFY AT SOURCE]" in clause.clause_text
    assert load_corpus(welfare_schemes_dir, strict=True) == []


def test_no_welfare_card_hedges(welfare_schemes_dir, sunita_profile, today):
    from haqdaar.render.render import BANNED_PHRASES

    schemes, _, results = _run(welfare_schemes_dir, sunita_profile, today)
    by_id = {s.scheme_id: s for s in schemes}
    for scheme_id, result in results.items():
        text = render_card(result, by_id[scheme_id], today=today).text().lower()
        for phrase in BANNED_PHRASES:
            assert phrase not in text, scheme_id
        assert "{" not in text
