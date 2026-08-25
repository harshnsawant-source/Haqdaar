"""A+ golden tests: the filled form, the gap list, the reference, and the refusals.

Red test means no deploy. The exact filled fields and the exact gap list are pinned,
because "it filled the form" is a claim the demo makes on stage and a silently-changed
gap list would make that claim wrong without anyone noticing.
"""

from datetime import date

import pytest

from haqdaar.action.fill import (
    ActionRefused,
    FilledForm,
    fill_form,
    missing_documents,
)
from haqdaar.action.track import SIMULATED_PREFIX, submit, tracking_reference
from haqdaar.corpus.forms import Requirement, load_form_for
from haqdaar.corpus.loader import load_corpus
from haqdaar.eligibility.evaluate import evaluate_scheme
from haqdaar.eligibility.verdict import Status
from haqdaar.render.render import RenderError, render_action

SUBMITTED_ON = date(2026, 8, 22)


@pytest.fixture(scope="module")
def forms_dir(request):
    return request.config.rootpath.parent / "corpus" / "entrepreneur" / "forms"


@pytest.fixture
def standup(schemes_dir):
    return next(
        s for s in load_corpus(schemes_dir) if s.scheme_id == "stand-up-india"
    )


@pytest.fixture
def form(forms_dir):
    return load_form_for(forms_dir, "stand-up-india")


def test_filled_form_for_entrepreneur_01(form, standup, entrepreneur_profile):
    """Exactly what her documents prove, and nothing else."""
    verdict = evaluate_scheme(standup, entrepreneur_profile)
    assert verdict.status is Status.ELIGIBLE

    filled_form = fill_form(form, verdict, entrepreneur_profile)

    assert [(f.field_id, f.value, f.source_document) for f in filled_form.filled] == [
        ("applicant_social_category", "SC", "caste_certificate"),
        ("applicant_gender", "FEMALE", "aadhaar"),
        ("enterprise_venture_type", "GREENFIELD", "project_report"),
        ("enterprise_loan_amount_sought", 1500000, "project_report"),
    ]
    # Every filled value is traceable to a document. No value has any other origin.
    assert all(f.source_document for f in filled_form.filled)


def test_gap_list_is_exact(form, standup, entrepreneur_profile):
    """Everything her documents cannot prove is named, not guessed."""
    verdict = evaluate_scheme(standup, entrepreneur_profile)
    filled_form = fill_form(form, verdict, entrepreneur_profile)

    assert [g.field_id for g in filled_form.gaps] == [
        "applicant_name",
        "applicant_date_of_birth",
        "applicant_aadhaar_number",
        "applicant_address",
        "applicant_mobile",
        "enterprise_name",
        "enterprise_sector",
        "enterprise_project_cost",
        "bank_account_number",
        "bank_ifsc",
    ]
    assert filled_form.is_complete is False

    # Ranked by how many gaps each document closes, ties alphabetical.
    assert missing_documents(filled_form) == [
        "aadhaar",
        "project_report",
        "bank_passbook",
        "domicile_certificate",
    ]


def test_aadhaar_number_is_never_auto_filled(form, standup, entrepreneur_profile):
    """Haqdaar does not hold or transmit Aadhaar numbers.

    The field is deliberately unmapped, so it lands in the gap list for the citizen to
    write themselves rather than being carried around by our software.
    """
    field = next(f for f in form.fields() if f.field_id == "applicant_aadhaar_number")
    assert field.profile_field is None

    verdict = evaluate_scheme(standup, entrepreneur_profile)
    filled_form = fill_form(form, verdict, entrepreneur_profile)
    assert "applicant_aadhaar_number" in {g.field_id for g in filled_form.gaps}
    assert not any("aadhaar_number" in f.field_id for f in filled_form.filled)


def test_tracking_reference_is_deterministic_and_obviously_simulated(
    form, standup, entrepreneur_profile
):
    verdict = evaluate_scheme(standup, entrepreneur_profile)
    filled_form = fill_form(form, verdict, entrepreneur_profile)

    first = tracking_reference(filled_form, "entrepreneur-01", SUBMITTED_ON)
    second = tracking_reference(filled_form, "entrepreneur-01", SUBMITTED_ON)

    assert first == second, "a rehearsal must produce the same reference twice"
    assert first.startswith(f"{SIMULATED_PREFIX}-")
    assert first == "SIM-STANDUPIND-20260822-D1679F"

    # A different applicant gets a different reference.
    assert tracking_reference(filled_form, "someone-else", SUBMITTED_ON) != first


def test_rendered_action_carries_the_simulated_banner(
    form, standup, entrepreneur_profile
):
    verdict = evaluate_scheme(standup, entrepreneur_profile)
    filled_form = fill_form(form, verdict, entrepreneur_profile)
    receipt = submit(filled_form, "entrepreneur-01", SUBMITTED_ON)
    rendered = render_action(filled_form, receipt, standup)

    assert "SIMULATED." in rendered.banners[0]
    assert "SIMULATED FORM LAYOUT." in rendered.banners[1]
    # The banner leads. A citizen reads it before they read a filled field.
    assert rendered.text().startswith("SIMULATED.")
    assert receipt.reference in rendered.text()

    # Stand-Up India carries no approval group, so no approval caveat is emitted.
    assert not any("Filing does not mean approval" in line for line in rendered.lines)


