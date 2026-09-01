"""Reading a citizen's own words into answers, without a model.

The design bet: patterns understand less than a language model would, and cannot
invent. Every test here is about the second half. A miss costs one question; a wrong
reading puts a fact into her profile that she did not state.

The safety net underneath all of it is that these are ANSWERS, which are declarations.
`evaluate.py` still applies the asymmetry, so a bad reading can rule a scheme out and
can never rule one in without the document the corpus asks for.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from haqdaar.api.app import app  # noqa: E402
from haqdaar.profile.intake import load_intake  # noqa: E402
from haqdaar.profile.understand import understand  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def config(corpus_dir):
    return load_intake(corpus_dir / "intake.yaml").understand


def read(text, config, language="en"):
    return understand(text, language, hints=config.hints, routes=config.routes)


# --- it reads what is actually there ----------------------------------------


def test_it_reads_a_plain_sentence(config):
    r = read("My husband died last year and I have 0.5 hectare of land", config)
    assert r.answers["marital_status"] == "WIDOW"
    assert r.answers["landholding"] == 0.5
    assert r.vertical == "welfare"


def test_every_answer_carries_the_words_that_produced_it(config):
    """A pre-filled answer with no visible cause is indistinguishable from a guess."""
    r = read("I am 60, a widow, below poverty line", config)
    assert r.matches
    for match in r.matches:
        assert match.phrase
        assert match.question_id in r.answers
        assert match.value == r.answers[match.question_id]


def test_it_reads_devanagari_and_devanagari_digits(config):
    r = read("माझे पती वारले आहेत, मी ६० वर्षांची आहे", config, "mr")
    assert r.answers["marital_status"] == "WIDOW"
    # Folded to ASCII, because the corpus and every bound are in ASCII digits and a
    # number surviving in another script would silently fail to compare.
    assert r.answers["age"] == 60


def test_a_marathi_speaker_writing_english_is_still_understood(config):
    """People mix scripts. Every language is tried, not just the one selected."""
    r = read("I am a widow", config, "mr")
    assert r.answers["marital_status"] == "WIDOW"


# --- it refuses to invent ---------------------------------------------------


def test_negation_is_respected(config):
    """The single most damaging misread available: it is the door into widow pensions."""
    assert "marital_status" not in read("I am not a widow", config).answers
    assert "marital_status" not in read("मी विधवा नाही", config, "mr").answers


def test_an_acre_is_never_converted_to_a_hectare(config):
    """The corpus threshold is in hectares and an acre is not one.

    Quietly converting a number a citizen typed is exactly the kind of helpfulness
    that produces a confidently wrong verdict.
    """
    assert "landholding" not in read("I have half an acre", config).answers
    assert "landholding" not in read("I own 2 acres of land", config).answers


def test_a_childs_class_is_not_read_as_hers(config):
    """Found by reading real output, not by predicting it.

    "I am a widow with a daughter in class 9" produced class_level=9, which is the
    daughter's class, not hers.
    """
    r = read("I am a widow with a daughter in class 9", config)
    assert "class_level" not in r.answers
    assert r.answers["marital_status"] == "WIDOW"


def test_silence_is_not_an_answer(config):
    """Not mentioning a husband does not make her unmarried."""
    r = read("I need help with money", config)
    assert "marital_status" not in r.answers
    assert "gender" not in r.answers


def test_nothing_recognised_reads_as_nothing(config):
    r = read("hello there", config)
    assert r.answers == {}
    assert r.matches == []


def test_an_impossible_number_is_dropped_not_clamped(config):
    """Clamping would turn a typo into a confident fact."""
    assert "age" not in read("I am 999 years old", config).answers


def test_more_specific_phrases_win(config):
    """'unmarried' contains 'married'. Order in the rule table is load-bearing."""
    assert read("I am unmarried", config).answers["marital_status"] == "UNMARRIED"


# --- routing ----------------------------------------------------------------


def test_a_stated_fact_beats_a_keyword(config):
    """She said she is a widow; the word 'business' does not outvote that."""
    r = read("I am a widow and I want to start a business", config)
    assert r.vertical in {"welfare", "entrepreneur"}
    assert r.answers["marital_status"] == "WIDOW"


def test_no_signal_routes_nowhere(config):
    """None means 'ask her'. Routing to the wrong corpus wastes her whole session."""
    assert read("hello", config).vertical is None


def test_understand_never_names_a_scheme(config, corpus_dir):
    """A reading is a fact about her, never a prediction about an outcome."""
    from haqdaar.api.app import PERSONAS
    from haqdaar.corpus.loader import load_corpus

    scheme_ids = {
        s.scheme_id
        for v in set(PERSONAS.values())
        for s in load_corpus(corpus_dir / v / "schemes")
    }
    assert scheme_ids
    r = read("I am a widow with land and I want a loan for my business", config)
    blob = f"{r.answers} {[m.phrase for m in r.matches]}".lower()
    for scheme_id in scheme_ids:
        assert scheme_id.lower() not in blob


# --- over HTTP --------------------------------------------------------------


def test_the_endpoint_returns_answers_and_their_phrases(client):
    body = client.post(
        "/api/understand",
        json={"text": "I am a widow, 60 years old, below poverty line"},
    ).json()

    assert body["vertical"] == "welfare"
    assert body["answers"]["marital_status"] == "WIDOW"
    assert body["understood"]
    for item in body["understood"]:
        assert item["phrase"]
        assert item["prompt"]  # the real question text, not a sentence we composed


def test_an_answer_the_routed_vertical_does_not_ask_is_dropped(client):
    """Otherwise the citizen gets a 422 for something she did nothing to cause.

    "widow" routes to welfare; a class number read from the same sentence would be
    rejected by the intake validator as a question welfare does not ask.
    """
    body = client.post(
        "/api/understand",
        json={"text": "I am a widow and I study in class 10"},
    ).json()

    assert body["vertical"] == "welfare"
    assert "class_level" not in body["answers"]
    assert all(u["question_id"] != "class_level" for u in body["understood"])


def test_whatever_it_returns_is_accepted_by_intake(client):
    """The contract that matters: a reading must be submittable as it stands."""
    read_back = client.post(
        "/api/understand",
        json={"text": "I am a widow, 60 years old, with 0.5 hectare"},
    ).json()

    submitted = client.post(
        "/api/intake",
        json={
            "vertical": read_back["vertical"],
            "answers": read_back["answers"],
            "documents_held": [],
            "language": "en",
        },
    )
    assert submitted.status_code == 200, submitted.json()
    assert submitted.json()["cards"]


def test_empty_text_is_not_an_error(client):
    body = client.post("/api/understand", json={"text": "   "}).json()
    assert body["answers"] == {}
    assert body["vertical"] is None


def test_a_very_long_text_is_refused_rather_than_processed(client):
    assert client.post(
        "/api/understand", json={"text": "x" * 5000}
    ).status_code == 422


def test_a_class_number_is_not_read_as_an_age(config):
    """Found by reading real output, the same way the child's-class guard was.

    "I am in class 10" produced age=10. The age cue will bridge up to twenty
    non-digit characters to reach a number, and " in class " is ten of them. A student
    recorded as ten years old fails age bounds across the corpus, and the front door
    would have shown her "How old are you? 10" in her own words, which reads as the
    engine being confidently wrong rather than merely quiet.
    """
    r = read("I am in class 10, my father earns very little, we are SC", config)
    assert "age" not in r.answers
    assert r.answers["class_level"] == 10

    # Same sentence in Marathi: मी is an age cue and इयत्ता is the class it bridges to.
    mr = read("मी इयत्ता 10 मध्ये आहे", config, "mr")
    assert "age" not in mr.answers
    assert mr.answers["class_level"] == 10

    # The guard must not cost a real age in the same breath as a class.
    both = read("I am 15 and I am in class 10", config)
    assert both.answers["age"] == 15
    assert both.answers["class_level"] == 10
