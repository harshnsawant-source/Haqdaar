"""The second and third languages, and the guards around them.

Marathi and Hindi run through the same deterministic renderer as English — a language
is a template set, not a code path.

WHAT CHANGED ON 2026-08-26
--------------------------
These used to assert that every Marathi value was still a [NEEDS HUMAN TRANSLATION]
placeholder, which was the right test while nobody had translated anything. Both
languages are now drafted, so that test would fail by design and has been replaced.

The discipline it protected is unchanged and now runs the other way: a translation must
be STRUCTURALLY sound (same keys, same slots, no digits, no hedging) before it can ship,
because the renderer fills real facts into it and a dropped slot is a sentence missing
its number. What no test can check is whether the Marathi is GOOD Marathi. That is a
human review, tracked in docs/TRANSLATION-REVIEW.md, and until it is signed off the
files say so in their headers.
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

#: Every language the product renders. Adding one here makes every test below cover it.
TRANSLATED = ("mr", "hi")


@pytest.mark.parametrize("lang", TRANSLATED)
def test_every_language_has_a_slot_for_every_english_one(lang):
    """Structural parity. A missing key would raise mid-render, on stage."""
    en, other = load_templates("en"), load_templates(lang)
    assert set(other) == set(en)
    assert len(other) == len(en)


@pytest.mark.parametrize("lang", TRANSLATED)
def test_every_language_passes_the_same_build_time_audit_as_english(lang):
    """T4 applies per language: no digits in prose, no hedging.

    Devanagari numerals matter here. `\d` matches ० १ २ exactly as it matches 0 1 2,
    so a translator who writes a year in Devanagari trips the same audit an English
    one would. That is the intended behaviour: every number reaches a citizen through
    a slot bound to a predicate, in every script.
    """
    audit_templates(lang)


@pytest.mark.parametrize("lang", TRANSLATED)
def test_no_value_is_left_as_a_placeholder(lang):
    """The inverse of the test this replaces.

    Both languages were drafted on 2026-08-26, so a remaining placeholder now means a
    string was ADDED to English and never translated. That ships a card that reads
    half in Devanagari and half in bracketed English, which is worse than either.
    """
    left = [k for k, v in load_templates(lang).items() if PLACEHOLDER in v]
    assert left == [], (
        f"{len(left)} {lang} value(s) still carry the placeholder. A new English "
        "string was probably added without its translation."
    )


@pytest.mark.parametrize("lang", TRANSLATED)
def test_every_language_keeps_every_slot_its_english_counterpart_has(lang):
    """A dropped {slot} would render a sentence missing its fact.

    This is the failure most likely to survive a human review, because a translator
    reading for meaning does not necessarily notice that {count} vanished.
    """
    import re

    slot = re.compile(r"\{([a-z_]+)\}")
    en, other = load_templates("en"), load_templates(lang)
    for key, english in en.items():
        assert set(slot.findall(other[key])) == set(slot.findall(english)), key


@pytest.mark.parametrize("lang", TRANSLATED)
def test_a_translated_card_fills_real_facts_into_translated_prose(
    lang, welfare_schemes_dir, sunita_profile, today
):
    """The whole point: the prose is translated, the FACTS still come from the verdict.

    AVVC is the sharpest case. The rule is seventy and above, she is sixty, and the
    year she qualifies is arithmetic over two sourced numbers. All three must survive
    into Marathi and Hindi unchanged, because a translated number is a changed number.
    """
    schemes = load_corpus(welfare_schemes_dir)
    verdicts = evaluate_corpus(schemes, sunita_profile)
    by_id = {s.scheme_id: s for s in schemes}
    result = next(
        r for r in gate_all(verdicts, schemes, today=today) if r.verdict.scheme_id == "avvc"
    )

    text = render_card(result, by_id["avvc"], today=today, language=lang).text()

    assert PLACEHOLDER not in text
    assert "{" not in text  # every slot resolved

    # The FACTS survive translation unchanged. Deliberately asserting the digits and
    # not the English phrasing around them: "and above" is now "किंवा त्याहून अधिक",
    # which is the point. A number that changed in translation would be a wrong answer,
    # and Devanagari numerals here would be exactly that kind of change.
    assert "70" in text
    assert "60" in text
    assert "2036" in text
    # And it is actually in Devanagari, not English that forgot to translate.
    assert any("ऀ" <= ch <= "ॿ" for ch in text), lang


@pytest.mark.parametrize("lang", TRANSLATED)
def test_outside_corpus_card_renders_translated(lang):
    card = render_outside_corpus(language=lang)
    assert PLACEHOLDER not in card.text()
    assert "{" not in card.text()
    assert any("ऀ" <= ch <= "ॿ" for ch in card.text())


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


@pytest.mark.parametrize("lang", TRANSLATED)
def test_a_translation_does_not_smuggle_in_a_banned_phrase(lang):
    """The blocklist applies per language, not just to English."""
    joined = " ".join(load_templates(lang).values()).lower()
    for phrase in BANNED_PHRASES:
        assert phrase not in joined


def test_an_unknown_language_is_an_error_not_a_silent_fallback(
    welfare_schemes_dir, sunita_profile, today
):
    """Falling back to English would show a citizen a language they may not read."""
    from haqdaar.render.render import RenderError

    with pytest.raises(RenderError, match="no template set"):
        load_templates("ta")  # Tamil is not shipped; hi and mr now are


# --- intake questions carry the same translation discipline ------------------


def test_every_intake_string_is_translated_into_every_language(corpus_dir):
    """Intake prompts live in corpus/intake.yaml, not the template set.

    They are questions, not verdict sentences — no claim about anyone — so the digit
    ban that governs template prose would be wrong for them ("How much land, in
    hectares?" is fine). But the translation discipline is identical: a value in every
    language for every string, and none of them left as a placeholder.

    A mistranslated QUESTION is not cosmetic either. It changes what she answers, which
    changes the profile, which changes her verdict. The wording of the government
    employee and pension prompts carries an official carve-out for Class IV staff, and
    a translation that drops it silently disqualifies the lowest-paid workers in the
    country.
    """
    from haqdaar.profile.intake import load_intake

    spec = load_intake(corpus_dir / "intake.yaml")

    strings: list[tuple[str, dict]] = []
    for need in spec.needs:
        strings.append((f"need:{need.need_id}", need.label))
    for section in spec.sections:
        strings.append((section.section_id, section.title))
        for question in section.questions:
            strings.append((question.question_id, question.prompt))
            for option in question.options:
                strings.append((f"{question.question_id}:{option.value}", option.label))

    assert strings
    for name, mapping in strings:
        assert "en" in mapping, name
        assert PLACEHOLDER not in mapping["en"], f"{name} English carries a placeholder"
        for lang in TRANSLATED:
            assert lang in mapping, f"{name} has no {lang} value"
            assert mapping[lang].strip(), f"{name} {lang} value is empty"
            assert PLACEHOLDER not in mapping[lang], (
                f"{name} {lang} is still a placeholder. A string was probably added "
                "to English without translating it."
            )
            assert any("ऀ" <= ch <= "ॿ" for ch in mapping[lang]), (
                f"{name} {lang} contains no Devanagari — is it untranslated English?"
            )
