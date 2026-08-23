"""Bounds and sniffing for uploaded documents.

Threat model: this runs on a shared laptop at a Panchayat or CSC, handling caste
certificates, land records and income documents for people with very little margin for
error. The adversary is mostly not a hacker — it is a malformed phone photo, a 10,000 x
10,000 scan, and the next person to touch the machine.

Every rejection here lands on the same calm behaviour as an unreadable page: the
citizen is told the document could not be read, never shown a stack trace, and never
given a fabricated value in place of one.
"""

from __future__ import annotations

#: Per file. Chosen to fit a phone photo of a document (a 12 MP JPEG is ~3-4 MB) while
#: bounding worst-case memory at MAX_FILES x this. Also pinned to the multipart
#: parser's spool threshold in app.py so an accepted file never touches disk.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

#: A citizen brings a handful of papers, not a directory. Bounds total memory to ~20 MB.
MAX_UPLOAD_FILES = 4

#: Total request size, checked from Content-Length before the body is parsed.
#: Slack over MAX_FILES x MAX_UPLOAD_BYTES for multipart framing overhead.
MAX_REQUEST_BYTES = MAX_UPLOAD_FILES * MAX_UPLOAD_BYTES + (1024 * 1024)

#: Image types we can actually read. Anything else is refused rather than guessed at.
ALLOWED_CONTENT_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff", "image/bmp"}
)

#: Magic-byte prefixes for those same types. The declared content type is a claim by
#: the client; these are the file itself. Both must agree before we open anything.
_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
)


class UploadRejected(Exception):
    """An upload we will not open. Carries the status the API should return."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def sniff(payload: bytes) -> str | None:
    """Identify a file by its own bytes. WEBP needs the RIFF container checked."""
    for prefix, media_type in _MAGIC:
        if payload.startswith(prefix):
            return media_type
    if payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        return "image/webp"
    return None


def check_count(files: list, document_types: list) -> None:
    if len(files) > MAX_UPLOAD_FILES:
        raise UploadRejected(
            413, f"too many files: at most {MAX_UPLOAD_FILES} documents at a time"
        )
    if len(document_types) != len(files):
        raise UploadRejected(422, "each uploaded file needs a matching document_type")


def check_content_length(header: str | None) -> None:
    """Reject an oversized request before its body is parsed into memory."""
    if header is None:
        return
    try:
        declared = int(header)
    except ValueError:
        return
    if declared > MAX_REQUEST_BYTES:
        raise UploadRejected(413, "upload too large")


async def read_bounded(upload) -> bytes:
    """Read one upload, refusing to hold more than the cap.

    Reads one byte past the limit and stops: an oversized file is rejected without
    ever materialising the whole thing, so a hostile or accidental 500 MB scan cannot
    exhaust memory on a cheap laptop.
    """
    payload = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise UploadRejected(
            413,
            f"{upload.filename or 'file'} is larger than "
            f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )
    return payload


def check_type(upload, payload: bytes) -> None:
    """The declared type and the actual bytes must both be an image we support.

    Relying on the image library to throw is not enough: a file that merely fails to
    parse is indistinguishable from a corrupt scan, and we would rather tell the
    citizen "that is not a document photo" than "I could not read it".
    """
    declared = (upload.content_type or "").split(";")[0].strip().lower()
    if declared and declared not in ALLOWED_CONTENT_TYPES:
        raise UploadRejected(415, f"unsupported file type: {declared}")

    actual = sniff(payload)
    if actual is None:
        raise UploadRejected(415, "that file is not an image we can read")
    if actual not in ALLOWED_CONTENT_TYPES:
        raise UploadRejected(415, f"unsupported image format: {actual}")
