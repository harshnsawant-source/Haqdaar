"""Read a citizen's own words into intake answers, deterministically.

She types "my husband died last year and I have half a hectare"; this returns
`marital_status=WIDOW` and `landholding=0.5`, each with the exact phrase that produced
it, and the intake form comes up pre-filled and marked so she can correct it.

WHY THERE IS NO MODEL HERE
--------------------------
A language model would read this better. It would also mean an API key, a network round
trip, and the end of three claims this project can currently prove: zero generative
calls, no keys, works offline. The test suite passes with every key stripped from the
environment, and a Panchayat with no connection is the deployment story, not an edge
case. So this is patterns over text: worse at understanding, and it cannot invent.

WHAT THIS IS ALLOWED TO DO
--------------------------
Produce ANSWERS, which are her declarations. Nothing more. The answers travel the same
path as anything she types into the form, so `evaluate.py` still applies the asymmetry:
a declaration can rule a scheme OUT, and can never rule one IN without the document the
corpus asks for. That is what makes a wrong reading here recoverable rather than
dangerous. The worst case is that she sees a wrong answer pre-filled and changes it.

For the same reason every match carries the `phrase` that triggered it. A pre-filled
answer with no visible cause is indistinguishable from a guess.

WHAT IT REFUSES TO DO
---------------------
* No unit conversion. "half an acre" is NOT silently turned into hectares. An acre is
  not a hectare, the corpus threshold is in hectares, and quietly converting a number
  a citizen typed is exactly the kind of helpfulness that produces a wrong verdict.
  Only an explicit hectare figure is read.
* No inference from absence. Not mentioning a husband does not make her unmarried.
* No scheme names. This produces facts about her, never a prediction about outcomes.
"""

from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field

#: Words that flip a phrase's meaning. Without these, "I am not a widow" reads as
#: WIDOW, which is the single most damaging misread available: it is the door into the
#: widow-pension corpus.
#:
#: WORD ORDER DIFFERS BY LANGUAGE, and assuming otherwise is how this was wrong at
#: first. English negates BEFORE the thing ("not a widow"). Marathi and Hindi are
#: verb-final and negate AFTER it ("मी विधवा नाही" is literally "I widow am-not"), so a
#: backward-only check read that as a widow. Caught by a test, not by prediction.
_NEGATORS_BEFORE = (
    "not", "no", "never", "isn't", "isnt", "aren't", "arent", "wasn't", "wasnt",
    "नाही", "नाहीये", "नका", "नसून", "नहीं", "नही",
)

#: Checked AFTER the phrase as well. Devanagari only, on purpose: scanning forward in
#: English would let "I am a widow, not a farmer" suppress the widowhood.
_NEGATORS_AFTER = ("नाही", "नाहीये", "नसून", "नहीं", "नही")

#: How far to look, in characters. Short on purpose: "my husband is not working" must
#: not suppress a widowhood match ten words later.
_NEGATION_WINDOW = 24


class Match(BaseModel):
    """One thing understood, and the exact words that produced it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    question_id: str
    value: bool | int | float | str
    #: The substring of her text that triggered this. Shown to her, always.
    phrase: str


class Reading(BaseModel):
    """What her sentence was understood to say. Never a verdict."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: The corpus her words point at, or None when nothing points clearly enough.
    #: None means "ask her", not "guess".
    vertical: str | None = None
    #: question_id -> value, ready to seed the intake form.
    answers: dict[str, bool | int | float | str] = Field(default_factory=dict)
    matches: list[Match] = Field(default_factory=list)


