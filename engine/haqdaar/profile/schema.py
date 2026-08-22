"""The citizen profile: typed facts, each carrying its provenance.

Design doc s4. Every field names the document it came from. A value with no document
behind it cannot make a predicate TRUE or FALSE — that invariant is what stops the
engine from asserting anything it cannot show a source for.

This module is deliberately model-free. Day 6 adds extract.py and ocr.py alongside it;
the deterministic lane will still import only this file.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

#: Values below this are treated as unread (design doc s7). A field under the floor is
#: invisible to `get()`, so the evaluator sees no evidence and the predicate resolves
#: UNKNOWN. An OCR misread therefore surfaces as "I could not read this", never as a
#: confident wrong answer.
CONFIDENCE_FLOOR = 0.75


class FieldOrigin(str, Enum):
    """Where a value came from. Must be visible; never blurred.

    A fixture value presented as a live read, or a live read presented as a fixture,
    are both lies about what the machine actually did.
    """

    #: Read from a document the citizen supplied, this run.
    EXTRACTED = "EXTRACTED"
    #: Taken from a checked-in demo fixture (typed by hand, not read).
    FIXTURE = "FIXTURE"


class ProfileField(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: bool | int | float | str
    #: The document this value was read from. Required: no document, no evidence.
    document_id: str
    #: Where in that document it was read from, for the proof trail.
    source_field: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    origin: FieldOrigin = FieldOrigin.FIXTURE
    #: Pixel box (left, top, width, height) the value was read from, when extracted.
    region: tuple[int, int, int, int] | None = None

    @property
    def is_confident(self) -> bool:
        return self.confidence >= CONFIDENCE_FLOOR


class CitizenProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str
    #: Dotted path -> field, e.g. "applicant.social_category".
    fields: dict[str, ProfileField] = Field(default_factory=dict)
    description: str | None = None

    def get(self, path: str) -> ProfileField | None:
        """Return the field at `path`, or None if absent or not confidently read."""
        field = self.fields.get(path)
        if field is None or not field.is_confident:
            return None
        return field

    def document_ids(self) -> set[str]:
        return {f.document_id for f in self.fields.values()}

    def origins(self) -> dict[str, FieldOrigin]:
        return {path: field.origin for path, field in self.fields.items()}

    @property
    def is_fixture_backed(self) -> bool:
        """True when any value shown to the citizen was typed rather than read."""
        return any(f.origin is FieldOrigin.FIXTURE for f in self.fields.values())


def load_profile(path: str | Path) -> CitizenProfile:
    """Load a checked-in fixture profile (corpus/personas/*.json)."""
    return CitizenProfile.model_validate(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )
