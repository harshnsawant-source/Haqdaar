"""The two rehearsed refusals, pinned. Red test means no deploy.

Guard doc s5: pick one query, rehearse it, and make it a fixture so a Sept 1 refactor
cannot break it. These assert exact status and the exact predicate set, then assert the
rendered English, because rendering is deterministic slot-fill and can be asserted
directly rather than snapshotted for fuzz.

DEVIATION FROM THE BRIEFED QUERY, on purpose
--------------------------------------------
The primary refusal is briefed as "Will my Stand-Up India loan be approved?" Our
provisional Stand-Up India YAML carries no appraisal clause, because the addendum does
not state one and nobody has read the official page — inventing one to make the demo
land is the exact failure this project exists to avoid. Guard doc s5 offers "(or the
NSFDC sanction question)" as the alternative, so the fixture uses NSFDC, which really
does carry a discretionary sanction clause. If the content lane later verifies an
appraisal condition for Stand-Up India, re-point this fixture.
"""

import pytest

from haqdaar.corpus.loader import load_corpus
from haqdaar.eligibility.aggregate import aggregate_unlocks
from haqdaar.eligibility.evaluate import evaluate_corpus
from haqdaar.eligibility.verdict import ApprovalStatus, Evaluation, Status
from haqdaar.guard.gate import gate_all
from haqdaar.guard.triggers import Scope, TriggerId, t3_no_retrieval_support
from haqdaar.render.render import render_card, render_outside_corpus
from haqdaar.retrieval.route import route


# --- PRIMARY: the entrepreneur approval refusal -----------------------------


#: Verbatim from nsfdc.nic.in/how-to-apply-2 via the corpus, read 2026-08-26.
DECIDER = "the concerned State Channelising Agency or Channelising Agency"


def test_primary_refusal_approval_is_not_eligibility(
    schemes_dir, entrepreneur_profile, today
):
    """"Will my NSFDC loan be sanctioned?"

    She is eligible, with proof. Whether the bank sanctions it is the bank's decision.
    The engine says both, and never lets the second erase the first.
    """
    schemes = load_corpus(schemes_dir)
    routed = route("Will my NSFDC term loan be sanctioned?", schemes)
    assert "nsfdc-term-loan" in routed.scheme_ids
    assert t3_no_retrieval_support(routed) is None

    verdicts = evaluate_corpus(schemes, entrepreneur_profile)
    results = {r.verdict.scheme_id: r for r in gate_all(verdicts, schemes, today=today)}
    result = results["nsfdc-term-loan"]
    verdict = result.verdict

    # Eligibility resolves, with evidence, and is NOT suppressed by the appraisal.
    assert verdict.status is Status.ELIGIBLE
    by_id = {p.clause_id: p for p in verdict.predicates}
    assert set(by_id) == {"NSF-C1", "NSF-C2", "NSF-C3"}
    assert by_id["NSF-C1"].evaluation is Evaluation.TRUE
    assert by_id["NSF-C1"].evidence.document_id == "caste_certificate"

    # The refusal is scoped to approval.
    assert by_id["NSF-C3"].evaluation is Evaluation.UNKNOWN
    assert by_id["NSF-C3"].evidence is None
    assert verdict.approval.status is ApprovalStatus.UNVERIFIABLE
    assert verdict.approval.deciders == [DECIDER]
    assert [(f.trigger, f.scope) for f in result.findings] == [
        (TriggerId.T1_UNSUPPORTED_PREDICATE, Scope.APPROVAL)
    ]

    scheme = next(s for s in schemes if s.scheme_id == "nsfdc-term-loan")
    card = render_card(result, scheme, today=today)

    assert card.status is Status.ELIGIBLE
    assert card.lines[0] == "You are eligible for NSFDC Term Loan."
    assert any("must belong to the Scheduled Caste" in line for line in card.lines)
    assert "Proven from your caste certificate." in card.lines

    # The approval refusal renders separately, using decided_by as the noun.
    assert card.approval_lines == [
        "Whether it is approved is not mine to promise.",
        f"That is decided by {DECIDER}, and no document you hold determines it.",
        "The condition: verification of eligibility criteria shall be the sole "
        "responsibility of the concerned SCAs/CAs",
    ]
    # Verified corpus: the unverified banner is correctly absent, and nothing on the
    # card carries the unread marker.
    assert not any("not yet been verified" in b for b in card.banners)
    assert "[VERIFY AT SOURCE]" not in card.text()


