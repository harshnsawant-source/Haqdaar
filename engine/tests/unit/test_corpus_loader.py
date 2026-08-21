"""Corpus loading, and the guards that stop unverified rules reaching a citizen."""

from pathlib import Path

import pytest

from haqdaar.corpus.loader import CorpusError, load_corpus, load_scheme
from haqdaar.corpus.schema import Clause, RuleType, VerificationStatus


def test_day_one_corpus_loads(schemes_dir: Path):
    schemes = load_corpus(schemes_dir)
    assert [s.scheme_id for s in schemes] == ["nsfdc-term-loan", "stand-up-india"]


def test_strict_mode_yields_nothing_yet(schemes_dir: Path):
    """Tripwire. This changes the day the content lane lands a VERIFIED rule.

    If this assertion starts failing, that is good news — update it to name the
    scheme that got verified.
    """
    assert load_corpus(schemes_dir, strict=True) == []


def test_every_day_one_clause_is_marked_provisional(schemes_dir: Path):
    for scheme in load_corpus(schemes_dir):
        assert scheme.verification_status is VerificationStatus.PROVISIONAL
        for clause in scheme.clauses():
            assert clause.verification_status is VerificationStatus.PROVISIONAL
            assert "[VERIFY AT SOURCE]" in clause.clause_text
            assert clause.verify_note


def test_provisional_clause_without_the_marker_is_rejected():
    with pytest.raises(ValueError, match="VERIFY AT SOURCE"):
        Clause(
            clause_id="X",
            clause_text="The applicant must be a widow.",  # no marker
            rule_type=RuleType.ENUMERATED_CATEGORY,
            profile_field="applicant.category",
            bound={"values": ["WIDOW"]},
            verification_status=VerificationStatus.PROVISIONAL,
            verify_note="unsourced",
        )


def test_discretionary_clause_cannot_claim_a_document():
    """The refusal must stay structural: no document may settle a discretionary rule."""
    with pytest.raises(ValueError, match="empty verifiable_from"):
        Clause(
            clause_id="X",
            clause_text="[VERIFY AT SOURCE] Subject to bank appraisal.",
            rule_type=RuleType.DISCRETIONARY,
            decided_by="the bank",
            verifiable_from=["sanction_letter"],
            verification_status=VerificationStatus.PROVISIONAL,
            verify_note="unsourced",
        )


def test_discretionary_clause_must_name_its_decider():
    with pytest.raises(ValueError, match="decided_by"):
        Clause(
            clause_id="X",
            clause_text="[VERIFY AT SOURCE] Subject to appraisal.",
            rule_type=RuleType.DISCRETIONARY,
            verification_status=VerificationStatus.PROVISIONAL,
            verify_note="unsourced",
        )


def test_bound_shape_must_match_rule_type():
    with pytest.raises(ValueError, match="requires a NumericBound"):
        Clause(
            clause_id="X",
            clause_text="[VERIFY AT SOURCE] Age 18 to 65.",
            rule_type=RuleType.NUMERIC_BOUND,
            profile_field="applicant.age",
            bound={"values": ["18-65"]},
            verification_status=VerificationStatus.PROVISIONAL,
            verify_note="unsourced",
        )


def test_unreadable_scheme_raises_corpus_error(tmp_path: Path):
    bad = tmp_path / "broken.yaml"
    bad.write_text("scheme_id: x\nname: [unclosed", encoding="utf-8")
    with pytest.raises(CorpusError):
        load_scheme(bad)