#: (question_id, value, {language: [phrases]}). Order matters: the first match for a
#: question wins, so put the more specific phrase first ("unmarried" before "married").
_RULES: list[tuple[str, object, dict[str, list[str]]]] = [
    ("marital_status", "WIDOW", {
        "en": ["widow", "widowed", "husband died", "husband has died", "husband passed away",
               "lost my husband", "husband expired", "husband is no more"],
        "mr": ["विधवा", "पती वारले", "पती वारला", "नवरा वारला", "पती निधन"],
        "hi": ["विधवा", "पति की मृत्यु", "पति का निधन", "पति नहीं रहे", "पति गुजर गए"],
    }),
    ("marital_status", "DIVORCED", {
        "en": ["divorced", "divorce", "separated from my husband"],
        "mr": ["घटस्फोट", "घटस्फोटित"],
        "hi": ["तलाक", "तलाकशुदा"],
    }),
    ("marital_status", "UNMARRIED", {
        "en": ["unmarried", "never married", "not married", "single"],
        "mr": ["अविवाहित", "लग्न झाले नाही"],
        "hi": ["अविवाहित", "शादी नहीं हुई"],
    }),
    ("marital_status", "MARRIED", {
        "en": ["married"],
        "mr": ["विवाहित", "लग्न झाले"],
        "hi": ["विवाहित", "शादीशुदा"],
    }),

    ("social_category", "SC", {
        "en": ["scheduled caste", "sc category", "dalit"],
        "mr": ["अनुसूचित जाती", "अनुसूचित जातीचा", "दलित"],
        "hi": ["अनुसूचित जाति", "दलित"],
    }),
    ("social_category", "ST", {
        "en": ["scheduled tribe", "st category", "adivasi", "tribal"],
        "mr": ["अनुसूचित जमाती", "आदिवासी"],
        "hi": ["अनुसूचित जनजाति", "आदिवासी"],
    }),
    ("social_category", "OBC", {
        "en": ["obc", "other backward"],
        "mr": ["इतर मागास", "ओबीसी"],
        "hi": ["अन्य पिछड़ा", "ओबीसी"],
    }),
    ("social_category", "GENERAL", {
        "en": ["general category", "open category"],
        "mr": ["खुला प्रवर्ग", "खुल्या प्रवर्ग"],
        "hi": ["सामान्य वर्ग"],
    }),

    ("gender", "FEMALE", {
        "en": ["i am a woman", "i'm a woman", "female"],
        "mr": ["मी स्त्री", "महिला आहे"],
        "hi": ["मैं महिला", "महिला हूं"],
    }),
    ("gender", "MALE", {
        "en": ["i am a man", "i'm a man", "male"],
        "mr": ["मी पुरुष"],
        "hi": ["मैं पुरुष"],
    }),

    ("bpl", True, {
        "en": ["below poverty line", "bpl card", "bpl list", "on bpl"],
        "mr": ["दारिद्र्यरेषेखालील", "दारिद्र्य रेषेखाली", "बीपीएल"],
        "hi": ["गरीबी रेखा से नीचे", "बीपीएल"],
    }),

    ("venture_type", "GREENFIELD", {
        "en": ["start a business", "starting a business", "first business",
               "new business", "want to start"],
        "mr": ["व्यवसाय सुरू", "पहिला व्यवसाय"],
        "hi": ["व्यवसाय शुरू", "पहला व्यवसाय"],
    }),
    ("venture_type", "EXISTING", {
        "en": ["already run", "existing business", "my shop", "i run a"],
        "mr": ["आधीच चालवतो", "माझे दुकान"],
        "hi": ["पहले से चला", "मेरी दुकान"],
    }),
]


_AGE = re.compile(
    r"(?:\b|^)(?:i am|i'm|age|aged|वय|उम्र|मी)\D{0,20}?(\d{1,3})\b"
    r"|(\d{1,3})\s*(?:years old|year old|yrs old|वर्षांचा|वर्षांची|वर्ष|साल का|साल की)",
    re.IGNORECASE,
)
#: Hectares only. See the module docstring on why an acre is not converted.
_HECTARES = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:hectare|hectares|ha\b|हेक्टर|हेक्टेयर)", re.IGNORECASE
)
_CLASS = re.compile(
    r"(?:class|standard|इयत्ता|कक्षा)\s*(\d{1,2})\b"
    r"|(\d{1,2})\s*(?:th|st|nd|rd)\s*(?:class|standard)",
    re.IGNORECASE,
)

#: Someone ELSE whose class she might mention. Found by reading real output: "I am a
#: widow with a daughter in class 9" produced class_level=9, which is the daughter's
#: class, not hers, and not even her vertical. A missing answer costs one question; a
#: wrong one puts another person's life into her profile.
_THIRD_PARTY = re.compile(
    r"\b(?:daughter|son|child|children|kid|kids|grandson|granddaughter|"
    r"मुलगा|मुलगी|मुले|नात|नातू|"
    r"बेटा|बेटी|बच्चे|बच्चा|पोता|पोती)\b",
    re.IGNORECASE,
)