# --- REVEAL: the welfare SECC-2011 refusal ----------------------------------


def test_reveal_refusal_pmjay_secc_2011(welfare_schemes_dir, sunita_profile, today):
    """"Mala Ayushman Bharat cha labh milel ka?"

    Every deprivation criterion is keyed to SECC 2011, which Sunita cannot obtain. She
    plausibly satisfies D3 — and plausibly is exactly what the engine refuses to state.
    """
    schemes = load_corpus(welfare_schemes_dir)
    routed = route("Will I get the benefit of Ayushman Bharat?", schemes)
    # Both Ayushman schemes match, and PM-JAY ranks first. That is correct, not noise:
    # Ayushman Vay Vandana sits under AB PM-JAY, so the question genuinely touches
    # both. On stage it means one query produces the refusal AND the not-eligible
    # beat side by side.
    assert routed.scheme_ids[0] == "pmjay"
    assert set(routed.scheme_ids) == {"pmjay", "avvc"}
    assert t3_no_retrieval_support(routed) is None

    verdicts = evaluate_corpus(schemes, sunita_profile)
    results = {r.verdict.scheme_id: r for r in gate_all(verdicts, schemes, today=today)}
    result = results["pmjay"]
    verdict = result.verdict

    assert verdict.scheme_id == "pmjay"
    assert verdict.status is Status.UNVERIFIABLE

    # The exact predicate set: D1-D5 and D7, with D6 absent as published.
    assert [p.clause_id for p in verdict.predicates] == [
        "PMJAY-D1",
        "PMJAY-D2",
        "PMJAY-D3",
        "PMJAY-D4",
        "PMJAY-D5",
        "PMJAY-D7",
    ]
    # Every one permanently UNKNOWN, none with evidence, none fetchable.
    for predicate in verdict.predicates:
        assert predicate.evaluation is Evaluation.UNKNOWN
        assert predicate.evidence is None
        assert predicate.verifiable_from == []
        assert predicate.is_settleable is False

    # Nothing to send her to fetch. This is a refusal, not a blocked document.
    assert verdict.unlocking_docs == []
    # Other welfare schemes ARE merely blocked (IGNWPS on a BPL card), so the vertical
    # does produce an unlock beat — but PM-JAY must never appear in it. A refusal that
    # leaked into "one document away" would send her for a paper that cannot help.
    for option in aggregate_unlocks(verdicts):
        assert "pmjay" not in option.unlocks
        assert "pmjay" not in option.contributes_to
    assert [(f.trigger, f.scope) for f in result.findings] == [
        (TriggerId.T1_UNSUPPORTED_PREDICATE, Scope.ELIGIBILITY)
    ]

    scheme = next(s for s in schemes if s.scheme_id == "pmjay")
    card = render_card(result, scheme, today=today)
    assert card.lines[0] == "I cannot confirm this one, and I will not guess."
    assert card.lines[1] == (
        "This scheme's rule depends on records I cannot check, and nothing you have "
        "shown me can prove it."
    )
    # The rule it cannot settle is quoted verbatim from the corpus.
    # Verbatim from PIB PRID 1738169 since the 2026-08-26 verification; the
    # criteria now reach the citizen with their official D-numbers attached.
    assert card.lines[2].startswith("The rule I cannot settle: D1:")
    assert "kucha walls" in card.lines[2]
    assert card.approval_lines == []


# --- BACKUP: out of corpus --------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "How much tax do I owe this year?",
        "What is the weather in Pune tomorrow?",
        "Who won the cricket match?",
    ],
)
def test_backup_refusal_outside_corpus(schemes_dir, query):
    """T3. The pocket answer to "what if we ask it something random"."""
    schemes = load_corpus(schemes_dir)
    routed = route(query, schemes)
    assert routed.outside_corpus, f"{query!r} scored {routed.top_score}"

    finding = t3_no_retrieval_support(routed)
    assert finding is not None
    assert finding.trigger is TriggerId.T3_NO_RETRIEVAL_SUPPORT

    card = render_outside_corpus()
    assert card.status is Status.UNVERIFIABLE
    assert card.text() == (
        "I cannot confirm this one, and I will not guess.\n"
        "That is outside what I have rules for. I only answer where I can show you "
        "the official clause."
    )
