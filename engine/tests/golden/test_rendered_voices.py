"""All four citizen-facing voices, rendered from real corpus data.

Rendering is deterministic slot-fill, so these assert exact strings — no snapshot
fuzz, no temperature. Guard doc s4 defines the three refusal voices; ELIGIBLE-with-
proof is the fourth.
"""

from haqdaar.corpus.loader import load_corpus
from haqdaar.eligibility.aggregate import best_unlock
from haqdaar.eligibility.evaluate import evaluate_corpus
from haqdaar.eligibility.verdict import Status
from haqdaar.guard.gate import gate_all
from haqdaar.render.render import BANNED_PHRASES, render_card


def cards(schemes_path, profile, today, *, use_unlock: bool = True):
    schemes = load_corpus(schemes_path)
    verdicts = evaluate_corpus(schemes, profile)
    unlock = best_unlock(verdicts) if use_unlock else None
    by_id = {s.scheme_id: s for s in schemes}
    return {
        r.verdict.scheme_id: render_card(
            r, by_id[r.verdict.scheme_id], today=today, unlock=unlock
        )
        for r in gate_all(verdicts, schemes, today=today)
    }


def test_voice_eligible_with_proof(schemes_dir, entrepreneur_profile, today):
    card = cards(schemes_dir, entrepreneur_profile, today)["stand-up-india"]
    assert card.status is Status.ELIGIBLE
    assert card.lines[:3] == [
        "You are eligible for Stand-Up India.",
        "Here is the rule that entitles you:",
        "[VERIFY AT SOURCE] The applicant belongs to a Scheduled Caste or Scheduled "
        "Tribe.",
    ]
    # Each proven clause is followed by the document that proves it.
    assert "Proven from your caste certificate." in card.lines
    assert "Proven from your Aadhaar." in card.lines
    assert "Source: https://www.standupmitra.in/" in card.lines


def test_voice_blocked_on_document(schemes_dir, entrepreneur_02_profile, today):
    card = cards(schemes_dir, entrepreneur_02_profile, today)["stand-up-india"]
    assert card.status is Status.BLOCKED_ON_DOCUMENT
    assert card.lines[0] == "You are one document away."
    assert card.lines[1] == (
        "Bring your caste certificate and this unlocks 2 more schemes."
    )
    assert card.lines[2].startswith("The rule this settles: [VERIFY AT SOURCE]")


def test_blocked_names_the_scheme_when_it_unlocks_only_that_one(
    schemes_dir, entrepreneur_02_profile, today
):
    """Without an aggregator count, the card must not invent one."""
    card = cards(schemes_dir, entrepreneur_02_profile, today, use_unlock=False)[
        "stand-up-india"
    ]
    assert card.lines[1] == (
        "Bring your caste certificate and this unlocks Stand-Up India."
    )


def test_voice_unverifiable_names_every_criterion_it_cannot_settle(
    welfare_schemes_dir, sunita_profile, today
):
    card = cards(welfare_schemes_dir, sunita_profile, today)["pmjay"]
    assert card.status is Status.UNVERIFIABLE
    assert card.lines[0] == "I cannot confirm this one, and I will not guess."
    assert card.lines[1] == (
        "This scheme's rule depends on records I cannot check, and nothing you have "
        "shown me can prove it."
    )
    assert card.lines[2].startswith("The rule I cannot settle: [VERIFY AT SOURCE]")
    # Quoting one of six without saying so would imply it is the only one.
    assert card.lines[3] == (
        "The same records settle 5 further criteria in this scheme, and I cannot check "
        "any of them."
    )


def test_voice_not_eligible_states_the_bound_and_the_year(
    welfare_schemes_dir, sunita_profile, today
):
    """The brief's own beat: she is 60, the rule is 70+, she qualifies in 2036."""
    card = cards(welfare_schemes_dir, sunita_profile, today)["avvc"]
    assert card.status is Status.NOT_ELIGIBLE
    assert card.lines == [
        "Not this one, and here is exactly why.",
        "The rule says 70 and above. Your age is 60.",
        "You become eligible in 2036.",
    ]


