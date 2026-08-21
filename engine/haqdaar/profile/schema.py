"""The citizen profile: typed facts, each carrying its provenance.

Design doc s4. Every field names the document it came from. A value with no document
behind it cannot make a predicate TRUE or FALSE — that invariant is what stops the
engine from asserting anything it cannot show a source for.

This module is deliberately model-free. Day 6 adds extract.py and ocr.py alongside it;
the deterministic lane will still import only this file.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

#: Values below this are treated as unread by the extractor and fall back to the
#: checked-in fixture (design doc s7). Day 1 fixtures are all 1.0.
CONFIDENCE_FLOOR = 0.75


class ProfileField(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: bool | int | float | str
    #: The document this value was read from. Required: no document, no evidence.
    document_id: str
    #: Where in that document it was read from, for the proof trail.
    source_field: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

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


def load_profile(path: str | Path) -> CitizenProfile:
    """Load a checked-in fixture profile (corpus/personas/*.json)."""
    return CitizenProfile.model_validate(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )
