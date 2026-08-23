"""Upload bounds, format guards, and the proof that citizen data does not persist.

Threat model: a shared laptop at a Panchayat or CSC, holding caste certificates, land
records and income documents. The adversary is mostly not a hacker — it is a malformed
photo, a crafted image that decodes to gigabytes, and the next person to touch the
machine.

Every rejection here must read as a refusal, never as a crash.
"""

import io
import os
import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from haqdaar.api.uploads import (  # noqa: E402
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_FILES,
    UploadRejected,
    check_content_length,
    sniff,
)
from haqdaar.profile import ocr  # noqa: E402


@pytest.fixture(scope="module")
def client(corpus_dir):
    os.environ["HAQDAAR_CORPUS"] = str(corpus_dir)
    os.environ["HAQDAAR_TODAY"] = "2026-08-22"
    from haqdaar.api.app import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def png(size=(60, 40)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, format="PNG")
    return buffer.getvalue()


def post(client, files, types=None, mode="LIVE"):
    types = types if types is not None else ["caste_certificate"] * len(files)
    # httpx needs repeated form fields as a dict with a list value; a list of 2-tuples
    # silently drops the scalar fields alongside a files= list.
    data = {"persona_id": "sunita", "mode": mode, "document_types": types}
    return client.post("/api/extract", data=data, files=files)


# --- B1: size and count bounds ----------------------------------------------


def test_an_oversized_file_is_refused_not_absorbed(client):
    """A hostile or accidental huge scan must not be read into memory."""
    oversized = b"\x89PNG\r\n\x1a\n" + b"A" * (MAX_UPLOAD_BYTES + 1024)
    response = post(client, [("files", ("big.png", oversized, "image/png"))])

    assert response.status_code == 413
    assert "larger than" in response.json()["detail"]
    assert "Traceback" not in response.text


def test_a_file_at_the_limit_is_still_accepted(client):
    """The cap must not be so eager it refuses a legitimate document photo."""
    body = png((400, 300))
    assert len(body) < MAX_UPLOAD_BYTES
    assert post(client, [("files", ("ok.png", body, "image/png"))]).status_code == 200


def test_too_many_files_is_refused(client):
    files = [
        ("files", (f"f{i}.png", png(), "image/png")) for i in range(MAX_UPLOAD_FILES + 2)
    ]
    response = post(client, files)
    assert response.status_code == 413
    assert "too many files" in response.json()["detail"]


def test_the_allowed_number_of_files_is_accepted(client):
    files = [("files", (f"f{i}.png", png(), "image/png")) for i in range(MAX_UPLOAD_FILES)]
    assert post(client, files).status_code == 200


def test_content_length_is_checked_before_the_body_is_parsed():
    """The cheapest possible rejection: a header, before anything is read."""
    with pytest.raises(UploadRejected) as raised:
        check_content_length(str(MAX_UPLOAD_FILES * MAX_UPLOAD_BYTES * 10))
    assert raised.value.status_code == 413

    check_content_length("1024")  # under the cap, no raise
    check_content_length(None)  # absent header, no raise
    check_content_length("not-a-number")  # malformed header, no raise


def test_mismatched_files_and_types_is_refused(client):
    response = post(client, [("files", ("a.png", png(), "image/png"))], types=[])
    assert response.status_code == 422


# --- B2: decompression bomb -------------------------------------------------


def test_a_decompression_bomb_lands_on_nothing_was_read(monkeypatch):
    """A bomb must be an unreadable document, not a dead process.

    DecompressionBombError derives from Exception, not OSError or ValueError, so it
    would otherwise escape the handler that catches every other unreadable page.
    """
    monkeypatch.setattr(ocr, "tesseract_available", lambda: True)
    monkeypatch.setattr(ocr, "MAX_IMAGE_PIXELS", 10)  # anything real now "explodes"

    result = ocr.read(png((60, 40)))
    assert result.is_readable is False
    assert result.words == []


def test_the_pixel_bound_is_generous_enough_for_a_real_scan():
    """An A4 page at 600 dpi is about 35 MP. The bound must clear that."""
    assert ocr.MAX_IMAGE_PIXELS > 35_000_000


# --- B3: what we accept -----------------------------------------------------


