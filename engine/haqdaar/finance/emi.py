"""The instalment calculator, which is an ILLUSTRATION and never a quote.

SIH26092 asks for "a dynamic tool to calculate projected EMIs, accounting for specific
scheme guidelines like maximum loan limits, interest rates and moratorium periods".
This is that tool, built the way the rest of this engine is built: it computes only
what the corpus can source, and it says out loud what it had to assume and what the
source never stated.

WHY THIS IS NOT CALLED AN EMI
-----------------------------
Every NSFDC product in the corpus repays in QUARTERLY instalments. "EMI" means equated
MONTHLY instalment, and a monthly amortisation would be wrong for all of them. The
calculator uses the frequency the scheme actually states and names it in the result. A
monthly figure is offered only as `monthly_equivalent`, clearly derived, because a
citizen budgets by the month even when the bank collects by the quarter.

WHAT IT REFUSES TO DO
---------------------
* No loan above the scheme's stated ceiling. That is not a rounding matter; it is a
  different product, and quietly amortising it would invent an entitlement.
* No interest accrual through the moratorium. Not one NSFDC page says whether interest
  accrues while repayment is deferred, and the choice moves the total by real money.
  So the moratorium is excluded from the paying periods, and the result carries an
  explicit unknown saying the true total may be higher. Picking a convention silently
  is exactly the failure this project exists to avoid.
* No advice. It returns arithmetic, never "you can afford this".

IT MUST NEVER REACH THE EVALUATOR. Eligibility is decided by clauses; this module is
downstream of a verdict and cannot influence one. `evaluate.py` does not import it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, getcontext

from haqdaar.corpus.schema import CreditTerms, InstalmentFrequency, MoratoriumInterest

# Enough precision that repeated compounding does not drift before we round to paise.
getcontext().prec = 28

_PAISE = Decimal("0.01")

PERIODS_PER_YEAR: dict[InstalmentFrequency, int] = {
    InstalmentFrequency.MONTHLY: 12,
    InstalmentFrequency.QUARTERLY: 4,
    InstalmentFrequency.HALF_YEARLY: 2,
}


class IllustrationRefused(Exception):
    """Raised when the calculator will not produce a figure.

    Carries a citizen-readable reason, because the API surfaces it directly and a
    refusal a person cannot read is the same as no refusal at all.
    """


@dataclass(frozen=True)
class Illustration:
    """One repayment illustration. Every figure is derived, none is promised."""

    principal: Decimal
    annual_rate_pct: Decimal
    frequency: InstalmentFrequency
    instalment_count: int
    instalment_amount: Decimal
    total_repayable: Decimal
    total_interest: Decimal
    repayment_months: int
    moratorium_months: int | None
    #: What we had to decide that the source did not decide for us.
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    #: What the source never stated, and which therefore moves the real number.
    unknowns: tuple[str, ...] = field(default_factory=tuple)

    @property
    def monthly_equivalent(self) -> Decimal:
        """The instalment spread across the months it covers.

        A convenience for budgeting, not a payment schedule. Nobody pays this amount
        monthly; the agency collects `instalment_amount` at `frequency`.
        """
        months_per_period = 12 // PERIODS_PER_YEAR[self.frequency]
        return _round(self.instalment_amount / Decimal(months_per_period))


def _round(value: Decimal) -> Decimal:
    return value.quantize(_PAISE, rounding=ROUND_HALF_UP)


def illustrate(terms: CreditTerms, principal: Decimal | float | int) -> Illustration:
    """Amortise `principal` under `terms`, or refuse and say why."""
    principal = Decimal(str(principal))

    if principal <= 0:
        raise IllustrationRefused("Enter a loan amount above zero.")

    if terms.max_loan is not None and principal > Decimal(str(terms.max_loan)):
        raise IllustrationRefused(
            f"This scheme lends up to Rs {_lakh(terms.max_loan)}. "
            f"For more than that, a different scheme applies."
        )

    rate = Decimal(str(terms.beneficiary_interest_pct))
    if rate <= 0:
        raise IllustrationRefused(
            "This scheme's interest rate is not recorded, so no instalment can be shown."
        )

    per_year = PERIODS_PER_YEAR[terms.instalment_frequency]
    months_per_period = 12 // per_year

    assumptions: list[str] = []
    unknowns: list[str] = []

    # The moratorium is INSIDE the repayment period, which is how every NSFDC page
    # words it: "within a maximum period of three years ... including a 3-month
    # moratorium period". So paying time is what is left after it.
    paying_months = terms.repayment_months
    if terms.moratorium_months is not None:
        paying_months = terms.repayment_months - terms.moratorium_months
        if paying_months <= 0:
            raise IllustrationRefused(
                "This scheme's moratorium is as long as its repayment period, so an "
                "instalment cannot be worked out from what the source states."
            )
    else:
        unknowns.append(
            "This scheme states its moratorium as a period that depends on your "
            "course, so the figures below assume repayment starts immediately."
        )

    if terms.moratorium_interest is MoratoriumInterest.NOT_STATED:
        unknowns.append(
            "The scheme does not say whether interest is charged during the "
            "moratorium. If it is, the real total will be higher than shown."
        )
    elif terms.moratorium_interest is MoratoriumInterest.ACCRUES:
        unknowns.append(
            "Interest is charged during the moratorium. That accrual is not included "
            "below, so the real total will be higher."
        )

    # Whole instalments only. A part-period at the end is not something the corpus can
    # describe, so the count is floored and the shortfall noted rather than smeared.
    count = paying_months // months_per_period
    if count < 1:
        raise IllustrationRefused(
            "The repayment period is shorter than one instalment, so there is nothing "
            "to work out."
        )
    if count * months_per_period != paying_months:
        assumptions.append(
            f"Rounded down to {count} whole "
            f"{terms.instalment_frequency.value.lower()} instalments."
        )

    periodic_rate = rate / Decimal(100) / Decimal(per_year)
    growth = (Decimal(1) + periodic_rate) ** count
    instalment = principal * periodic_rate * growth / (growth - Decimal(1))
    instalment = _round(instalment)

    total = _round(instalment * count)
    return Illustration(
        principal=_round(principal),
        annual_rate_pct=rate,
        frequency=terms.instalment_frequency,
        instalment_count=count,
        instalment_amount=instalment,
        total_repayable=total,
        total_interest=_round(total - principal),
        repayment_months=terms.repayment_months,
        moratorium_months=terms.moratorium_months,
        assumptions=tuple(assumptions),
        unknowns=tuple(unknowns),
    )


def max_loan_for_project(terms: CreditTerms, project_cost: Decimal | float | int) -> Decimal:
    """The most this scheme will lend against a project of that cost.

    Two limits, and the smaller wins: the financed share (NSFDC funds up to 90% of
    project cost) and the scheme's own ceiling. Conflating them is the mistake that
    tells someone she can borrow Rs 1.40 lakh under a scheme that stops at Rs 1.25.
    """
    project_cost = Decimal(str(project_cost))
    if project_cost <= 0:
        raise IllustrationRefused("Enter a project cost above zero.")

    limits = []
    if terms.financed_share_pct is not None:
        limits.append(project_cost * Decimal(str(terms.financed_share_pct)) / Decimal(100))
    if terms.max_loan is not None:
        limits.append(Decimal(str(terms.max_loan)))
    if not limits:
        raise IllustrationRefused(
            "This scheme records no lending limit, so the most it will lend is unknown."
        )
    return _round(min(limits))


def _lakh(amount: float) -> str:
    """Format a rupee figure the way the source pages write it."""
    value = Decimal(str(amount)) / Decimal(100000)
    trimmed = value.quantize(_PAISE).normalize()
    return f"{trimmed} lakh"
