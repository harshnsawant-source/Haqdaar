"""The API serializes the deterministic renderer and adds nothing.

The load-bearing assertion is `test_payload_matches_the_golden_card`: whatever the
endpoint returns must be byte-identical to what render_card produced locally. If the
API ever starts composing a sentence, that test goes red.
"""

import os

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from haqdaar.corpus.loader import load_corpus  # noqa: E402
from haqdaar.eligibility.aggregate import best_unlock  # noqa: E402
from haqdaar.eligibility.evaluate import evaluate_corpus  # noqa: E402
from haqdaar.guard.gate import gate_all  # noqa: E402
from haqdaar.profile.schema import load_profile  # noqa: E402
from haqdaar.render.render import BANNED_PHRASES, render_card  # noqa: E402

TODAY = "2026-08-22"


@pytest.fixture(scope="module")
def client(corpus_dir):
    os.environ["HAQDAAR_CORPUS"] = str(corpus_dir)
    os.environ["HAQDAAR_TODAY"] = TODAY
    from haqdaar.api.app import app

    with TestClient(app) as test_client:
        yield test_client
    os.environ.pop("HAQDAAR_TODAY", None)


def test_health(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["verticals"] == ["entrepreneur", "welfare"]


def test_personas_lists_the_fixtures(client):
    body = client.get("/api/personas").json()
    assert {p["persona_id"] for p in body} == {
        "entrepreneur-01",
        "entrepreneur-02",
        "sunita",
    }
    assert {p["vertical"] for p in body} == {"entrepreneur", "welfare"}


def test_payload_matches_the_golden_card(client, corpus_dir, today):
    """The API must return exactly what the renderer produced. No re-phrasing."""
    response = client.get("/api/evaluate", params={"persona_id": "entrepreneur-01"})
    assert response.status_code == 200
    body = response.json()

    schemes = load_corpus(corpus_dir / "entrepreneur" / "schemes")
    profile = load_profile(
        corpus_dir / "entrepreneur" / "personas" / "entrepreneur-01.json"
    )
    verdicts = evaluate_corpus(schemes, profile)
    unlock = best_unlock(verdicts)
    by_id = {s.scheme_id: s for s in schemes}
    expected = {
        r.verdict.scheme_id: render_card(
            r, by_id[r.verdict.scheme_id], today=today, unlock=unlock
        )
        for r in gate_all(verdicts, schemes, today=today)
    }

    assert {c["scheme_id"] for c in body["cards"]} == set(expected)
    for card in body["cards"]:
        golden = expected[card["scheme_id"]]
        assert card["lines"] == golden.lines
        assert card["approval_lines"] == golden.approval_lines
        assert card["banners"] == golden.banners
        assert card["status"] == golden.status.value


def test_approval_split_is_flagged_not_merged(client):
    body = client.get(
        "/api/evaluate", params={"persona_id": "entrepreneur-01"}
    ).json()
    nsfdc = next(c for c in body["cards"] if c["scheme_id"] == "nsfdc-term-loan")

    assert nsfdc["status"] == "ELIGIBLE"
    assert nsfdc["has_approval_split"] is True
    assert nsfdc["approval_lines"]
    # The refusal never leaks into the eligibility lines.
    assert not any("not mine to promise" in line for line in nsfdc["lines"])


def test_citations_are_verbatim_with_sources(client):
    body = client.get(
        "/api/evaluate", params={"persona_id": "entrepreneur-01"}
    ).json()
    standup = next(c for c in body["cards"] if c["scheme_id"] == "stand-up-india")

    assert len(standup["citations"]) == 4
    for citation in standup["citations"]:
        assert citation["clause_text"].startswith("[VERIFY AT SOURCE]")
        assert citation["source_url"] == "https://www.standupmitra.in/"
        assert citation["evaluation"] == "TRUE"
        assert citation["document_id"]


def test_unlock_beat_is_served(client):
    body = client.get(
        "/api/evaluate", params={"persona_id": "entrepreneur-02"}
    ).json()
    assert body["unlock"] == {
        "document_id": "caste_certificate",
        "count": 2,
        "scheme_ids": ["nsfdc-term-loan", "stand-up-india"],
    }
    assert all(c["status"] == "BLOCKED_ON_DOCUMENT" for c in body["cards"])


def test_reveal_vertical_serves_the_refusal(client):
    body = client.get("/api/evaluate", params={"persona_id": "sunita"}).json()
    assert body["vertical"] == "welfare"
    pmjay = next(c for c in body["cards"] if c["scheme_id"] == "pmjay")
    assert pmjay["status"] == "UNVERIFIABLE"
    assert pmjay["unlocking_docs"] == []
    assert all(c["settleable"] is False for c in pmjay["citations"])

    avvc = next(c for c in body["cards"] if c["scheme_id"] == "avvc")
    assert avvc["status"] == "NOT_ELIGIBLE"
    assert "You become eligible in 2036." in avvc["lines"]


def test_out_of_corpus_query_refuses(client):
    body = client.get(
        "/api/evaluate",
        params={"persona_id": "entrepreneur-01", "query": "How much tax do I owe?"},
    ).json()
    assert body["outside_corpus"] is True
    assert len(body["cards"]) == 1
    assert body["cards"][0]["status"] == "UNVERIFIABLE"
    assert body["cards"][0]["citations"] == []
    assert body["unlock"] is None


def test_in_corpus_query_narrows_to_the_routed_scheme(client):
    body = client.get(
        "/api/evaluate",
        params={"persona_id": "entrepreneur-01", "query": "Stand-Up India"},
    ).json()
    assert body["outside_corpus"] is False
    assert [c["scheme_id"] for c in body["cards"]] == ["stand-up-india"]


def test_unknown_persona_is_404(client):
    assert client.get("/api/evaluate", params={"persona_id": "nobody"}).status_code == 404


def test_no_served_string_ever_hedges(client):
    """The blocklist, asserted at the network boundary."""
    for persona in ["entrepreneur-01", "entrepreneur-02", "sunita"]:
        body = client.get("/api/evaluate", params={"persona_id": persona}).json()
        for card in body["cards"]:
            served = " ".join(
                [*card["lines"], *card["approval_lines"], *card["banners"]]
            ).lower()
            for phrase in BANNED_PHRASES:
                assert phrase not in served
            assert "{" not in served


def test_every_card_declares_its_provisional_status(client):
    """Nothing unverified reaches the UI without saying so."""
    body = client.get(
        "/api/evaluate", params={"persona_id": "entrepreneur-01"}
    ).json()
    for card in body["cards"]:
        assert card["verification_status"] == "PROVISIONAL"
        assert any("not yet been verified" in b for b in card["banners"])
