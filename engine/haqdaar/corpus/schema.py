"""Typed corpus schema.

A vertical is a corpus folder plus a template set (design doc s3). Everything the
engine knows about a scheme lives in YAML validated by these models, so swapping the
welfare corpus for the entrepreneur corpus is a data edit and not an engine change.

Two rules are enforced here rather than left to discipline:

1. A PROVISIONAL clause must carry the [VERIFY AT SOURCE] marker in its clause_text.
   Unverified rules cannot silently read as fact.
2. Clauses that no citizen document can ever settle (external_dataset, discretionary)
   may not name a profile_field or a verifiable_from document. They are permanently
   UNKNOWN by construction, which is what makes the refusal structural.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

VERIFY_MARKER = "[VERIFY AT SOURCE]"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PROVISIONAL = "PROVISIONAL"


class RuleType(str, Enum):
    NUMERIC_BOUND = "numeric_bound"
    ENUMERATED_CATEGORY = "enumerated_category"
    INCOME_THRESHOLD = "income_threshold"
    EXCLUSION = "exclusion"
    EXTERNAL_DATASET = "external_dataset"
    DISCRETIONARY = "discretionary"


#: Rule types no citizen-held document can ever settle. Always UNKNOWN.
UNSETTLEABLE_RULE_TYPES = frozenset(
    {RuleType.EXTERNAL_DATASET, RuleType.DISCRETIONARY}
)


class Satisfy(str, Enum):
    ALL = "ALL"
    ANY = "ANY"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class NumericBound(_Frozen):
    """Inclusive numeric range. Either end may be open."""

    min: float | None = None
    max: float | None = None


class CategoryBound(_Frozen):
    """Membership in an enumerated set, compared as strings."""

    values: list[str] = Field(min_length=1)


class IncomeBound(_Frozen):
    max_value: float
    currency: str = "INR"
    period: str = "ANNUAL"


Bound = NumericBound | CategoryBound | IncomeBound

#: Which bound shape each rule type requires. EXCLUSION accepts any shape because an
#: exclusion can be categorical ("income tax payers") or numeric ("pension >= 10000").
_BOUND_FOR_RULE: dict[RuleType, tuple[type, ...]] = {
    RuleType.NUMERIC_BOUND: (NumericBound,),
    RuleType.ENUMERATED_CATEGORY: (CategoryBound,),
    RuleType.INCOME_THRESHOLD: (IncomeBound,),
    RuleType.EXCLUSION: (NumericBound, CategoryBound, IncomeBound),
}


class Clause(_Frozen):
    clause_id: str
    clause_text: str
    rule_type: RuleType
    verification_status: VerificationStatus
    verify_note: str
    profile_field: str | None = None
    bound: Bound | None = None
    verifiable_from: list[str] = Field(default_factory=list)
    #: Only for rule_type=discretionary: who actually decides. Renders as a slot.
    decided_by: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _check(self) -> Clause:
        if self.rule_type in UNSETTLEABLE_RULE_TYPES:
            if self.bound is not None or self.profile_field is not None:
                raise ValueError(
                    f"{self.clause_id}: {self.rule_type.value} clauses are never "
                    "settled from the profile; drop bound and profile_field"
                )
            if self.verifiable_from:
                raise ValueError(
                    f"{self.clause_id}: {self.rule_type.value} clauses must have an "
                    "empty verifiable_from — no document can settle them"
                )
            if self.rule_type is RuleType.DISCRETIONARY and not self.decided_by:
                raise ValueError(
                    f"{self.clause_id}: discretionary clauses must name decided_by"
                )
        else:
            expected = _BOUND_FOR_RULE[self.rule_type]
            if not isinstance(self.bound, expected):
                names = " or ".join(t.__name__ for t in expected)
                raise ValueError(
                    f"{self.clause_id}: rule_type {self.rule_type.value} requires a "
                    f"{names} bound"
                )
            if not self.profile_field:
                raise ValueError(f"{self.clause_id}: profile_field is required")
            if self.decided_by is not None:
                raise ValueError(
                    f"{self.clause_id}: decided_by belongs only on discretionary clauses"
                )

        if (
            self.verification_status is VerificationStatus.PROVISIONAL
            and VERIFY_MARKER not in self.clause_text
        ):
            raise ValueError(
                f"{self.clause_id}: PROVISIONAL clause_text must carry {VERIFY_MARKER}"
            )
        return self


class ClauseGroup(_Frozen):
    """A set of clauses combined under ALL or ANY.

    ANY exists because real rules need it: PM-JAY qualifies a family that meets *at
    least one* of D1..D7. Without it that scheme cannot be encoded at all.
    """

    group_id: str
    satisfy: Satisfy
    clauses: list[Clause] = Field(min_length=1)


class Scheme(_Frozen):
    scheme_id: str
    name: str
    authority: str
    benefit: str
    source_url: str
    retrieved_on: date
    verification_status: VerificationStatus
    verify_note: str
    clause_groups: list[ClauseGroup] = Field(min_length=1)
    last_amended: date | None = None
    portal_url: str | None = None
    filing_office: str | None = None
    #: scheme_ids. Parsed and carried on day 1; resolved by the evaluator on day 2.
    stacks_with: list[str] = Field(default_factory=list)
    subsumed_by: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Scheme:
        seen: set[str] = set()
        for group in self.clause_groups:
            for clause in group.clauses:
                if clause.clause_id in seen:
                    raise ValueError(
                        f"{self.scheme_id}: duplicate clause_id {clause.clause_id}"
                    )
                seen.add(clause.clause_id)
                if (
                    clause.verification_status is VerificationStatus.PROVISIONAL
                    and self.verification_status is not VerificationStatus.PROVISIONAL
                ):
                    raise ValueError(
                        f"{self.scheme_id}: has PROVISIONAL clause {clause.clause_id} "
                        "but is marked VERIFIED"
                    )
        return self

    def clauses(self) -> list[Clause]:
        return [c for g in self.clause_groups for c in g.clauses]
