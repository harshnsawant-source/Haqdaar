"""Rehearsing the failure (guard doc s6).

Every realistic on-stage failure must land on a calm, correct refusal or a labelled
stored answer. Never a hang, never a stack trace, never an empty screen, never a guess.

This file is the rehearsal. If a demo goes wrong on 2 September it will go wrong in one
of the ways below, and each one is asserted here rather than hoped for.
"""

import os

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from haqdaar.corpus.loader import CorpusError, load_corpus  # noqa: E402
from haqdaar.eligibility.evaluate import evaluate_corpus  # noqa: E402
from haqdaar.eligibility.verdict import Status  # noqa: E402
from haqdaar.guard.triggers import t3_no_retrieval_support  # noqa: E402
from haqdaar.profile import ocr  # noqa: E402
from haqdaar.profile.extract import ExtractionMode, build_profile, extract_document  # noqa: E402
from haqdaar.render.render import render_outside_corpus  # noqa: E402
from haqdaar.retrieval.route import route  # noqa: E402


@pytest.fixture(scope="module")
def client(corpus_dir):
    os.environ["HAQDAAR_CORPUS"] = str(corpus_dir)
    os.environ["HAQDAAR_TODAY"] = "2026-08-22"
    from haqdaar.api.app import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def documents_dir(request):
    return request.config.rootpath.parent / "corpus" / "documents"


# --- OCR unavailable, or failing mid-read -----------------------------------


def test_ocr_engine_missing_degrades_to_unknown(documents_dir, monkeypatch):
    monkeypatch.setattr(ocr, "tesseract_available", lambda: False)
    report = extract_document(
        b"", document_type="caste_certificate", documents_dir=documents_dir
    )
    assert report.ocr_available is False
    assert report.fields == []
    assert build_profile([report], profile_id="p").fields == {}


def test_ocr_raising_mid_read_is_caught_not_propagated(monkeypatch):
    """A timeout, a crashed subprocess, a bad DLL — all the same to the citizen.

    pytesseract raises a family of errors and none of them may reach the stage as a
    traceback. They must land on "nothing was read", which the confidence gate turns
    into UNKNOWN.
    """
    monkeypatch.setattr(ocr, "tesseract_available", lambda: True)

    class Boom:
        Output = type("O", (), {"DICT": "dict"})

        @staticmethod
        def image_to_data(*_args, **_kwargs):
            raise TimeoutError("tesseract timed out")

    import sys

    monkeypatch.setitem(sys.modules, "pytesseract", Boom)

    from PIL import Image
    import io

    buffer = io.BytesIO()
    Image.new("RGB", (40, 20), "white").save(buffer, format="PNG")

    result = ocr.read(buffer.getvalue())
    assert result.is_readable is False
    assert result.words == []


def test_corrupt_upload_reads_nothing(documents_dir, monkeypatch):
    monkeypatch.setattr(ocr, "tesseract_available", lambda: True)
    report = extract_document(
        b"\x00\x01 not an image at all",
        document_type="caste_certificate",
        documents_dir=documents_dir,
    )
    assert report.readable is False
    assert report.fields == []


def test_a_file_that_is_not_an_image_is_refused_cleanly(client):
    """Bytes claiming to be a PNG but which are not.

    Since the security pass this is caught by magic-byte sniffing and refused with a
    clear reason, rather than handed to the image library to fail obscurely. Telling
    someone "that is not a document photo" is more use than "I could not read it" when
    the file was never an image.
    """
    response = client.post(
        "/api/extract",
        data={
            "persona_id": "sunita",
            "mode": "LIVE",
            "document_types": ["caste_certificate"],
        },
        files={"files": ("junk.png", b"\x00\x01\x02 not a png", "image/png")},
    )
    assert response.status_code == 415
    assert "not an image" in response.json()["detail"]
    assert "Traceback" not in response.text


