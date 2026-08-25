"""Corpus loading, and the guards that stop unverified rules reaching a citizen."""

from pathlib import Path

import pytest

from haqdaar.corpus.loader import CorpusError, load_corpus, load_scheme
from haqdaar.corpus.schema import Clause, RuleType, VerificationStatus


def test_day_one_corpus_loads(schemes_dir: Path):
    schemes = load_corpus(schemes_dir)
    assert [s.scheme_id for s in schemes] == [
        "nsfdc-term-loan",
        "stand-up-india",
        "vcf-sc",
    ]


#: Schemes whose clause text has been transcribed verbatim from an official
#: government page. The tripwire below names them one by one on purpose: adding a
#: scheme here is a deliberate act that says a human read the source, and a scheme
#: cannot drift into the verified set by accident.
VERIFIED_SCHEMES = {"stand-up-india", "nsfdc-term-loan"}


def test_strict_mode_yields_only_the_schemes_we_have_actually_read(schemes_dir: Path):
    """The tripwire fired on 2026-08-26, which is what it was built for.

    It used to assert that strict mode yielded nothing at all. Stand-Up India is now
    transcribed verbatim from standupmitra.in and financialservices.gov.in, so the
    assertion becomes the stricter one: strict mode yields exactly the schemes we can
    name, and nothing else.
    """
    assert {s.scheme_id for s in load_corpus(schemes_dir, strict=True)} == {
        s for s in VERIFIED_SCHEMES if (schemes_dir / f"{s}.yaml").is_file()
    }


def test_every_unverified_clause_still_carries_the_marker(schemes_dir: Path):
    """The rule that has not changed: anything unread is loudly labelled unread.

    A verified scheme must carry no [VERIFY AT SOURCE] marker anywhere, and an
    unverified one must carry it on every clause. The dangerous state is a scheme
    marked VERIFIED that still contains a paraphrase nobody checked, so both
    directions are asserted.
    """
    for scheme in load_corpus(schemes_dir):
        verified = scheme.scheme_id in VERIFIED_SCHEMES
        expected = (
            VerificationStatus.VERIFIED if verified else VerificationStatus.PROVISIONAL
        )
        assert scheme.verification_status is expected, scheme.scheme_id
        for clause in scheme.clauses():
            assert clause.verification_status is expected, clause.clause_id
            assert clause.verify_note
            if verified:
                assert "[VERIFY AT SOURCE]" not in clause.clause_text, clause.clause_id
            else:
                assert "[VERIFY AT SOURCE]" in clause.clause_text, clause.clause_id


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
