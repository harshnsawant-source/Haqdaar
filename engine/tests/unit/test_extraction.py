"""Extraction, and every way it is allowed to fail.

The happy path matters least here. What matters is that an unreadable page, a missing
OCR engine, a low-confidence word and a value outside its declared map ALL land on the
same place: no field, therefore UNKNOWN, therefore the existing refusal machinery. None
of them may produce a value.
"""

from pathlib import Path

import pytest

from haqdaar.profile import ocr
from haqdaar.profile.extract import (
    DocumentRules,
    ExtractedField,
    ExtractionMode,
    ExtractionReport,
    build_profile,
    extract_document,
    load_rules,
)
from haqdaar.profile.schema import CONFIDENCE_FLOOR, FieldOrigin, load_profile


@pytest.fixture(scope="module")
def documents_dir(request):
    return request.config.rootpath.parent / "corpus" / "documents"


def word(text, confidence, left=0, top=0):
    return ocr.Word(
        text=text, confidence=confidence, left=left, top=top, width=40, height=12
    )


# --- the rules load ---------------------------------------------------------


def test_document_rules_load(documents_dir: Path):
    rules = load_rules(documents_dir, "caste_certificate")
    assert rules is not None
    assert rules.document_type == "caste_certificate"
    assert any(f.profile_field == "applicant.social_category" for f in rules.fields)


def test_unknown_document_type_extracts_nothing(documents_dir: Path):
    """An unrecognised document is not a crash and not a guess."""
    report = extract_document(
        b"not an image", document_type="mystery_document", documents_dir=documents_dir
    )
    assert report.fields == []
    assert report.readable is False


def test_aadhaar_rules_do_not_extract_the_aadhaar_number(documents_dir: Path):
    """A deliberate absence. We do not hold or transmit Aadhaar numbers."""
    rules = load_rules(documents_dir, "aadhaar")
    paths = {f.profile_field for f in rules.fields}
    assert not any("aadhaar" in p or "uid" in p for p in paths)


# --- OCR unavailable / unreadable -------------------------------------------


def test_missing_ocr_engine_reads_nothing_and_does_not_raise(monkeypatch):
    monkeypatch.setattr(ocr, "tesseract_available", lambda: False)
    result = ocr.read(b"anything")
    assert result.available is False
    assert result.is_readable is False
    assert result.words == []


def test_unreadable_document_yields_unknown_fields(documents_dir: Path, monkeypatch):
    """A blank or corrupt page produces NO fields — never fabricated ones."""
    monkeypatch.setattr(ocr, "tesseract_available", lambda: False)
    report = extract_document(
        b"", document_type="caste_certificate", documents_dir=documents_dir
    )
    assert report.fields == []
    assert report.unread == ["applicant.social_category"]

    profile = build_profile([report], profile_id="p")
    assert profile.fields == {}
    # The evaluator sees nothing, so the predicate will resolve UNKNOWN.
    assert profile.get("applicant.social_category") is None


# --- the confidence gate ----------------------------------------------------


def _report(field: ExtractedField) -> ExtractionReport:
    return ExtractionReport(
        document_id=field.document_id,
        document_type="caste_certificate",
        engine="tesseract",
        ocr_available=True,
        readable=True,
        fields=[field],
    )


def test_low_confidence_field_never_reaches_the_profile():
    """The load-bearing test.

    A field the reader was unsure about must not become a TRUE or FALSE predicate. It
    is dropped here, so the evaluator sees no evidence at all.
    """
    smudged = ExtractedField(
        profile_field="applicant.social_category",
        value="SC",
        confidence=CONFIDENCE_FLOOR - 0.01,
        document_id="caste_certificate",
        source_field="Caste",
    )
    profile = build_profile([_report(smudged)], profile_id="p")
    assert profile.fields == {}
    assert profile.get("applicant.social_category") is None


def test_confident_field_is_kept_and_marked_extracted():
    clear = ExtractedField(
        profile_field="applicant.social_category",
        value="SC",
        confidence=0.96,
        document_id="caste_certificate",
        source_field="Caste",
        region=(10, 20, 40, 12),
    )
    profile = build_profile([_report(clear)], profile_id="p")
    field = profile.get("applicant.social_category")
    assert field.value == "SC"
    assert field.origin is FieldOrigin.EXTRACTED
    assert field.confidence == 0.96
    assert field.region == (10, 20, 40, 12)


def test_the_more_confident_read_wins_when_two_documents_disagree():
    low = _report(
        ExtractedField(
            profile_field="applicant.gender",
            value="MALE",
            confidence=0.80,
            document_id="doc_a",
            source_field="Sex",
        )
    )
    high = _report(
        ExtractedField(
            profile_field="applicant.gender",
            value="FEMALE",
            confidence=0.95,
            document_id="doc_b",
            source_field="Gender",
        )
    )
    profile = build_profile([low, high], profile_id="p")
    assert profile.get("applicant.gender").value == "FEMALE"