def _normalise(text: str) -> str:
    """Fold to a comparable form without changing what she wrote.

    Devanagari digits are folded to ASCII so "वय ६०" reads as 60. The corpus and every
    bound are in ASCII digits, and a number that survives in a different script would
    silently fail to compare.
    """
    folded = unicodedata.normalize("NFKC", text)
    return "".join(
        str(unicodedata.decimal(ch)) if ch.isdigit() and not ch.isascii() else ch
        for ch in folded
    ).lower()


def _negated(haystack: str, start: int, end: int) -> bool:
    before = haystack[max(0, start - _NEGATION_WINDOW) : start]
    after = haystack[end : end + _NEGATION_WINDOW]
    hit = lambda window, words: any(  # noqa: E731
        re.search(rf"(?:^|\W){re.escape(w)}(?:\W|$)", window) for w in words
    )
    return hit(before, _NEGATORS_BEFORE) or hit(after, _NEGATORS_AFTER)


def understand(
    text: str,
    language: str = "en",
    *,
    hints: dict[str, list[str]] | None = None,
    routes: dict[str, str] | None = None,
) -> Reading:
    """Read her sentence. Returns only what it is sure of, and says why.

    `language` selects which phrase list to try FIRST, but every language is tried:
    people mix scripts, and a Marathi speaker typing "widow" in English should still
    be understood.

    `hints` and `routes` come from corpus/intake.yaml. They are passed in rather than
    hardcoded so this module never learns a vertical's name: adding a corpus folder
    must stay a corpus change, and a test walks the engine to enforce it.
    """
    if not text or not text.strip():
        return Reading()

    hay = _normalise(text)
    answers: dict[str, bool | int | float | str] = {}
    matches: list[Match] = []

    langs = [language] + [l for l in ("en", "mr", "hi") if l != language]

    for question_id, value, by_lang in _RULES:
        if question_id in answers:
            continue  # first rule wins; more specific phrases are listed first
        for lang in langs:
            hit = None
            for phrase in by_lang.get(lang, []):
                needle = _normalise(phrase)
                index = hay.find(needle)
                if index != -1 and not _negated(hay, index, index + len(needle)):
                    hit = phrase
                    break
            if hit:
                answers[question_id] = value
                matches.append(Match(question_id=question_id, value=value, phrase=hit))
                break

    for question_id, pattern, cast in (
        ("age", _AGE, int),
        ("landholding", _HECTARES, float),
        ("class_level", _CLASS, int),
    ):
        found = pattern.search(hay)
        if not found:
            continue
        raw = next((g for g in found.groups() if g), None)
        if raw is None:
            continue
        number = cast(raw)
        # Bounds that are obviously not what she meant are dropped rather than clamped.
        if question_id == "age" and not 0 < number <= 120:
            continue
        if question_id == "class_level":
            if not 1 <= number <= 12:
                continue
            # If a child is mentioned anywhere, the class probably is not hers. Drop it
            # and let her answer: a missing answer costs one question, a wrong one puts
            # somebody else's life into her profile.
            if _THIRD_PARTY.search(hay):
                continue
        answers[question_id] = number
        matches.append(
            Match(question_id=question_id, value=number, phrase=found.group(0).strip())
        )

    return Reading(
        vertical=_route(hay, answers, hints or {}, routes or {}),
        answers=answers,
        matches=matches,
    )


def _route(
    hay: str,
    answers: dict[str, object],
    hints: dict[str, list[str]],
    routes: dict[str, str],
) -> str | None:
    """Pick the corpus her words point at, or None.

    None is a real answer here. Routing someone to the wrong corpus wastes their whole
    session and shows them schemes that were never going to apply, so a tie or a blank
    hands the choice back rather than guessing.
    """
    for question_id, vertical in routes.items():
        if question_id in answers:
            return vertical

    scores = {
        vertical: sum(1 for word in words if _normalise(word) in hay)
        for vertical, words in hints.items()
    }
    if not scores:
        return None
    best = max(scores.values())
    if best == 0:
        return None
    leaders = [v for v, n in scores.items() if n == best]
    return leaders[0] if len(leaders) == 1 else None
