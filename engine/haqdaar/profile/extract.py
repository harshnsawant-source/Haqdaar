"""Documents in, CitizenProfile out. The input boundary, and nothing more.

This module and `ocr.py` are the only ones that touch a reading engine. What comes out
is typed facts with real confidence and real provenance; what happens next is the same
deterministic evaluator, Guard and template renderer as always. Extraction cannot write
an eligibility value, a verdict, or a sentence a citizen reads.

**No generative model is involved, and that is a deliberate upgrade on the plan.** The
design doc budgeted one generative call here. It turned out not to be needed: local OCR
plus per-document parsing rules does the job, which means Haqdaar now has *zero*
generative calls anywhere. Every fact a citizen sees is read off their document by
Tesseract and matched against a declared rule; nothing is written by a model at any
point in the system. The cost is that we only read documents we have rules for — and an
unrecognised document extracts nothing, which lands on UNKNOWN, which is honest.

**The confidence gate is the whole safety story.** A word Tesseract was unsure about,
a value outside its declared map, a number outside its plausibility window: all are
dropped, not coerced. A dropped field is invisible to `CitizenProfile.get()`, so the
evaluator sees no evidence and the predicate resolves UNKNOWN, and T1/T2 turn that into
a refusal or a blocked-on-document. An OCR misread can therefore cost us a *yes we
could have proven*. It cannot produce a confident wrong answer.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from haqdaar.profile import ocr
from haqdaar.profile.schema import (
    CONFIDENCE_FLOOR,
    CitizenProfile,
    FieldOrigin,
    ProfileField,
)


class ExtractionMode(str, Enum):
    """How a profile was assembled. Always shown, never inferred silently."""

    #: Only what was read from the documents. Unreadable fields stay UNKNOWN.
    LIVE = "LIVE"
    #: Read where confident, checked-in fixture elsewhere, every field labelled.
    FIXTURE_BACKED = "FIXTURE_BACKED"
    #: Nothing was read at all; the whole profile is the fixture.
    FIXTURE_ONLY = "FIXTURE_ONLY"


class FieldRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_field: str
    labels: list[str] = Field(min_length=1)
    value_map: dict[str, str] = Field(default_factory=dict)
    numeric: bool = False
    min_value: float | None = None
    max_value: float | None = None


class DocumentRules(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document_type: str
    label: str
    fields: list[FieldRule] = Field(min_length=1)


class ExtractedField(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_field: str
    value: bool | int | float | str
    confidence: float
    document_id: str
    source_field: str
    region: tuple[int, int, int, int] | None = None

    @property
    def is_confident(self) -> bool:
        return self.confidence >= CONFIDENCE_FLOOR


class ExtractionReport(BaseModel):
    """What the reader actually managed to do. Shown on screen, not hidden."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    document_type: str
    engine: str
    ocr_available: bool
    readable: bool
    fields: list[ExtractedField] = Field(default_factory=list)
    #: Fields the rules looked for and did not find or could not trust.
    unread: list[str] = Field(default_factory=list)


def load_rules(documents_dir: str | Path, document_type: str) -> DocumentRules | None:
    path = Path(documents_dir) / f"{document_type}.yaml"
    if not path.is_file():
        return None
    return DocumentRules.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )


def _normalise(text: str) -> str:
    return "".join(c for c in text.lower() if c.isalnum() or c.isspace()).strip()


def _match_rule(rule: FieldRule, words: list[ocr.Word]) -> ExtractedField | None:
    """Find `rule`'s value near one of its labels. Returns None when unsure.

    Every ambiguity resolves to None. There is no nearest-match, no fuzzy coercion and
    no default: a value we cannot read is a value we do not have.
    """
    normalised = [_normalise(w.text) for w in words]

    for index, token in enumerate(normalised):
        if not token:
            continue
        # A label may be one or two words ("year of birth" is matched on its head).
        if not any(token == _normalise(lbl).split()[0] for lbl in rule.labels):
            continue

        # Look just to the right of the label; a labelled field's value is adjacent.
        for offset in range(1, 5):
            position = index + offset
            if position >= len(words):
                break
            candidate = words[position]
            candidate_text = normalised[position]
            if not candidate_text:
                continue

            value: bool | int | float | str | None = None
            if rule.numeric:
                digits = "".join(c for c in candidate.text if c.isdigit())
                if not digits:
                    continue
                number = int(digits)
                if rule.min_value is not None and number < rule.min_value:
                    continue  # a misread, not a person
                if rule.max_value is not None and number > rule.max_value:
                    continue
                value = number
            else:
                value = rule.value_map.get(candidate_text)
                if value is None:
                    continue  # outside the declared map: dropped, never coerced

            # Confidence is the label's and the value's, whichever the engine was
            # *less* sure of. Bias to refuse.
            confidence = min(words[index].confidence, candidate.confidence)
            return ExtractedField(
                profile_field=rule.profile_field,
                value=value,
                confidence=confidence,
                document_id="",  # filled by the caller, which knows the document
                source_field=words[index].text,
                region=candidate.region,
            )
    return None


def extract_document(
    image_bytes: bytes,
    *,
    document_type: str,
    documents_dir: str | Path,
    document_id: str | None = None,
) -> ExtractionReport:
    """Read one document. Never raises on an unreadable page or a missing engine."""
    document_id = document_id or document_type
    rules = load_rules(documents_dir, document_type)
    if rules is None:
        return ExtractionReport(
            document_id=document_id,
            document_type=document_type,
            engine="none",
            ocr_available=ocr.tesseract_available(),
            readable=False,
            unread=[],
        )

    result = ocr.read(image_bytes)
    found: list[ExtractedField] = []
    unread: list[str] = []
    for rule in rules.fields:
        match = _match_rule(rule, result.words) if result.is_readable else None
        if match is None:
            unread.append(rule.profile_field)
            continue
        found.append(match.model_copy(update={"document_id": document_id}))

    return ExtractionReport(
        document_id=document_id,
        document_type=document_type,
        engine=result.engine,
        ocr_available=result.available,
        readable=result.is_readable,
        fields=found,
        unread=unread,
    )


def build_profile(
    reports: list[ExtractionReport],
    *,
    profile_id: str,
    fixture: CitizenProfile | None = None,
    mode: ExtractionMode = ExtractionMode.LIVE,
) -> CitizenProfile:
    """Assemble a profile from extraction reports, optionally fixture-backed.

    In LIVE mode the profile contains only what was read. In FIXTURE_BACKED mode a
    field the reader could not supply falls back to the checked-in fixture value —
    and is tagged FIXTURE, so the screen can say which values were read and which were
    typed. The two are never blurred: a fixture value is never presented as a live
    read, and a live read is never overwritten by a fixture.
    """
    fields: dict[str, ProfileField] = {}

    for report in reports:
        for extracted in report.fields:
            if not extracted.is_confident:
                continue  # below the floor: treated as unread, not as a value
            existing = fields.get(extracted.profile_field)
            if existing is not None and existing.confidence >= extracted.confidence:
                continue
            fields[extracted.profile_field] = ProfileField(
                value=extracted.value,
                document_id=extracted.document_id,
                source_field=extracted.source_field,
                confidence=extracted.confidence,
                origin=FieldOrigin.EXTRACTED,
                region=extracted.region,
            )

    if mode is not ExtractionMode.LIVE and fixture is not None:
        for path, field in fixture.fields.items():
            if path in fields:
                continue  # a live read always wins over a fixture
            fields[path] = field.model_copy(update={"origin": FieldOrigin.FIXTURE})

    return CitizenProfile(profile_id=profile_id, fields=fields)
