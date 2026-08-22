"""OCR: the only module in Haqdaar that reads a document.

This and `extract.py` are the input boundary. Everything downstream — evaluator, Guard,
renderer, action layer — imports neither, and `tests/unit/test_no_model_in_deterministic
_lane.py` asserts that boundary holds in both directions.

**Local, not cloud.** Tesseract runs on the device. That is the offline pitch made real:
no network, no key, no data leaving the machine a citizen handed their documents to.
Sending a scan of someone's caste certificate to a third-party API to save ourselves
some work would be a poor trade at a Panchayat and an indefensible one on stage.

**Confidence is per word and it is real.** Tesseract reports 0-100 per token; we carry
it through as 0..1 and never round it up. Where OCR is unavailable or the page is
unreadable, this module returns *nothing* — the honest result — and the confidence gate
turns that into UNKNOWN rather than a guess.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class Word:
    """One recognised token, with where it was and how sure the engine was."""

    text: str
    confidence: float  # 0..1
    left: int
    top: int
    width: int
    height: int

    @property
    def region(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.width, self.height)


@dataclass(frozen=True)
class OcrResult:
    words: list[Word]
    engine: str
    available: bool

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def is_readable(self) -> bool:
        return bool(self.words)


UNAVAILABLE = OcrResult(words=[], engine="none", available=False)


def tesseract_available() -> bool:
    """True only when both the Python wrapper and the binary are installed.

    The wrapper alone is not enough, and a missing binary must be a clean False rather
    than an exception at read time — the app degrades to "I could not read this",
    which is a correct answer, not a crash.
    """
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return shutil.which("tesseract") is not None


def read(image_bytes: bytes, *, min_word_confidence: float = 0.0) -> OcrResult:
    """Read an image. Returns UNAVAILABLE rather than raising when OCR cannot run.

    Every failure path here — no wrapper, no binary, corrupt image, engine error —
    lands on "nothing was read". That is deliberate: an unreadable document and an
    absent OCR engine are the same fact to the citizen, and both must produce UNKNOWN
    fields rather than an error page or, far worse, a fabricated value.
    """
    if not tesseract_available():
        return UNAVAILABLE

    import io

    import pytesseract
    from PIL import Image, UnidentifiedImageError

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        return OcrResult(words=[], engine="tesseract", available=True)

    try:
        data = pytesseract.image_to_data(
            image, output_type=pytesseract.Output.DICT
        )
    except Exception:  # pytesseract raises a family of errors; none should crash a demo
        return OcrResult(words=[], engine="tesseract", available=True)

    words: list[Word] = []
    for i, raw_text in enumerate(data.get("text", [])):
        text = (raw_text or "").strip()
        if not text:
            continue
        try:
            confidence = float(data["conf"][i]) / 100.0
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        if confidence < 0:  # tesseract uses -1 for "no confidence"
            continue
        if confidence < min_word_confidence:
            continue
        words.append(
            Word(
                text=text,
                confidence=confidence,
                left=int(data["left"][i]),
                top=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
            )
        )

    return OcrResult(words=words, engine="tesseract", available=True)
