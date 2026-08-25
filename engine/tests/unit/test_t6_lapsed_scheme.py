"""T6 — the scheme's own door is shut, whatever the rules say about this citizen.

Found by verifying the corpus against the official source rather than by unit testing:
the Department of Financial Services' own page states the Stand-Up India sanctioned
period runs "upto 31.03.2025", which is well before demo day. The engine had no way to
express that. T5 asks whether OUR READING of a rule is stale; T6 asks whether the
SCHEME is still open. They are independent facts and both can be true at once.

The design rule under test throughout: a lapse is reported BESIDE eligibility, never
instead of it, exactly as a discretionary approval is. A citizen can be provably
eligible under the published rules of a scheme that has closed, and collapsing those
two facts into NOT_ELIGIBLE would repeat the mistake the approval split exists to
prevent.
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
from haqdaar.eligibility.verdict import (
    Evaluation,
    GroupResult,
    SchemeWindow,
    Status,
    derive_window,
)
from haqdaar.guard.gate import gate
from haqdaar.guard.triggers import TriggerId, t6_lapsed_scheme
from haqdaar.render.render import render_card

TODAY = date(2026, 8, 26)


def scheme(
    *,
    valid_from: date | None = None,
    valid_until: date | None = None,
    validity_text: str | None = None,
) -> Scheme:
    return Scheme(
        scheme_id="synthetic",
        name="Synthetic",
        authority="test",
        benefit="test",
        source_url="https://example.invalid/",
        retrieved_on=TODAY,
        valid_from=valid_from,
        valid_until=valid_until,
        validity_text=validity_text,
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


def eligible_verdict():
    return verdict(
        [predicate("C", "g", Evaluation.TRUE, verifiable_from=["doc"])],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.TRUE)],
        Status.ELIGIBLE,
    )


# --- derive_window ----------------------------------------------------------


def test_a_scheme_with_no_declared_window_reports_nothing():
    """Not knowing a scheme is open is different from knowing it is.

    The engine must not manufacture the difference. Every scheme that predates T6
    renders exactly as it did before.
    """
    assert derive_window(scheme(), today=TODAY) is None


def test_a_scheme_whose_period_has_ended_is_lapsed():
    window = derive_window(scheme(valid_until=date(2025, 3, 31)), today=TODAY)
    assert window is not None
    assert window.state is SchemeWindow.LAPSED
    assert window.valid_until == date(2025, 3, 31)


def test_the_last_day_of_the_window_is_still_open():
    """Inclusive, and deliberately so. A scheme closing today is open today."""
    window = derive_window(scheme(valid_until=TODAY), today=TODAY)
    assert window.state is SchemeWindow.OPEN


def test_a_scheme_that_has_not_started_is_not_yet_open():
    window = derive_window(scheme(valid_from=date(2026, 12, 1)), today=TODAY)
    assert window.state is SchemeWindow.NOT_YET_OPEN


def test_a_currently_running_scheme_is_open():
    window = derive_window(
        scheme(valid_from=date(2020, 1, 1), valid_until=date(2030, 1, 1)), today=TODAY
    )
    assert window.state is SchemeWindow.OPEN


def test_an_open_ended_scheme_with_only_a_start_date_is_open():
    window = derive_window(scheme(valid_from=date(2020, 1, 1)), today=TODAY)
    assert window.state is SchemeWindow.OPEN


# --- the trigger ------------------------------------------------------------


def test_the_trigger_is_silent_on_an_open_scheme():
    assert t6_lapsed_scheme(scheme(valid_until=date(2030, 1, 1)), today=TODAY) is None


def test_the_trigger_is_silent_when_no_window_is_declared():
    assert t6_lapsed_scheme(scheme(), today=TODAY) is None


def test_the_trigger_carries_the_dates_for_the_slots():
    finding = t6_lapsed_scheme(scheme(valid_until=date(2025, 3, 31)), today=TODAY)
    assert finding is not None
    assert finding.trigger is TriggerId.T6_LAPSED_SCHEME
    assert finding.valid_until == "2025-03-31"


def test_t6_is_independent_of_t5():
    """A rule transcribed this morning can belong to a scheme that closed last year.

    This is the exact Stand-Up India shape and the reason T6 could not be folded into
    T5: `retrieved_on` is today, so T5 is correctly silent, and the scheme is still
    shut.
    """
    from haqdaar.guard.triggers import t5_stale_rule

    lapsed_but_freshly_read = scheme(valid_until=date(2025, 3, 31))
    assert t5_stale_rule(lapsed_but_freshly_read, today=TODAY) is None
    assert t6_lapsed_scheme(lapsed_but_freshly_read, today=TODAY) is not None


# --- the gate ---------------------------------------------------------------


def test_the_gate_attaches_the_window_to_the_verdict():
    result = gate(
        eligible_verdict(), scheme(valid_until=date(2025, 3, 31)), today=TODAY
    )
    assert result.verdict.window is not None
    assert result.verdict.window.state is SchemeWindow.LAPSED


def test_a_lapse_never_suppresses_the_eligibility_it_could_prove():
    """The whole design decision, asserted.

    She stays ELIGIBLE. The proof survives, because a successor scheme normally
    carries the rules forward and she will want to know she meets them.
    """
    result = gate(
        eligible_verdict(), scheme(valid_until=date(2025, 3, 31)), today=TODAY
    )
    assert result.verdict.status is Status.ELIGIBLE
    assert result.findings_for(TriggerId.T6_LAPSED_SCHEME)


# --- rendering --------------------------------------------------------------


def test_the_closed_door_leads_the_card():
    """A citizen must read "closed" before she reads "you are eligible".

    Buried under a proof of eligibility, a lapse sends someone to a shut counter,
    which is the same harm the Guard exists to prevent arriving from another
    direction.
    """
    scheme_ = scheme(
        valid_until=date(2025, 3, 31),
        validity_text="the SUPI Scheme is upto 31.03.2025",
    )
    card = render_card(gate(eligible_verdict(), scheme_, today=TODAY), scheme_, today=TODAY)

    assert card.window_lines
    assert card.text().splitlines()[0] == card.window_lines[0]
    assert "closed" in card.window_lines[0].lower()


def test_the_lapse_quotes_the_source_that_states_it():
    """A closure is cited exactly like an eligibility clause is."""
    quote = "the SUPI Scheme is upto 31.03.2025"
    scheme_ = scheme(valid_until=date(2025, 3, 31), validity_text=quote)
    card = render_card(gate(eligible_verdict(), scheme_, today=TODAY), scheme_, today=TODAY)

    assert any(quote in line for line in card.window_lines)


def test_the_date_reaches_the_citizen_through_a_slot_not_prose():
    scheme_ = scheme(valid_until=date(2025, 3, 31))
    card = render_card(gate(eligible_verdict(), scheme_, today=TODAY), scheme_, today=TODAY)
    assert any("2025-03-31" in line for line in card.window_lines)


def test_an_open_scheme_renders_no_window_lines():
    scheme_ = scheme(valid_until=date(2030, 1, 1))
    card = render_card(gate(eligible_verdict(), scheme_, today=TODAY), scheme_, today=TODAY)
    assert card.window_lines == []


def test_a_scheme_without_a_window_renders_exactly_as_before():
    """The regression guard for all eight existing schemes."""
    scheme_ = scheme()
    card = render_card(gate(eligible_verdict(), scheme_, today=TODAY), scheme_, today=TODAY)
    assert card.window_lines == []
    assert card.text() == "\n".join([*card.lines, *card.approval_lines, *card.banners])


def test_a_not_yet_open_scheme_says_when_it_opens():
    scheme_ = scheme(valid_from=date(2026, 12, 1))
    card = render_card(gate(eligible_verdict(), scheme_, today=TODAY), scheme_, today=TODAY)
    assert any("2026-12-01" in line for line in card.window_lines)


# --- the schema refuses incoherent windows ----------------------------------


def test_a_window_that_ends_before_it_starts_is_rejected():
    with pytest.raises(ValueError, match="precedes"):
        scheme(valid_from=date(2026, 1, 1), valid_until=date(2025, 1, 1))


def test_quoting_a_window_the_scheme_does_not_declare_is_rejected():
    """Stops a validity quote drifting away from the dates it is supposed to prove."""
    with pytest.raises(ValueError, match="does not declare"):
        scheme(validity_text="upto 31.03.2025")


# --- the action layer refuses to file into a shut scheme --------------------


def test_filing_is_refused_for_a_lapsed_scheme():
    """The UI hides the button; this is why that is not the guarantee.

    A direct API call must be refused too, or "we never file into a closed scheme"
    is a statement about our frontend rather than about the engine.
    """
    from haqdaar.action.fill import ActionRefused, fill_form
    from haqdaar.corpus.forms import FormDefinition, FormField, FormSection
    from haqdaar.profile.schema import CitizenProfile

    scheme_ = scheme(valid_until=date(2025, 3, 31))
    gated = gate(eligible_verdict(), scheme_, today=TODAY).verdict
    form = FormDefinition(
        form_id="synthetic-form",
        scheme_id="synthetic",
        title="Synthetic",
        verification_status=VerificationStatus.PROVISIONAL,
        verify_note="synthetic",
        retrieved_on=TODAY,
        is_stand_in=True,
        sections=[
            FormSection(
                section_id="s",
                title="S",
                fields=[FormField(field_id="f", label="[VERIFY AT SOURCE] F")],
            )
        ],
    )

    with pytest.raises(ActionRefused, match="LAPSED"):
        fill_form(form, gated, CitizenProfile(profile_id="synthetic", fields={}))


def test_filing_is_allowed_when_the_scheme_declares_no_window():
    """The regression guard: eight existing schemes must still be fileable."""
    from haqdaar.action.fill import fill_form
    from haqdaar.corpus.forms import FormDefinition, FormField, FormSection
    from haqdaar.profile.schema import CitizenProfile

    scheme_ = scheme()
    gated = gate(eligible_verdict(), scheme_, today=TODAY).verdict
    form = FormDefinition(
        form_id="synthetic-form",
        scheme_id="synthetic",
        title="Synthetic",
        verification_status=VerificationStatus.PROVISIONAL,
        verify_note="synthetic",
        retrieved_on=TODAY,
        is_stand_in=True,
        sections=[
            FormSection(
                section_id="s",
                title="S",
                fields=[FormField(field_id="f", label="[VERIFY AT SOURCE] F")],
            )
        ],
    )

    filled = fill_form(form, gated, CitizenProfile(profile_id="synthetic", fields={}))
    assert filled.scheme_id == "synthetic"
