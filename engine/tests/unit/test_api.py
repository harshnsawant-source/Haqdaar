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
        "document_label": "caste certificate",
        "count": 3,
        "scheme_ids": ["nsfdc-term-loan", "stand-up-india", "vcf-sc"],
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


# --- A+ action endpoint -----------------------------------------------------


def test_act_fills_the_form_and_returns_a_simulated_reference(client):
    response = client.post(
        "/api/act",
        params={"persona_id": "entrepreneur-01", "scheme_id": "stand-up-india"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["simulated"] is True
    assert body["is_stand_in"] is True
    assert body["reference"] == "SIM-STANDUPIND-20260822-D1679F"
    assert body["reference"].startswith("SIM-")

    assert [f["field_id"] for f in body["filled"]] == [
        "applicant_social_category",
        "applicant_gender",
        "enterprise_venture_type",
        "enterprise_loan_amount_sought",
    ]
    assert len(body["gaps"]) == 10
    assert body["missing_documents"][0] == "aadhaar"


def test_act_always_serves_the_simulated_banner(client):
    """The marker cannot be absent from the wire, whatever else changes."""
    body = client.post(
        "/api/act",
        params={"persona_id": "entrepreneur-01", "scheme_id": "stand-up-india"},
    ).json()
    assert any("SIMULATED." in b for b in body["banners"])
    assert any("SIMULATED FORM LAYOUT." in b for b in body["banners"])
    assert "SIMULATED" in " ".join(body["banners"])


def test_act_refuses_a_non_eligible_verdict(client):
    """entrepreneur-02 is blocked on a document; no application gets filled."""
    response = client.post(
        "/api/act",
        params={"persona_id": "entrepreneur-02", "scheme_id": "stand-up-india"},
    )
    assert response.status_code == 409
    assert "BLOCKED_ON_DOCUMENT" in response.json()["detail"]


def test_act_404s_when_no_form_exists(client):
    """NSFDC has no application form yet. Say so; do not improvise one."""
    response = client.post(
        "/api/act",
        params={"persona_id": "entrepreneur-01", "scheme_id": "nsfdc-term-loan"},
    )
    assert response.status_code == 404
    assert "no application form" in response.json()["detail"]


def test_act_404s_on_an_unknown_scheme(client):
    response = client.post(
        "/api/act", params={"persona_id": "entrepreneur-01", "scheme_id": "nope"}
    )
    assert response.status_code == 404


def test_act_never_hedges(client):
    body = client.post(
        "/api/act",
        params={"persona_id": "entrepreneur-01", "scheme_id": "stand-up-india"},
    ).json()
    served = " ".join([*body["lines"], *body["gap_lines"], *body["banners"]]).lower()
    for phrase in BANNED_PHRASES:
        assert phrase not in served
    assert "{" not in served


# --- document upload / extraction -------------------------------------------


def _png(lines):
    """A small generated document image, so the upload path is exercised for real."""
    import io

    from PIL import Image, ImageDraw

    image = Image.new("RGB", (700, 60 + 60 * len(lines)), "white")
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(lines):
        draw.text((20, 30 + 60 * i), line, fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_extract_fixture_backed_reproduces_the_golden_verdict(client):
    """With nothing readable, the labelled fallback still gives the golden result."""
    response = client.post(
        "/api/extract",
        data={
            "persona_id": "entrepreneur-01",
            "mode": "FIXTURE_BACKED",
            "document_types": ["caste_certificate"],
        },
        files={"files": ("blank.png", _png([]), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["mode"] == "FIXTURE_BACKED"
    assert {c["scheme_id"]: c["status"] for c in body["cards"]} == {
        "nsfdc-term-loan": "ELIGIBLE",
        "stand-up-india": "ELIGIBLE",
        "vcf-sc": "ELIGIBLE",
    }


def test_extract_marks_where_every_value_came_from(client):
    body = client.post(
        "/api/extract",
        data={
            "persona_id": "entrepreneur-01",
            "mode": "FIXTURE_BACKED",
            "document_types": ["caste_certificate"],
        },
        files={"files": ("blank.png", _png([]), "image/png")},
    ).json()

    assert body["fixture_backed"] is True
    origins = {f["profile_field"]: f["origin"] for f in body["fields"]}
    assert origins  # every field says where it came from
    assert set(origins.values()) <= {"EXTRACTED", "FIXTURE"}
    for field in body["fields"]:
        assert 0.0 <= field["confidence"] <= 1.0


def test_extract_live_mode_refuses_rather_than_borrowing(client):
    """LIVE with an unreadable page must produce UNKNOWN, not the fixture's answers.

    This is the honest failure: nothing was read, so nothing is claimed.
    """
    body = client.post(
        "/api/extract",
        data={
            "persona_id": "entrepreneur-01",
            "mode": "LIVE",
            "document_types": ["caste_certificate"],
        },
        files={"files": ("blank.png", _png([]), "image/png")},
    ).json()

    assert body["mode"] == "LIVE"
    assert body["fixture_backed"] is False
    # Nothing readable and nothing borrowed: no confident value anywhere.
    assert all(f["origin"] == "EXTRACTED" for f in body["fields"])
    # ...so the engine cannot clear her, and says so rather than guessing.
    assert {c["status"] for c in body["cards"]} <= {
        "BLOCKED_ON_DOCUMENT",
        "UNVERIFIABLE",
        "NOT_ELIGIBLE",
    }


def test_extract_reports_whether_ocr_was_even_available(client):
    body = client.post(
        "/api/extract",
        data={
            "persona_id": "entrepreneur-01",
            "mode": "LIVE",
            "document_types": ["caste_certificate"],
        },
        files={"files": ("blank.png", _png([]), "image/png")},
    ).json()
    assert isinstance(body["ocr_available"], bool)
    assert body["reports"][0]["document_type"] == "caste_certificate"
    # Whatever it could not read is named, not silently dropped.
    assert isinstance(body["reports"][0]["unread"], list)


def test_extract_rejects_mismatched_files_and_types(client):
    response = client.post(
        "/api/extract",
        data={"persona_id": "entrepreneur-01", "document_types": []},
        files={"files": ("blank.png", _png([]), "image/png")},
    )
    assert response.status_code == 422


def test_extract_rejects_an_unknown_mode(client):
    response = client.post(
        "/api/extract",
        data={
            "persona_id": "entrepreneur-01",
            "mode": "TRUST_ME",
            "document_types": ["caste_certificate"],
        },
        files={"files": ("blank.png", _png([]), "image/png")},
    )
    assert response.status_code == 422


def test_every_served_identifier_carries_an_engine_computed_label(client):
    """The frontend must never derive prose from an id.

    The "one document away" headline once rendered `document_id.replace(/_/g, " ")` in
    JS, so it read "bpl ration card" directly above a card that correctly said "BPL
    ration card" — same paper, two spellings, one screen. Labels now come from
    render/labels.py, and this asserts the payload agrees with it so the two cannot
    drift apart again.
    """
    from haqdaar.render.labels import document_label, field_label

    welfare = client.get("/api/evaluate", params={"persona_id": "sunita"}).json()
    assert welfare["unlock"]["document_label"] == document_label(
        welfare["unlock"]["document_id"]
    )
    assert welfare["unlock"]["document_label"] == "BPL ration card"

    for card in welfare["cards"]:
        for citation in card["citations"]:
            if citation["document_id"]:
                assert citation["document_label"] == document_label(
                    citation["document_id"]
                )
            else:
                assert citation["document_label"] is None

    action = client.post(
        "/api/act",
        params={"persona_id": "entrepreneur-01", "scheme_id": "stand-up-india"},
    ).json()
    for filled in action["filled"]:
        assert filled["source_document_label"] == document_label(
            filled["source_document"]
        )

    extracted = client.post(
        "/api/extract",
        data={
            "persona_id": "sunita",
            "mode": "FIXTURE_BACKED",
            "document_types": ["caste_certificate"],
        },
        files={"files": ("blank.png", _png([]), "image/png")},
    ).json()
    for field in extracted["fields"]:
        assert field["label"] == field_label(field["profile_field"])
        assert field["document_label"] == document_label(field["document_id"])
        assert "." not in field["label"]  # never a dotted path on screen
    for report in extracted["reports"]:
        assert report["unread_labels"] == [field_label(f) for f in report["unread"]]


def test_the_headline_and_the_card_spell_the_document_the_same_way(client):
    """The exact regression: chip and card, same screen, same words."""
    body = client.get("/api/evaluate", params={"persona_id": "sunita"}).json()
    headline = body["unlock"]["document_label"]

    blocked = [c for c in body["cards"] if c["status"] == "BLOCKED_ON_DOCUMENT"]
    assert blocked
    for card in blocked:
        assert any(headline in line for line in card["lines"]), (
            f"{card['scheme_id']}: card does not spell the document as {headline!r}"
        )
