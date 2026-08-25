"""Comparison and need-based entry.

Both come from the Product Architecture doc, and both are deliberately narrower than it
asked for. The doc wanted "Best fit for your profile with a clear explanation" and a
recommendation engine that ranks Strong / Good / Possible Match. Neither exists here,
and the tests below are what stop either creeping back in:

  * a comparison returns facts side by side and never a winner;
  * a need routes to a corpus and never names a scheme.

Both refusals are the same refusal the renderer makes when it rejects "you may qualify".
A ranking is a claim, and this project only makes claims it can prove from a clause.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from haqdaar.api.app import app  # noqa: E402
from haqdaar.corpus.loader import load_corpus  # noqa: E402
from haqdaar.eligibility.compare import (  # noqa: E402
    MAX_SCHEMES,
    ComparisonError,
    compare,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def welfare_schemes(corpus_dir: Path):
    return load_corpus(corpus_dir / "welfare" / "schemes")


# --- compare, as a function -------------------------------------------------


def test_a_comparison_of_one_is_refused(welfare_schemes):
    """Two is the minimum, because one column is not a comparison."""
    with pytest.raises(ComparisonError, match="two to"):
        compare(welfare_schemes[:1])


def test_a_comparison_wider_than_four_is_refused(welfare_schemes):
    with pytest.raises(ComparisonError, match="two to"):
        compare(welfare_schemes[: MAX_SCHEMES + 1])


def test_the_same_scheme_twice_is_refused(welfare_schemes):
    with pytest.raises(ComparisonError, match="duplicate"):
        compare([welfare_schemes[0], welfare_schemes[0]])


def test_every_column_carries_its_source_and_when_we_read_it(welfare_schemes):
    result = compare(welfare_schemes[:3])
    assert len(result.schemes) == 3
    for column in result.schemes:
        assert column.source_url.startswith("https://")
        assert column.retrieved_on
        assert column.eligibility_clauses
        # No profile was supplied, so there is no verdict to report. None means "not
        # evaluated", which must not be confused with "evaluated and unknown".
        assert column.status is None


def test_a_comparison_without_verdicts_is_not_reordered(welfare_schemes):
    """Ordering by actionability is meaningless with nothing to act on."""
    picked = welfare_schemes[:3]
    result = compare(picked)
    assert [c.scheme_id for c in result.schemes] == [s.scheme_id for s in picked]


def test_stacking_schemes_are_grouped_so_a_table_cannot_double_count(welfare_schemes):
    """IGNWPS + SGNAY are one Rs 1,500 payment, not two.

    A comparison table is precisely where someone would otherwise add two benefit
    columns together, so the grouping has to travel with the comparison.
    """
    picked = [s for s in welfare_schemes if s.scheme_id in {"ignwps", "sgnay"}]
    result = compare(picked)
    assert result.stacked_groups == [["ignwps", "sgnay"]]


def test_a_missing_verdict_is_refused_rather_than_left_blank(welfare_schemes):
    """A blank column beside filled ones reads as "nothing found for this scheme"."""
    from haqdaar.eligibility.evaluate import evaluate_scheme
    from haqdaar.profile.schema import CitizenProfile

    picked = welfare_schemes[:2]
    profile = CitizenProfile(profile_id="synthetic", fields={})
    only_one = [evaluate_scheme(picked[0], profile)]

    with pytest.raises(ComparisonError, match="no verdict supplied"):
        compare(picked, only_one)


# --- compare, over HTTP -----------------------------------------------------


def test_compare_serves_facts_without_a_persona(client):
    response = client.get(
        "/api/compare",
        params={"vertical": "welfare", "scheme_ids": "ignwps,sgnay"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["persona_id"] is None
    assert {c["scheme_id"] for c in body["schemes"]} == {"ignwps", "sgnay"}
    assert body["stacked_groups"] == [["ignwps", "sgnay"]]


def test_compare_with_a_persona_orders_by_what_she_can_act_on(client):
    response = client.get(
        "/api/compare",
        params={
            "vertical": "welfare",
            "scheme_ids": "avvc,pm-kisan,ignwps",
            "persona_id": "sunita",
        },
    )
    assert response.status_code == 200
    columns = response.json()["schemes"]

    # An entitlement she can claim, then a paper she can fetch, then the closed door.
    assert [c["scheme_id"] for c in columns] == ["pm-kisan", "ignwps", "avvc"]
    assert [c["status"] for c in columns] == [
        "ELIGIBLE",
        "BLOCKED_ON_DOCUMENT",
        "NOT_ELIGIBLE",
    ]


def test_compare_never_returns_a_winner(client):
    """The feature the Product Architecture doc asked for and this one refuses.

    If a `best_fit`, `score`, `rank` or `match` field ever appears in this response,
    someone has added a ranking, and a ranking is a claim we cannot prove from a clause.
    """
    body = client.get(
        "/api/compare",
        params={
            "vertical": "welfare",
            "scheme_ids": "pm-kisan,ignwps",
            "persona_id": "sunita",
        },
    ).json()

    banned = {"best_fit", "best", "score", "rank", "ranking", "match", "match_strength"}
    assert not banned & set(body)
    for column in body["schemes"]:
        assert not banned & set(column)


def test_compare_refuses_a_persona_from_another_corpus(client):
    """Sunita's verdicts cannot label entrepreneur schemes."""
    response = client.get(
        "/api/compare",
        params={
            "vertical": "entrepreneur",
            "scheme_ids": "nsfdc-term-loan,vcf-sc",
            "persona_id": "sunita",
        },
    )
    assert response.status_code == 409
    assert "belongs to welfare" in response.json()["detail"]


