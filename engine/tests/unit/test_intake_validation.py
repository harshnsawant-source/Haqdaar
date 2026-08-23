"""An answer the question set cannot account for is not a fact about the citizen.

The engine may say "I do not know", and it may say "no, and here is the rule". It must
never build either sentence out of an input it could not understand.

The bug this file pins: `venture_type="FIRST"` — a value the corpus never defines —
produced "The rule says greenfield. Your venture type is first." A definitive, cited,
WRONG refusal. The asymmetry made it worse: a junk value that once sat UNKNOWN and read
as "bring a document" now read as a confident no.
"""

import os

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from haqdaar.profile.intake import (  # noqa: E402
    AnswerRejected,
    load_intake,
    validate_answers,
)
from haqdaar.render.labels import value_label  # noqa: E402


@pytest.fixture(scope="module")
def spec(corpus_dir):
    return load_intake(corpus_dir / "intake.yaml")


@pytest.fixture(scope="module")
def client(corpus_dir):
    os.environ["HAQDAAR_CORPUS"] = str(corpus_dir)
    os.environ["HAQDAAR_TODAY"] = "2026-08-22"
    from haqdaar.api.app import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def post(client, vertical, answers, documents=None):
    return client.post(
        "/api/intake",
        json={
            "vertical": vertical,
            "answers": answers,
            "documents_held": documents or [],
        },
    )


# --- the reported bug -------------------------------------------------------


def test_a_choice_value_the_corpus_never_defined_is_refused(client):
    response = post(client, "entrepreneur", {"venture_type": "FIRST"})
    assert response.status_code == 422
    detail = str(response.json()["detail"])
    assert "venture_type" in detail and "FIRST" in detail
    assert "GREENFIELD" in detail  # tells the caller what was expected


def test_the_refused_value_can_never_reach_a_rendered_card(client):
    """The whole point: no card is built from an input we did not understand."""
    response = post(client, "entrepreneur", {"venture_type": "FIRST"})
    assert response.status_code == 422

    body = response.json()
    assert "cards" not in body
    assert "unlock" not in body

    # No verdict language of any kind. The error may name the allowed values — that is
    # the message being useful — but it must not contain a sentence about her.
    for sentence in (
        "The rule says",
        "Not this one",
        "Bring your",
        "You are eligible",
        "I cannot confirm",
    ):
        assert sentence not in response.text


# --- numbers ----------------------------------------------------------------


@pytest.mark.parametrize("age", [-5, 9999, 121])
def test_an_age_outside_the_declared_range_is_refused(client, age):
    response = post(client, "welfare", {"age": age})
    assert response.status_code == 422
    assert "age" in str(response.json()["detail"])


@pytest.mark.parametrize("age", [0, 34, 60, 120])
def test_a_legitimate_age_is_unaffected(client, age):
    assert post(client, "welfare", {"age": age}).status_code == 200


def test_a_non_numeric_answer_to_a_number_question_is_refused(client):
    response = post(client, "welfare", {"age": "twelve"})
    assert response.status_code == 422
    assert "not a number" in str(response.json()["detail"])


def test_a_boolean_is_not_a_number(client):
    """True is an int in Python. It is not an age."""
    assert post(client, "welfare", {"age": True}).status_code == 422


def test_a_non_boolean_answer_to_a_yes_no_question_is_refused(client):
    response = post(client, "welfare", {"bpl": "maybe"})
    assert response.status_code == 422
    assert "yes or no" in str(response.json()["detail"])


# --- vertical scoping makes foreign answers reachable -----------------------


def test_a_question_from_another_vertical_is_refused(client):
    """Scoping the form made this reachable: welfare-only answers sent to entrepreneur."""
    response = post(client, "entrepreneur", {"bpl": True})
    assert response.status_code == 422
    assert "bpl" in str(response.json()["detail"])

    response = post(client, "welfare", {"venture_type": "GREENFIELD"})
    assert response.status_code == 422
    assert "venture_type" in str(response.json()["detail"])


def test_a_question_id_that_exists_nowhere_is_refused(client):
    response = post(client, "welfare", {"favourite_colour": "blue"})
    assert response.status_code == 422
    assert "favourite_colour" in str(response.json()["detail"])


def test_a_document_the_form_does_not_offer_is_refused(client):
    response = post(client, "welfare", {"age": 60}, documents=["forged_certificate"])
    assert response.status_code == 422
    assert "forged_certificate" in str(response.json()["detail"])


# --- absent is not wrong ----------------------------------------------------


def test_unanswered_questions_are_still_legitimate(client):
    """Rejecting is for values that are actively wrong, never for absent ones."""
    for answers in ({}, {"age": None}, {"marital_status": ""}, {"age": None, "bpl": None}):
        response = post(client, "welfare", answers)
        assert response.status_code == 200, answers


def test_a_valid_submission_is_unaffected(client):
    response = post(
        client,
        "welfare",
        {"age": 60, "marital_status": "WIDOW", "bpl": True, "monthly_pension": 0},
        documents=["aadhaar", "husband_death_certificate"],
    )
    assert response.status_code == 200
    assert response.json()["cards"]


# --- every problem is reported, not just the first --------------------------


def test_all_problems_are_reported_together(spec):
    with pytest.raises(AnswerRejected) as raised:
        validate_answers(
            spec,
            {"age": 9999, "marital_status": "SINGLE", "favourite_colour": "blue"},
            vertical="welfare",
        )
    assert len(raised.value.problems) == 3


# --- the rendering bug found alongside it -----------------------------------


def test_a_negative_number_is_never_shown_as_a_positive_one():
    """Found while reproducing age=-5.

    value_label split on "-" like a category token, so -5 rendered as "5" and a card
    read "Your age is 5" for an age of minus five. Changing the number a person is
    shown is never a formatting decision. Validation now refuses -5 outright, but the
    renderer must not corrupt any number it is given.
    """
    assert value_label(-5) == "-5"
    assert value_label(0) == "0"
    assert value_label(1500000) == "1500000"
    assert value_label(0.8) == "0.8"
    # Category tokens still read as words.
    assert value_label("WIDOW") == "widow"
    assert value_label("SC") == "SC"
