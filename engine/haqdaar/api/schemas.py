"""Wire format. Assembles what the deterministic renderer already produced.

The API phrases nothing. Every human-readable string in a payload came out of
`render/render.py` by slot-fill over the human-translated template set, and every
`clause_text` is verbatim corpus. If a sentence could be constructed here, T4's
guarantee would end at the network boundary — so it cannot be.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from haqdaar.action.fill import FilledForm, Receipt
from haqdaar.corpus.schema import Scheme, VerificationStatus
from haqdaar.eligibility.aggregate import UnlockOption
from haqdaar.eligibility.verdict import Evaluation, Status
from haqdaar.guard.gate import GateResult
from haqdaar.render.render import RenderedAction, RenderedCard


class Citation(BaseModel):
    """One rule clause, quoted verbatim, with the page it came from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    clause_id: str
    clause_text: str
    source_url: str
    evaluation: Evaluation
    #: The document that proved it, when one did.
    document_id: str | None = None
    #: Who decides, for a discretionary clause. Never a document.
    decided_by: str | None = None
    settleable: bool = True


class CardPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme_id: str
    scheme_name: str
    status: Status
    verification_status: VerificationStatus
    #: Rendered sentences. The UI displays these; it never composes its own.
    lines: list[str] = Field(default_factory=list)
    approval_lines: list[str] = Field(default_factory=list)
    banners: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    unlocking_docs: list[str] = Field(default_factory=list)
    staleness_flag: bool = False
    #: True when this card has an approval refusal to show beside its eligibility.
    has_approval_split: bool = False
    portal_url: str | None = None
    filing_office: str | None = None


class UnlockPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    count: int
    scheme_ids: list[str] = Field(default_factory=list)


class EvaluateResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    persona_id: str
    vertical: str
    query: str | None = None
    #: True when T3 fired: nothing in the corpus answers the question.
    outside_corpus: bool = False
    cards: list[CardPayload] = Field(default_factory=list)
    unlock: UnlockPayload | None = None


class FilledFieldPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field_id: str
    label: str
    value: bool | int | float | str
    source_document: str


class GapFieldPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field_id: str
    label: str
    obtainable_from: list[str] = Field(default_factory=list)
    note: str | None = None


class ActionResponse(BaseModel):
    """A simulated filing. Every flag here exists to stop it reading as a real one."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme_id: str
    scheme_name: str
    form_id: str
    #: Literal True on the wire as well as in the engine.
    simulated: Literal[True] = True
    is_stand_in: bool = True
    reference: str
    submitted_on: str
    lines: list[str] = Field(default_factory=list)
    gap_lines: list[str] = Field(default_factory=list)
    banners: list[str] = Field(default_factory=list)
    filled: list[FilledFieldPayload] = Field(default_factory=list)
    gaps: list[GapFieldPayload] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)


def to_action(
    filled_form: FilledForm,
    receipt: Receipt,
    rendered: RenderedAction,
    scheme: Scheme,
    missing: list[str],
) -> ActionResponse:
    return ActionResponse(
        scheme_id=filled_form.scheme_id,
        scheme_name=scheme.name,
        form_id=filled_form.form_id,
        is_stand_in=filled_form.is_stand_in,
        reference=receipt.reference,
        submitted_on=receipt.submitted_on.isoformat(),
        lines=list(rendered.lines),
        gap_lines=list(rendered.gap_lines),
        banners=list(rendered.banners),
        filled=[
            FilledFieldPayload(
                field_id=f.field_id,
                label=f.label,
                value=f.value,
                source_document=f.source_document,
            )
            for f in filled_form.filled
        ],
        gaps=[
            GapFieldPayload(
                field_id=g.field_id,
                label=g.label,
                obtainable_from=list(g.obtainable_from),
                note=g.note,
            )
            for g in filled_form.gaps
        ],
        missing_documents=list(missing),
    )


class PersonaSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    persona_id: str
    vertical: str
    description: str


def to_payload(result: GateResult, scheme: Scheme, card: RenderedCard) -> CardPayload:
    """Serialize one rendered card. Copies strings; never builds them."""
    verdict = result.verdict
    return CardPayload(
        scheme_id=verdict.scheme_id,
        scheme_name=scheme.name,
        status=verdict.status,
        verification_status=verdict.verification_status,
        lines=list(card.lines),
        approval_lines=list(card.approval_lines),
        banners=list(card.banners),
        citations=[
            Citation(
                clause_id=p.clause_id,
                clause_text=p.clause_text,
                source_url=p.source_url,
                evaluation=p.evaluation,
                document_id=p.evidence.document_id if p.evidence else None,
                decided_by=p.decided_by,
                settleable=p.is_settleable,
            )
            for p in verdict.predicates
        ],
        unlocking_docs=list(verdict.unlocking_docs),
        staleness_flag=verdict.staleness_flag,
        has_approval_split=bool(card.approval_lines),
        portal_url=scheme.portal_url,
        filing_office=scheme.filing_office,
    )


def to_unlock(option: UnlockOption | None) -> UnlockPayload | None:
    if option is None:
        return None
    return UnlockPayload(
        document_id=option.document_id,
        count=option.unlock_count,
        scheme_ids=list(option.unlocks),
    )
