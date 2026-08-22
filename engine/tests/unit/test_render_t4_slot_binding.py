"""T4 — the anti-hallucination net, in both halves.

Not an NLI check. Build time: no template carries a factual claim outside a slot.
Runtime: every slot resolves from the verdict, and clause text matches verbatim.
An unbound or orphan slot voids the whole response.
"""

import pytest
from _helpers import predicate, verdict

from haqdaar.corpus.schema import Satisfy
from haqdaar.eligibility.verdict import Evaluation, GroupResult, Status
from haqdaar.guard.gate import unchecked
from haqdaar.render import render as render_module
from haqdaar.render.render import (
    BANNED_PHRASES,
    RenderError,
    _fill,
    audit_templates,
    load_templates,
    render_outside_corpus,
)


# --- build time -------------------------------------------------------------


def test_shipped_templates_pass_the_build_time_audit():
    audit_templates("en")


def test_every_template_is_reachable_and_non_empty():
    templates = load_templates("en")
    assert templates
    assert all(v.strip() for v in templates.values())


def test_a_literal_number_in_a_template_is_rejected(monkeypatch):
    """A number in prose is an unbound fact — the exact hallucination shape."""
    monkeypatch.setattr(
        render_module, "load_templates", lambda language="en": {"x": "You are 60."}
    )
    with pytest.raises(RenderError, match="literal number outside a slot"):
        audit_templates("en")


def test_a_number_inside_a_slot_name_is_fine(monkeypatch):
    monkeypatch.setattr(
        render_module,
        "load_templates",
        lambda language="en": {"x": "You become eligible in {year}."},
    )
    audit_templates("en")


@pytest.mark.parametrize("phrase", BANNED_PHRASES)
def test_banned_phrases_are_rejected_at_build_time(monkeypatch, phrase):
    monkeypatch.setattr(
        render_module,
        "load_templates",
        lambda language="en": {"x": f"Well, {phrase} for this scheme."},
    )
    with pytest.raises(RenderError, match="banned phrase"):
        audit_templates("en")


def test_no_shipped_template_contains_a_banned_phrase():
    joined = " ".join(load_templates("en").values()).lower()
    for phrase in BANNED_PHRASES:
        assert phrase not in joined


# --- runtime ----------------------------------------------------------------


def test_unbound_slot_voids_the_response():
    with pytest.raises(RenderError, match="unbound"):
        _fill("k", {"k": "Apply at {filing_office}."}, {}, set())


def test_empty_slot_voids_the_response():
    """Rendering "Apply at ." is worse than refusing to render."""
    with pytest.raises(RenderError, match="resolved empty"):
        _fill("k", {"k": "Apply at {office}."}, {"office": ""}, set())


def test_orphan_clause_text_voids_the_response():
    """Clause text that no predicate carries verbatim cannot be shown as proof."""
    with pytest.raises(RenderError, match="does not match any predicate"):
        _fill(
            "k",
            {"k": "The rule: {clause_text}"},
            {"clause_text": "A rule nobody sourced."},
            {"[VERIFY AT SOURCE] The real one."},
        )


def test_clause_text_matching_verbatim_renders():
    text = _fill(
        "k",
        {"k": "The rule: {clause_text}"},
        {"clause_text": "[VERIFY AT SOURCE] The real one."},
        {"[VERIFY AT SOURCE] The real one."},
    )
    assert text == "The rule: [VERIFY AT SOURCE] The real one."


def test_a_banned_phrase_arriving_through_a_slot_is_still_caught():
    """The blocklist runs on rendered output, not just on templates.

    A clause quoted from the corpus could itself contain a hedge; the check has to be
    on what the citizen actually reads.
    """
    with pytest.raises(RenderError, match="banned phrase"):
        _fill(
            "k",
            {"k": "The rule: {clause_text}"},
            {"clause_text": "You may qualify if the officer agrees."},
            {"You may qualify if the officer agrees."},
        )


def test_missing_template_key_voids_the_response():
    with pytest.raises(RenderError, match="no template"):
        _fill("nope", {}, {}, set())


def test_unknown_language_is_an_error_not_a_fallback():
    """Silently falling back to English would show a citizen a language they may not
    read, while looking like it worked."""
    with pytest.raises(RenderError, match="no template set"):
        load_templates("mr-nonexistent")


def test_outside_corpus_card_binds_no_slots():
    """T3 names nothing it cannot show, so it needs no verdict at all."""
    card = render_outside_corpus()
    assert card.scheme_id == ""
    assert card.status is Status.UNVERIFIABLE
    assert "{" not in card.text()


def test_no_rendered_card_ever_contains_an_unfilled_slot():
    v = verdict(
        [predicate("C", "g", Evaluation.UNKNOWN)],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.UNVERIFIABLE,
    )
    assert "{" not in unchecked(v).verdict.scheme_id