def test_approval_pending_is_carried_into_the_action(schemes_dir, entrepreneur_profile, forms_dir):
    """NSFDC is eligible with an outstanding bank appraisal.

    Filing is still correct — eligibility is what entitles her to apply — but the
    receipt must never read as approval.
    """
    nsfdc = next(
        s for s in load_corpus(schemes_dir) if s.scheme_id == "nsfdc-term-loan"
    )
    verdict = evaluate_scheme(nsfdc, entrepreneur_profile)
    assert verdict.status is Status.ELIGIBLE

    # We have no NSFDC form; reuse the Stand-Up India layout only to prove the
    # approval caveat propagates, via a form whose scheme_id we override.
    form = load_form_for(forms_dir, "stand-up-india").model_copy(
        update={"scheme_id": "nsfdc-term-loan"}
    )
    filled_form = fill_form(form, verdict, entrepreneur_profile)
    assert filled_form.approval_pending_by == [
        "the concerned State Channelising Agency or Channelising Agency"
    ]

    rendered = render_action(
        filled_form, submit(filled_form, "entrepreneur-01", SUBMITTED_ON), nsfdc
    )
    assert any("Filing does not mean approval" in line for line in rendered.lines)


# --- the refusals -----------------------------------------------------------


def test_refuses_a_blocked_verdict(form, standup, entrepreneur_02_profile):
    """entrepreneur-02 is blocked on a caste certificate. No form gets filled."""
    verdict = evaluate_scheme(standup, entrepreneur_02_profile)
    assert verdict.status is Status.BLOCKED_ON_DOCUMENT

    with pytest.raises(ActionRefused, match="BLOCKED_ON_DOCUMENT"):
        fill_form(form, verdict, entrepreneur_02_profile)


def test_refuses_an_unverifiable_verdict(form, welfare_schemes_dir, sunita_profile):
    pmjay = next(
        s for s in load_corpus(welfare_schemes_dir) if s.scheme_id == "pmjay"
    )
    verdict = evaluate_scheme(pmjay, sunita_profile)
    assert verdict.status is Status.UNVERIFIABLE

    with pytest.raises(ActionRefused, match="UNVERIFIABLE"):
        fill_form(form.model_copy(update={"scheme_id": "pmjay"}), verdict, sunita_profile)


def test_refuses_a_not_eligible_verdict(form, welfare_schemes_dir, sunita_profile):
    avvc = next(s for s in load_corpus(welfare_schemes_dir) if s.scheme_id == "avvc")
    verdict = evaluate_scheme(avvc, sunita_profile)
    assert verdict.status is Status.NOT_ELIGIBLE

    with pytest.raises(ActionRefused, match="NOT_ELIGIBLE"):
        fill_form(form.model_copy(update={"scheme_id": "avvc"}), verdict, sunita_profile)


def test_refuses_a_form_for_a_different_scheme(form, welfare_schemes_dir, sunita_profile):
    avvc = next(s for s in load_corpus(welfare_schemes_dir) if s.scheme_id == "avvc")
    verdict = evaluate_scheme(avvc, sunita_profile)
    with pytest.raises(ActionRefused, match="is for stand-up-india"):
        fill_form(form, verdict, sunita_profile)


# --- the SIMULATED marker cannot be removed ---------------------------------


def test_simulated_flag_cannot_be_set_false(form, standup, entrepreneur_profile):
    """Not a convention. The type refuses."""
    verdict = evaluate_scheme(standup, entrepreneur_profile)
    filled_form = fill_form(form, verdict, entrepreneur_profile)
    assert filled_form.simulated is True

    with pytest.raises(Exception):
        FilledForm(
            form_id="x", scheme_id="y", title="z", simulated=False
        )
    with pytest.raises(Exception):
        filled_form.model_copy(update={"simulated": False}).model_validate(
            filled_form.model_dump() | {"simulated": False}
        )


def test_render_refuses_to_emit_without_the_banner(
    form, standup, entrepreneur_profile, monkeypatch
):
    """If a future edit drops the banner, rendering raises instead of shipping it."""
    from haqdaar.render import render as render_module

    verdict = evaluate_scheme(standup, entrepreneur_profile)
    filled_form = fill_form(form, verdict, entrepreneur_profile)
    receipt = submit(filled_form, "entrepreneur-01", SUBMITTED_ON)

    original = render_module.load_templates("en")
    sabotaged = dict(original)
    sabotaged["action.simulated_banner"] = "Your application has been filed."
    sabotaged["action.stand_in_banner"] = "A form."
    monkeypatch.setattr(render_module, "load_templates", lambda language="en": sabotaged)

    with pytest.raises(RenderError, match="lost its SIMULATED banner"):
        render_action(filled_form, receipt, standup)


# --- the stand-in form cannot masquerade as the official one ----------------


def test_stand_in_form_labels_all_carry_the_marker(form):
    assert form.is_stand_in is True
    for field in form.fields():
        assert "[VERIFY AT SOURCE]" in field.label


def test_stand_in_form_claims_no_requirements(form):
    """We have not read the official form, so we do not know what it requires."""
    for field in form.fields():
        assert field.requirement is Requirement.UNVERIFIED