# --- value matching refuses to coerce ---------------------------------------


def _match(rule_fields, words):
    from haqdaar.profile.extract import _match_rule

    rules = DocumentRules(
        document_type="t", label="l", fields=[rule_fields]
    )
    return _match_rule(rules.fields[0], words)


def test_value_outside_the_declared_map_is_dropped():
    """A misread that lands outside the map is not snapped to the nearest option."""
    from haqdaar.profile.extract import FieldRule

    rule = FieldRule(
        profile_field="applicant.social_category",
        labels=["caste"],
        value_map={"scheduled caste": "SC"},
    )
    assert _match(rule, [word("Caste", 0.99), word("Schedvled", 0.6)]) is None


def test_number_outside_its_plausibility_window_is_dropped():
    from haqdaar.profile.extract import FieldRule

    rule = FieldRule(
        profile_field="applicant.age",
        labels=["age"],
        numeric=True,
        min_value=1,
        max_value=120,
    )
    assert _match(rule, [word("Age", 0.99), word("870", 0.99)]) is None
    found = _match(rule, [word("Age", 0.99), word("60", 0.98)])
    assert found is not None and found.value == 60


def test_confidence_is_the_weaker_of_label_and_value():
    """Bias to refuse: an uncertain label makes the whole read uncertain."""
    from haqdaar.profile.extract import FieldRule

    rule = FieldRule(
        profile_field="applicant.gender", labels=["gender"], value_map={"female": "FEMALE"}
    )
    found = _match(rule, [word("Gender", 0.55), word("Female", 0.99)])
    assert found.confidence == pytest.approx(0.55)
    assert not found.is_confident  # below the floor, so it will be dropped


# --- fixture fallback -------------------------------------------------------


def test_live_mode_never_borrows_from_the_fixture(corpus_dir):
    fixture = load_profile(
        corpus_dir / "entrepreneur" / "personas" / "entrepreneur-01.json"
    )
    profile = build_profile(
        [], profile_id="p", fixture=fixture, mode=ExtractionMode.LIVE
    )
    assert profile.fields == {}


def test_fixture_backed_mode_labels_every_borrowed_field(corpus_dir):
    fixture = load_profile(
        corpus_dir / "entrepreneur" / "personas" / "entrepreneur-01.json"
    )
    live = _report(
        ExtractedField(
            profile_field="applicant.social_category",
            value="SC",
            confidence=0.97,
            document_id="caste_certificate",
            source_field="Caste",
        )
    )
    profile = build_profile(
        [live], profile_id="p", fixture=fixture, mode=ExtractionMode.FIXTURE_BACKED
    )

    # The live read wins and is marked EXTRACTED.
    assert profile.get("applicant.social_category").origin is FieldOrigin.EXTRACTED
    # Everything else is borrowed and marked FIXTURE. Never blurred.
    assert profile.get("applicant.gender").origin is FieldOrigin.FIXTURE
    assert profile.is_fixture_backed is True


def test_fixture_backed_profile_reproduces_the_golden_verdict(
    corpus_dir, schemes_dir, today
):
    """Demo determinism: with nothing read, the fallback gives the golden result."""
    from haqdaar.corpus.loader import load_corpus
    from haqdaar.eligibility.evaluate import evaluate_corpus
    from haqdaar.eligibility.verdict import Status

    fixture = load_profile(
        corpus_dir / "entrepreneur" / "personas" / "entrepreneur-01.json"
    )
    fallback = build_profile(
        [], profile_id="entrepreneur-01", fixture=fixture,
        mode=ExtractionMode.FIXTURE_ONLY,
    )
    schemes = load_corpus(schemes_dir)

    assert {v.scheme_id: v.status for v in evaluate_corpus(schemes, fallback)} == {
        "nsfdc-term-loan": Status.ELIGIBLE,
        "stand-up-india": Status.ELIGIBLE,
    }
    assert all(f.origin is FieldOrigin.FIXTURE for f in fallback.fields.values())


# --- the real engine, when it is installed ----------------------------------


@pytest.mark.skipif(
    not ocr.tesseract_available(), reason="tesseract binary not installed"
)
def test_real_ocr_reads_a_generated_document(documents_dir: Path, tmp_path: Path):
    """Runs only where the binary exists. Proves the local path end to end."""
    import io

    from PIL import Image, ImageDraw

    image = Image.new("RGB", (600, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 40), "Caste: Scheduled Caste", fill="black")
    draw.text((20, 100), "Gender: Female", fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    report = extract_document(
        buffer.getvalue(),
        document_type="caste_certificate",
        documents_dir=documents_dir,
    )
    assert report.ocr_available is True
    assert report.readable is True
    found = {f.profile_field: f.value for f in report.fields}
    assert found.get("applicant.social_category") == "SC"
