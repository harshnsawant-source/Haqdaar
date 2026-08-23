"""The second-language plumbing, and the guard against it leaking.

Marathi is wired through the same deterministic renderer as English — a language is a
template set, not a code path. What is NOT here is Marathi text: every value is a
placeholder until a native speaker fills it in. These tests hold that line in both
directions: the structure must be complete, and the placeholders must never reach a
citizen reading English.
"""

import pytest

from haqdaar.corpus.loader import load_corpus
from haqdaar.eligibility.evaluate import evaluate_corpus
from haqdaar.guard.gate import gate_all
from haqdaar.render.render import (
    BANNED_PHRASES,
    audit_templates,
    load_templates,
    render_card,
    render_outside_corpus,
)

PLACEHOLDER = "[NEEDS HUMAN TRANSLATION]"


def test_marathi_set_has_a_slot_for_every_english_one():
    """Structural parity. A missing key would raise mid-render, on stage."""
    en, mr = load_templates("en"), load_templates("mr")
    assert set(mr) == set(en)
    assert len(mr) == len(en)


def test_marathi_passes_the_same_build_time_audit_as_english():
    """T4 applies per language: no digits in prose, no hedging."""
    audit_templates("mr")


def test_every_marathi_value_is_still_a_placeholder():
    """When this starts failing, someone has begun translating. Update it then.

    It exists so nobody can quietly ship a machine translation: a real Marathi string
    without the marker will trip this, and the diff will show who wrote it.
    """
    mr = load_templates("mr")
    untranslated = [k for k, v in mr.items() if PLACEHOLDER not in v]
    assert untranslated == [], (
        f"{len(untranslated)} Marathi value(s) no longer carry the placeholder. If a "
        "human translated them, that is good news — confirm a native speaker did it, "
        "then narrow this test to the remaining keys."
    )


def test_marathi_keeps_every_slot_its_english_counterpart_has():
    """A dropped {slot} would render a sentence missing its fact."""
    import re

    slot = re.compile(r"\{([a-z_]+)\}")
    en, mr = load_templates("en"), load_templates("mr")
    for key, english in en.items():
        assert set(slot.findall(mr[key])) == set(slot.findall(english)), key


def test_a_marathi_card_renders_from_its_slots(welfare_schemes_dir, sunita_profile, today):
    """Proof the plumbing works: an mr card fills real values into placeholder prose."""
    schemes = load_corpus(welfare_schemes_dir)
    verdicts = evaluate_corpus(schemes, sunita_profile)
    by_id = {s.scheme_id: s for s in schemes}
    result = next(
        r for r in gate_all(verdicts, schemes, today=today) if r.verdict.scheme_id == "avvc"
    )

    card = render_card(result, by_id["avvc"], today=today, language="mr")
    text = card.text()

    assert PLACEHOLDER in text  # still untranslated, and says so
    assert "{" not in text  # but every slot resolved
    # The facts arrived through slots, exactly as in English.
    assert "70 and above" in text
    assert "60" in text
    assert "2036" in text


def test_marathi_outside_corpus_card_renders():
    card = render_outside_corpus(language="mr")
    assert PLACEHOLDER in card.text()
    assert "{" not in card.text()


# --- the placeholder must never reach an English reader ---------------------


def test_english_templates_contain_no_placeholder():
    assert not any(PLACEHOLDER in v for v in load_templates("en").values())


def test_no_english_render_leaks_a_placeholder(
    schemes_dir, welfare_schemes_dir, entrepreneur_profile, sunita_profile, today
):
    for directory, profile in (
        (schemes_dir, entrepreneur_profile),
        (welfare_schemes_dir, sunita_profile),
    ):
        schemes = load_corpus(directory)
        verdicts = evaluate_corpus(schemes, profile)
        by_id = {s.scheme_id: s for s in schemes}
        for result in gate_all(verdicts, schemes, today=today):
            card = render_card(
                result, by_id[result.verdict.scheme_id], today=today, language="en"
            )
            assert PLACEHOLDER not in card.text(), card.scheme_id


def test_marathi_placeholders_do_not_smuggle_in_a_banned_phrase():
    """The blocklist applies per language, not just to English."""
    joined = " ".join(load_templates("mr").values()).lower()
    for phrase in BANNED_PHRASES:
        assert phrase not in joined


def test_an_unknown_language_is_an_error_not_a_silent_fallback(
    welfare_schemes_dir, sunita_profile, today
):
    """Falling back to English would show a citizen a language they may not read."""
    from haqdaar.render.render import RenderError

    with pytest.raises(RenderError, match="no template set"):
        load_templates("hi")


# --- intake questions carry the same translation discipline ------------------


def test_every_intake_string_has_a_marathi_placeholder(corpus_dir):
    """Intake prompts live in corpus/intake.yaml, not the template set.

    They are questions, not verdict sentences — no claim about anyone — so the digit
    ban that governs template prose would be wrong for them ("How much land, in
    hectares?" is fine; a rupee figure in a prompt is fine). But the translation
    discipline is identical: an mr value for every string, placeholdered until a
    native speaker fills it in, never machine translated.
    """
    from haqdaar.profile.intake import load_intake

    spec = load_intake(corpus_dir / "intake.yaml")

    strings: list[tuple[str, dict]] = []
    for section in spec.sections:
        strings.append((section.section_id, section.title))
        for question in section.questions:
            strings.append((question.question_id, question.prompt))
            for option in question.options:
                strings.append((f"{question.question_id}:{option.value}", option.label))

    assert strings
    for name, mapping in strings:
        assert "en" in mapping, name
        assert "mr" in mapping, f"{name} has no Marathi value"
        assert PLACEHOLDER in mapping["mr"], f"{name} Marathi is not placeholdered"
        assert PLACEHOLDER not in mapping["en"], f"{name} English carries a placeholder"