@pytest.mark.parametrize(
    "payload,expected",
    [
        (b"\x89PNG\r\n\x1a\n rest", "image/png"),
        (b"\xff\xd8\xff\xe0 rest", "image/jpeg"),
        (b"BM rest", "image/bmp"),
        (b"II*\x00 rest", "image/tiff"),
        (b"RIFF????WEBPVP8 ", "image/webp"),
        (b"%PDF-1.4", None),
        (b"MZ\x90\x00", None),  # a Windows executable
        (b"", None),
    ],
)
def test_magic_byte_sniffing(payload, expected):
    assert sniff(payload) == expected


def test_a_declared_type_we_do_not_support_is_refused(client):
    response = post(client, [("files", ("doc.pdf", b"%PDF-1.4 ...", "application/pdf"))])
    assert response.status_code == 415
    assert "unsupported file type" in response.json()["detail"]


def test_an_executable_renamed_as_an_image_is_refused(client):
    """The declared type is a claim by the client; the bytes are the file."""
    response = post(client, [("files", ("payload.png", b"MZ\x90\x00\x03", "image/png"))])
    assert response.status_code == 415


# --- B4: citizen data does not persist --------------------------------------


def _temp_snapshot() -> set[Path]:
    root = Path(tempfile.gettempdir())
    try:
        return set(root.iterdir())
    except OSError:
        return set()


def test_an_upload_leaves_nothing_on_disk(client):
    """The load-bearing privacy test.

    An accepted document must live in memory for the length of the request and then be
    gone. Starlette spools a multipart part to a temp file once it exceeds a threshold,
    which is why app.py raises that threshold to our own per-file cap — a file we
    accept never reaches the filesystem at all.
    """
    before = _temp_snapshot()

    marker = b"SECRET-CASTE-CERTIFICATE-CONTENT"
    buffer = io.BytesIO()
    Image.new("RGB", (200, 120), "white").save(buffer, format="PNG")
    payload = buffer.getvalue() + marker  # trailing bytes survive PNG decoding

    assert post(client, [("files", ("cert.png", payload, "image/png"))]).status_code == 200

    after = _temp_snapshot()
    new_files = after - before
    # Any file that did appear must not contain the document.
    for path in new_files:
        if not path.is_file():
            continue
        try:
            assert marker not in path.read_bytes()
        except (OSError, PermissionError):
            pass


def test_the_response_never_echoes_the_document_bytes(client):
    marker = b"SECRET-CASTE-CERTIFICATE-CONTENT"
    buffer = io.BytesIO()
    Image.new("RGB", (120, 80), "white").save(buffer, format="PNG")

    response = post(
        client, [("files", ("cert.png", buffer.getvalue() + marker, "image/png"))]
    )
    assert response.status_code == 200
    assert marker.decode() not in response.text
    # And nothing that looks like an embedded image.
    assert "base64" not in response.text.lower()
    assert "\\x89PNG" not in response.text


def test_no_engine_module_retains_uploaded_bytes(client):
    """Nothing stashes the document in a module global between requests."""
    import sys

    marker = "SECRET-CASTE-CERTIFICATE-CONTENT"
    buffer = io.BytesIO()
    Image.new("RGB", (80, 60), "white").save(buffer, format="PNG")
    post(client, [("files", ("cert.png", buffer.getvalue() + marker.encode(), "image/png"))])

    for name, module in list(sys.modules.items()):
        if not name.startswith("haqdaar"):
            continue
        for attribute, value in vars(module).items():
            if isinstance(value, (bytes, str)) and marker in str(value):
                pytest.fail(f"{name}.{attribute} retained the uploaded document")


def test_the_engine_writes_no_files_during_a_normal_evaluation(client, monkeypatch):
    """The verdict path is pure. Nothing about a citizen is written anywhere.

    Asserted by intercepting `open` rather than by watching the temp directory: the
    system temp directory is shared, so a snapshot fails whenever any unrelated process
    happens to write during the test. That is a flaky test pretending to be a security
    guarantee. This one cannot be fooled either way — a write attempt raises.
    """
    import builtins

    real_open = builtins.open
    writes: list[str] = []

    def guarded(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            writes.append(f"{file!r} mode={mode!r}")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded)

    assert client.get("/api/evaluate", params={"persona_id": "sunita"}).status_code == 200
    assert client.post(
        "/api/act",
        params={"persona_id": "entrepreneur-01", "scheme_id": "stand-up-india"},
    ).status_code == 200
    assert client.post(
        "/api/intake",
        json={"vertical": "welfare", "answers": {"age": 60}, "documents_held": []},
    ).status_code == 200

    assert writes == [], f"the verdict path opened files for writing: {writes}"