def test_compare_404s_on_an_unknown_scheme(client):
    response = client.get(
        "/api/compare",
        params={"vertical": "welfare", "scheme_ids": "pm-kisan,not-a-scheme"},
    )
    assert response.status_code == 404
    assert "not-a-scheme" in response.json()["detail"]


def test_compare_422s_on_a_single_scheme(client):
    response = client.get(
        "/api/compare", params={"vertical": "welfare", "scheme_ids": "pm-kisan"}
    )
    assert response.status_code == 422


# --- needs ------------------------------------------------------------------


def test_every_need_routes_to_a_corpus_that_exists(client):
    """A need pointing at a missing vertical is a button that leads nowhere."""
    from haqdaar.api.app import PERSONAS

    body = client.get("/api/needs").json()
    assert body["needs"]
    for need in body["needs"]:
        assert need["vertical"] in set(PERSONAS.values()), need["need_id"]


def test_needs_are_scoped_by_vertical(client):
    body = client.get("/api/needs", params={"vertical": "student"}).json()
    assert body["vertical"] == "student"
    assert {n["vertical"] for n in body["needs"]} == {"student"}


def test_a_need_never_names_a_scheme(client):
    """A need is a routing hint, not a promise.

    Naming a scheme before the evaluator has seen a single fact is how a question
    quietly becomes an answer, which is the failure this whole project exists around.
    """
    from haqdaar.api.app import CORPUS_ROOT, PERSONAS

    scheme_ids = {
        scheme.scheme_id
        for vertical in set(PERSONAS.values())
        for scheme in load_corpus(CORPUS_ROOT / vertical / "schemes")
    }
    assert scheme_ids, "no schemes loaded; this test would pass vacuously"

    body = client.get("/api/needs").json()
    for need in body["needs"]:
        assert set(need) == {"need_id", "label", "vertical"}
        blob = f"{need['need_id']} {need['label']}".lower()
        for scheme_id in scheme_ids:
            assert scheme_id.lower() not in blob


def test_needs_404s_on_an_unknown_vertical(client):
    assert client.get("/api/needs", params={"vertical": "nope"}).status_code == 404


def test_needs_cover_every_vertical(client):
    """A vertical with no door into it is unreachable for a citizen who has not been
    handed a demo persona."""
    from haqdaar.api.app import PERSONAS

    body = client.get("/api/needs").json()
    assert {n["vertical"] for n in body["needs"]} == set(PERSONAS.values())


def test_a_shut_scheme_sorts_below_an_open_one_at_the_same_status(client):
    """Found by looking at real output rather than by a test.

    Both of these are ELIGIBLE for entrepreneur-01. Stand-Up India's sanctioned period
    ended on 2025-03-31, so it is the least actionable thing on the table however good
    her verdict looks. Before the window entered the sort key it ranked first, purely
    because "nsfdc" sorts after "stand-up" is false and alphabetical order put it there.
    """
    body = client.get(
        "/api/compare",
        params={
            "vertical": "entrepreneur",
            "scheme_ids": "stand-up-india,nsfdc-term-loan",
            "persona_id": "entrepreneur-01",
        },
    ).json()

    columns = body["schemes"]
    assert [c["status"] for c in columns] == ["ELIGIBLE", "ELIGIBLE"]
    assert [c["scheme_id"] for c in columns] == ["nsfdc-term-loan", "stand-up-india"]
    assert columns[-1]["window_state"] == "LAPSED"
