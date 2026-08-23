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

ATTRIBUTION, and the one judgement call in this module
-----------------------------------------------------
Intake also asks which documents she actually holds. A stated fact is attributed to one
of those documents when the corpus accepts it as proof for that clause — she is
asserting both the fact and that she can evidence it, which is what an intake desk
records. We have not seen the document, so every such field is marked
`FieldOrigin.DECLARED` and every intake result carries a banner saying so. A field
attributed to `self_declaration` is her word alone and settles only what her word can.
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


class IntakeSpec(_Frozen):
    version: int
    sections: list[IntakeSection] = Field(min_length=1)

    def questions(self) -> list[IntakeQuestion]:
        return [q for s in self.sections for q in s.questions]

    def answerable_fields(self) -> set[str]:
        return {q.profile_field for q in self.questions() if q.profile_field}

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
    documents_held: list[str] | None = None,
    profile_id: str = "intake",
) -> CitizenProfile:
    """Turn answers into a profile. Attribution is explained in the module docstring."""
    documents_held = documents_held or []
    fields: dict[str, ProfileField] = {}

    for question in spec.questions():
        if not question.profile_field:
            continue
        if question.question_id not in answers:
            continue
        value = answers[question.question_id]
        if value is None or value == "":
            continue  # unanswered is unknown, and unknown is a real answer

        accepted = accepted_documents(schemes, question.profile_field)
        # Prefer a document she says she holds; fall back to her word alone.
        evidenced_by = next((d for d in accepted if d in documents_held), None)
        document = evidenced_by or SELF_DECLARATION

        fields[question.profile_field] = ProfileField(
            value=value,
            document_id=document,
            source_field=question.question_id,
            # She told us. We have not seen the paper, and the UI says so.
            confidence=1.0,
            origin=FieldOrigin.DECLARED,
        )

    return CitizenProfile(profile_id=profile_id, fields=fields)