def test_a_rule_amended_before_we_read_it_is_not_stale(
    welfare_schemes_dir, sunita_profile, today
):
    """AVVC changed in Oct 2024 and we transcribed it in Aug 2026.

    The amendment predates our reading, so our copy already reflects it and no banner
    is warranted. Flagging here would train the room to ignore the banner, which is
    the thing that makes T5 worth having at all. Staleness in both directions is
    covered exhaustively in tests/unit/test_t5_stale_rule.py.
    """
    card = cards(welfare_schemes_dir, sunita_profile, today)["avvc"]
    assert card.status is Status.NOT_ELIGIBLE
    assert not any("last checked" in b for b in card.banners)
    assert not any("records a change" in b for b in card.banners)


def test_provisional_corpus_always_says_so(schemes_dir, entrepreneur_profile, today):
    for card in cards(schemes_dir, entrepreneur_profile, today).values():
        assert any("not yet been verified" in b for b in card.banners)


def test_no_rendered_card_hedges(
    schemes_dir, welfare_schemes_dir, entrepreneur_profile, entrepreneur_02_profile,
    sunita_profile, today,
):
    """The blocklist, asserted across every card the demo can produce."""
    everything = [
        *cards(schemes_dir, entrepreneur_profile, today).values(),
        *cards(schemes_dir, entrepreneur_02_profile, today).values(),
        *cards(welfare_schemes_dir, sunita_profile, today).values(),
    ]
    # Every card the demo can produce, both verticals. Deliberately not a fixed
    # count: adding a scheme must widen this test's coverage, never break it.
    assert len(everything) >= 6
    assert {c.status for c in everything} == {
        Status.ELIGIBLE,
        Status.NOT_ELIGIBLE,
        Status.BLOCKED_ON_DOCUMENT,
        Status.UNVERIFIABLE,
    }
    for card in everything:
        lowered = card.text().lower()
        for phrase in BANNED_PHRASES:
            assert phrase not in lowered, f"{card.scheme_id}: {phrase!r}"
        assert "{" not in card.text()


def test_the_unlock_count_always_matches_the_document_it_names(
    welfare_schemes_dir, sunita_profile, today
):
    """Regression: the count and the document must come from the same option.

    Found during the day 8-9 hardening pass. The renderer paired each card's own first
    unlocking document with the GLOBALLY best document's count, so SGNAY rendered
    "Bring your income certificate and this unlocks 2 more schemes" — while an income
    certificate clears exactly one. Over-claiming is the one direction of error that is
    disqualifying, so this asserts the pairing on every blocked card in both verticals.
    """
    import re

    from haqdaar.eligibility.aggregate import aggregate_unlocks, best_unlock
    from haqdaar.eligibility.evaluate import evaluate_corpus
    from haqdaar.guard.gate import gate_all

    schemes = load_corpus(welfare_schemes_dir)
    verdicts = evaluate_corpus(schemes, sunita_profile)
    unlock = best_unlock(verdicts)
    by_document = {o.document_id: o for o in aggregate_unlocks(verdicts)}
    by_id = {s.scheme_id: s for s in schemes}

    for result in gate_all(verdicts, schemes, today=today):
        if result.verdict.status is not Status.BLOCKED_ON_DOCUMENT:
            continue
        card = render_card(
            result, by_id[result.verdict.scheme_id], today=today, unlock=unlock
        )
        line = card.lines[1]
        match = re.search(r"Bring your (.+?) and this unlocks (\d+) more", line)
        if match is None:
            continue  # the single-scheme phrasing names no count at all
        from haqdaar.render.labels import document_label

        named_label, claimed = match.group(1), int(match.group(2))
        # Map the rendered name back to the document it names, so the assertion
        # survives the display layer changing how a document is written.
        named_document = next(
            d for d in by_document if document_label(d) == named_label
        )
        actual = by_document[named_document].unlock_count
        assert claimed == actual, (
            f"{card.scheme_id}: claims {named_document} unlocks {claimed}, "
            f"but it unlocks {actual}"
        )