def test_a_real_image_that_cannot_be_read_still_returns_a_verdict(client):
    """A genuine but unreadable photo — blurred, blank, wrong page.

    This is the case that must NOT be rejected: it is a document photo, we simply
    could not get anything off it. She still gets answers, all refusing.
    """
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (60, 40), "white").save(buffer, format="PNG")

    response = client.post(
        "/api/extract",
        data={
            "persona_id": "sunita",
            "mode": "LIVE",
            "document_types": ["caste_certificate"],
        },
        files={"files": ("blank.png", buffer.getvalue(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fields"] == []
    assert {c["status"] for c in body["cards"]} <= {
        "BLOCKED_ON_DOCUMENT",
        "UNVERIFIABLE",
        "NOT_ELIGIBLE",
    }


# --- queries between in-corpus and out --------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "scheme",  # pure corpus noise
        "I want money for my family",  # adjacent, no scheme named
        "pension",  # a welfare word asked of the entrepreneur corpus
    ],
)
def test_ambiguous_queries_refuse_rather_than_guess(schemes_dir, query):
    """The floor is biased to refuse. A near-miss is not a match.

    Note what is deliberately NOT in this list: "loan". Against a corpus of two loan
    schemes that word is genuinely in-corpus, and routing to both is the right answer.
    Refusing it would be a false refusal — safe, but wrong.
    """
    result = route(query, load_corpus(schemes_dir))
    assert result.outside_corpus, f"{query!r} scored {result.top_score}"
    assert t3_no_retrieval_support(result) is not None


def test_the_outside_corpus_card_names_nothing_it_cannot_show():
    card = render_outside_corpus()
    assert card.scheme_id == ""
    assert "{" not in card.text()
    assert card.status is Status.UNVERIFIABLE


# --- a corpus that will not load --------------------------------------------


def test_a_missing_corpus_directory_raises_a_clear_error(tmp_path):
    with pytest.raises(CorpusError, match="not a directory"):
        load_corpus(tmp_path / "nope")


def test_a_missing_corpus_over_http_is_503_not_500(client, monkeypatch):
    """503 is what the PWA already treats as "offline, show the stored answer"."""
    from haqdaar.api import app as app_module

    # Patch the loader, not the guard around it, so the real 503 path runs.
    monkeypatch.setattr(app_module, "load_corpus", lambda *_a, **_k: [])
    response = client.get("/api/evaluate", params={"persona_id": "sunita"})
    assert response.status_code == 503
    assert "no corpus" in response.json()["detail"]


def test_an_unexpected_internal_error_never_leaks_a_traceback(client, monkeypatch):
    """A crash mid-demo must read as a failure to answer, not as a Python stack.

    The PWA maps any 5xx onto its calm offline copy, so what matters here is that the
    body carries no traceback for a judge to photograph.
    """
    from haqdaar.api import app as app_module

    def explode(*_args, **_kwargs):
        raise RuntimeError("something unexpected happened deep in the engine")

    monkeypatch.setattr(app_module, "_cards_for", explode)
    response = client.get("/api/evaluate", params={"persona_id": "sunita"})

    assert response.status_code >= 500
    body = response.text
    assert "Traceback" not in body
    assert "haqdaar/eligibility" not in body
    assert "something unexpected happened" not in body


# --- an empty profile still produces answers --------------------------------


def test_a_citizen_with_no_documents_still_gets_correct_verdicts(
    welfare_schemes_dir, today
):
    """The worst realistic input: nothing was read at all.

    Every scheme must resolve to a refusal or a blocked-on-document. None may resolve
    ELIGIBLE, and none may crash.
    """
    from haqdaar.guard.gate import gate_all
    from haqdaar.profile.schema import CitizenProfile

    empty = CitizenProfile(profile_id="nobody", fields={})
    schemes = load_corpus(welfare_schemes_dir)
    verdicts = evaluate_corpus(schemes, empty)

    assert all(v.status is not Status.ELIGIBLE for v in verdicts)
    # And every one still passes the Guard rather than raising.
    assert len(gate_all(verdicts, schemes, today=today)) == len(schemes)


def test_the_action_layer_refuses_for_a_citizen_with_no_documents(client):
    """No profile, no application. The action layer will not improvise one."""
    response = client.post(
        "/api/act",
        params={"persona_id": "entrepreneur-02", "scheme_id": "stand-up-india"},
    )
    assert response.status_code == 409
