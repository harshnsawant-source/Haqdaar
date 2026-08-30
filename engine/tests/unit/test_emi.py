"""The instalment calculator.

SIH26092 asks for a projected-EMI tool "accounting for specific scheme guidelines like
maximum loan limits, interest rates and moratorium periods". These tests pin the three
things that make it honest rather than merely arithmetically correct:

1. It amortises at the frequency the scheme states. Every NSFDC product repays
   QUARTERLY, and a monthly amortisation would be wrong for all of them.
2. It refuses above the scheme ceiling instead of producing a number for a loan that
   scheme cannot make.
3. It reports what the source never said. No NSFDC page states whether interest runs
   during the moratorium, and that unknown must reach the screen rather than be
   silently resolved.
"""

from decimal import Decimal

import pytest

from haqdaar.corpus.loader import load_corpus
from haqdaar.corpus.schema import InstalmentFrequency
from haqdaar.finance.emi import (
    IllustrationRefused,
    illustrate,
    max_loan_for_project,
)

CORPUS = "corpus"


def _scheme(vertical: str, scheme_id: str):
    for scheme in load_corpus(f"{CORPUS}/{vertical}/schemes"):
        if scheme.scheme_id == scheme_id:
            return scheme
    raise AssertionError(f"{scheme_id} not in {vertical}")


@pytest.fixture
def micro():
    return _scheme("entrepreneur", "nsfdc-micro-finance").credit_terms


@pytest.fixture
def term():
    return _scheme("entrepreneur", "nsfdc-term-loan").credit_terms


@pytest.fixture
def education():
    return _scheme("student", "nsfdc-educational-loan").credit_terms


def test_the_three_schemes_the_problem_statement_names_carry_terms(micro, term, education):
    for terms in (micro, term, education):
        assert terms is not None


def test_it_amortises_quarterly_because_that_is_what_the_scheme_says(micro):
    # Three years including a three-month moratorium leaves 33 paying months, which is
    # 11 whole quarters. A monthly reading would have said 33 instalments.
    result = illustrate(micro, 100000)
    assert result.frequency is InstalmentFrequency.QUARTERLY
    assert result.instalment_count == 11


def test_the_instalment_matches_the_amortisation_formula(micro):
    # 6.5% a year is 1.625% a quarter over 11 quarters on Rs 1,00,000.
    result = illustrate(micro, 100000)
    principal = Decimal(100000)
    rate = Decimal("6.5") / Decimal(100) / Decimal(4)
    growth = (1 + rate) ** 11
    expected = principal * rate * growth / (growth - 1)
    assert abs(result.instalment_amount - expected) < Decimal("0.01")
    assert result.total_repayable > principal
    assert result.total_interest == result.total_repayable - result.principal


def test_it_refuses_a_loan_above_the_scheme_ceiling(micro):
    # The micro finance scheme lends up to Rs 1.25 lakh. Rs 1.40 lakh is the UNIT COST
    # ceiling, and asking for it as a loan is the exact confusion the PS describes.
    with pytest.raises(IllustrationRefused) as caught:
        illustrate(micro, 140000)
    assert "1.25 lakh" in str(caught.value)


def test_it_refuses_a_nonsense_amount(micro):
    with pytest.raises(IllustrationRefused):
        illustrate(micro, 0)
    with pytest.raises(IllustrationRefused):
        illustrate(micro, -5000)


def test_it_reports_the_moratorium_interest_it_was_never_told(micro, term):
    for terms in (micro, term):
        result = illustrate(terms, 100000)
        assert any("moratorium" in u for u in result.unknowns), result.unknowns


def test_the_educational_loan_admits_it_does_not_know_its_moratorium(education):
    # Its moratorium is "course period plus 01 year", which depends on a course length
    # the corpus does not hold, so moratorium_months is absent by design.
    assert education.moratorium_months is None
    result = illustrate(education, 500000)
    assert any("course" in u for u in result.unknowns), result.unknowns


def test_the_term_loan_costs_more_per_rupee_than_micro_finance(micro, term):
    # 8% against 6.5%. A sanity check that the rates are wired to the right schemes.
    small = illustrate(micro, 100000)
    large = illustrate(term, 100000)
    assert large.annual_rate_pct > small.annual_rate_pct


def test_monthly_equivalent_is_derived_not_charged(micro):
    result = illustrate(micro, 100000)
    assert result.monthly_equivalent * 3 == pytest.approx(
        result.instalment_amount, abs=Decimal("0.03")
    )


def test_the_smaller_of_the_two_lending_limits_wins(micro):
    # 90% of a Rs 1.00 lakh project is Rs 90,000, which is under the ceiling.
    assert max_loan_for_project(micro, 100000) == Decimal("90000.00")
    # 90% of a Rs 1.40 lakh project is Rs 1.26 lakh, which is OVER the Rs 1.25 lakh
    # ceiling, so the ceiling wins. This is the case the corpus header warns about.
    assert max_loan_for_project(micro, 140000) == Decimal("125000.00")


def test_a_pension_has_no_credit_terms_and_is_not_made_to_invent_any():
    ignwps = _scheme("welfare", "ignwps")
    assert ignwps.credit_terms is None


def test_the_evaluator_does_not_import_the_calculator():
    """Eligibility must not be able to depend on what a loan costs.

    Parsed, not grepped. The first version of this test searched the source for the
    string "emi" and matched the word "emitting" in a comment, which is a test that
    fails for a reason having nothing to do with the rule it protects.
    """
    import ast

    import haqdaar.eligibility.evaluate as evaluate

    tree = ast.parse(open(evaluate.__file__, encoding="utf-8").read())
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    assert not any("finance" in name for name in imported), imported
