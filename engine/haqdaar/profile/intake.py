"""Guided intake: structured answers in, CitizenProfile out.

The front door. A citizen describes their situation by answering declared questions,
and what comes out is an ordinary profile that flows through the same evaluator, Guard
and renderer as a document upload or a checked-in fixture. Nothing about the decision
path knows intake exists.

No model, no free text, no interpretation. An answer is recorded, never read.

WHAT AN ANSWER IS WORTH
-----------------------
An answer is a self-declaration. Whether it settles a clause is decided by the corpus,
not here: `eligibility/evaluate.py` checks that a value's document appears in the
clause's `verifiable_from`, so a declaration settles exactly the clauses the rules say
a declaration settles — PM-KISAN's exclusions, for instance, which the real form
collects on the applicant's own account. A clause needing a caste certificate, a BPL
card or a 7/12 extract stays UNKNOWN and becomes BLOCKED_ON_DOCUMENT.

That produces the honest output the product is for: *here is what you are entitled to
on your own account, and here is the paper you need to prove the rest.*

ATTRIBUTION: HER WORD, AND ONLY HER WORD
----------------------------------------
Every fact stated at intake is filed under `self_declaration`. Nothing else. Ticking
"I have a caste certificate" is not evidence of what the certificate says — we have not
read it — so it cannot make a clause resolve.

An earlier version attributed a stated fact to a document she said she held, on the
reasoning that she was asserting both the fact and that she could evidence it. That was
wrong, and its own banner proved it: the banner promises "I have not seen your
documents, so anything that needs a certificate is still marked as needing one", while
the card underneath said "Proven from your caste certificate" about a certificate
nobody had seen. **"Proven" is the strongest word this product uses and it has to stay
earned.** The banner was the half that was right.

Intake still asks which documents she holds, because it is useful — the UI can point
her straight at the upload step for the papers she already has. It just never counts
as evidence.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from haqdaar.corpus.schema import Scheme
from haqdaar.profile.schema import CitizenProfile, FieldOrigin, ProfileField

#: The document id an unevidenced answer is filed under.
SELF_DECLARATION = "self_declaration"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class IntakeOption(_Frozen):
    value: str
    label: dict[str, str]


class IntakeQuestion(_Frozen):
    question_id: str
    type: str  # number | boolean | choice | documents
    prompt: dict[str, str]
    profile_field: str | None = None
    options: list[IntakeOption] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    min: float | None = None
    max: float | None = None


class IntakeSection(_Frozen):
    section_id: str
    title: dict[str, str]
    questions: list[IntakeQuestion] = Field(min_length=1)
    #: Which verticals this section belongs to. Empty means every vertical.
    verticals: list[str] = Field(default_factory=list)

    def applies_to(self, vertical: str | None) -> bool:
        return vertical is None or not self.verticals or vertical in self.verticals


class IntakeSpec(_Frozen):
    version: int
    sections: list[IntakeSection] = Field(min_length=1)

    def sections_for(self, vertical: str | None = None) -> list[IntakeSection]:
        """Only the sections that belong to this domain.

        Someone who came for money to start a business should not be asked about
        widowhood, BPL status or landholding, and someone who came for a pension should
        not be asked whether this is their first business.
        """
        return [s for s in self.sections if s.applies_to(vertical)]

    def questions(self, vertical: str | None = None) -> list[IntakeQuestion]:
        return [q for s in self.sections_for(vertical) for q in s.questions]

    def answerable_fields(self, vertical: str | None = None) -> set[str]:
        return {q.profile_field for q in self.questions(vertical) if q.profile_field}

    def document_options(self) -> list[str]:
        return [d for q in self.questions() for d in q.documents]


def load_intake(path: str | Path) -> IntakeSpec:
    return IntakeSpec.model_validate(
        yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    )


def accepted_documents(schemes: list[Scheme], profile_field: str) -> list[str]:
    """Every document the corpus accepts as proof for any clause using this field."""
    accepted: list[str] = []
    for scheme in schemes:
        for clause in scheme.clauses():
            if clause.profile_field != profile_field:
                continue
            for document in clause.verifiable_from:
                if document not in accepted:
                    accepted.append(document)
    return accepted


def self_declarable_fields(schemes: list[Scheme]) -> set[str]:
    """Fields the corpus says a self-declaration can settle.

    Every one of these must have an intake question, or a citizen would face a clause
    she is entitled to settle on her own account and no way to say so. A test asserts
    it, so adding a scheme cannot silently leave an unanswerable clause behind.
    """
    return {
        clause.profile_field
        for scheme in schemes
        for clause in scheme.clauses()
        if clause.profile_field and SELF_DECLARATION in clause.verifiable_from
    }


def build_intake_profile(
    spec: IntakeSpec,
    answers: dict[str, object],
    *,
    schemes: list[Scheme],
    profile_id: str = "intake",
) -> CitizenProfile:
    """Turn answers into a profile. Every field is her own declaration; see above.

    Note there is no `documents_held` parameter. It used to be here and it used to
    change the answer, which was the bug. What she says she holds is a routing hint for
    the UI, not evidence, so it does not reach the profile at all.
    """
    fields: dict[str, ProfileField] = {}

    for question in spec.questions():
        if not question.profile_field:
            continue
        if question.question_id not in answers:
            continue
        value = answers[question.question_id]
        if value is None or value == "":
            continue  # unanswered is unknown, and unknown is a real answer

        fields[question.profile_field] = ProfileField(
            value=value,
            # Always. A document she says she holds is not a document we have read.
            document_id=SELF_DECLARATION,
            source_field=question.question_id,
            confidence=1.0,
            origin=FieldOrigin.DECLARED,
        )

    return CitizenProfile(profile_id=profile_id, fields=fields)
