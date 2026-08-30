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
from haqdaar.eligibility.compare import ComparedScheme
from haqdaar.eligibility.verdict import Evaluation, Status
from haqdaar.guard.gate import GateResult
from haqdaar.render.labels import document_label, field_label
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
    #: Its citizen-facing name. The UI renders this verbatim and never derives prose
    #: from an id itself — identifiers are the engine's to name.
    document_label: str | None = None
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
    #: T6. The scheme's own operating window, rendered ahead of everything else.
    window_lines: list[str] = Field(default_factory=list)
    #: OPEN | LAPSED | NOT_YET_OPEN, or None when the scheme declares no window.
    window_state: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    unlocking_docs: list[str] = Field(default_factory=list)
    staleness_flag: bool = False
    #: True when this card has an approval refusal to show beside its eligibility.
    has_approval_split: bool = False
    portal_url: str | None = None
    filing_office: str | None = None
    #: Where these rules came from and when we last read them. Present on every card,
    #: not only stale ones: "last verified" is the claim the proof beat rests on, and a
    #: citizen should be able to see it without the answer having to go wrong first.
    source_url: str | None = None
    authority: str | None = None
    retrieved_on: str | None = None
    last_amended: str | None = None
    #: Scheme-interaction results, computed by resolve_interactions. Pass-through: the
    #: UI groups stacking schemes so two halves of one payment are never shown as two
    #: independent benefits (01-DEMO-CORPUS.md s2, IGNWPS + SGNAY).
    stack_group_id: str | None = None
    claimable: bool = True
    subsumed_by_scheme: str | None = None
    #: True when the corpus holds credit terms for this scheme, so the UI knows whether
    #: a repayment panel belongs on the card at all. A pension has nothing to repay and
    #: must never be offered a calculator.
    lends: bool = False


class CompareResponse(BaseModel):
    """A comparison table. Structure only, and deliberately no "best fit".

    Picking a winner would need facts nobody here holds: what each benefit is worth to
    this person, how long each office takes, whether she can travel to the filing
    office. See eligibility/compare.py for the full reasoning.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    vertical: str
    #: None when no persona was supplied: a plain fact table, not an evaluated one.
    persona_id: str | None = None
    schemes: list[ComparedScheme] = Field(default_factory=list)
    stacked_groups: list[list[str]] = Field(default_factory=list)


class UnderstoodPayload(BaseModel):
    """One fact read from her sentence, with the words that produced it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    question_id: str
    #: The prompt she will see for this, so the UI can say what it understood without
    #: composing a sentence of its own.
    prompt: str
    value: bool | int | float | str
    #: The value as a citizen reads it: "yes" rather than "true", "widow" rather than
    #: WIDOW, translated. The raw `value` stays for seeding the form.
    display: str
    #: The exact substring of her text. Shown to her always: a pre-filled answer with
    #: no visible cause is indistinguishable from a guess.
    phrase: str


class UnderstandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(max_length=2000)
    language: str = "en"


class UnderstandResponse(BaseModel):
    """What her words were read to say. Never a verdict, never a scheme."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: None means "we could not tell" and the UI must ask, not guess.
    vertical: str | None = None
    answers: dict[str, bool | int | float | str] = Field(default_factory=dict)
    understood: list[UnderstoodPayload] = Field(default_factory=list)


class NeedPayload(BaseModel):
    """One need-based door, already resolved to the vertical that can answer it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    need_id: str
    label: str
    vertical: str
    #: What this need already establishes, to seed the form. Answers, never evidence.
    answers: dict[str, bool | int | float | str] = Field(default_factory=dict)


class NeedsResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    language: str
    #: The vertical filter that was applied, or None when every need is returned.
    vertical: str | None = None
    needs: list[NeedPayload] = Field(default_factory=list)


class UnlockPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    #: The name shown on the "one document away" chip. Computed by render/labels.py so
    #: the headline and the card underneath it can never spell the same paper two ways.
    document_label: str
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
    source_document_label: str


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
                source_document_label=document_label(f.source_document),
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


class ExtractedFieldPayload(BaseModel):
    """One profile fact, with how it got there. The origin is never hidden."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_field: str
    #: Citizen-facing name for profile_field. The UI must not show a dotted path.
    label: str
    value: bool | int | float | str
    confidence: float
    origin: str
    document_id: str
    document_label: str
    source_field: str


class ExtractionReportPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    document_type: str
    engine: str
    ocr_available: bool
    readable: bool
    #: Fields the rules looked for and could not read or could not trust.
    unread: list[str] = Field(default_factory=list)
    #: The same list, named for a citizen.
    unread_labels: list[str] = Field(default_factory=list)


class ExtractResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    persona_id: str
    vertical: str
    mode: str
    #: True when any displayed value was typed into a fixture rather than read.
    fixture_backed: bool
    ocr_available: bool
    reports: list[ExtractionReportPayload] = Field(default_factory=list)
    fields: list[ExtractedFieldPayload] = Field(default_factory=list)
    cards: list[CardPayload] = Field(default_factory=list)
    unlock: UnlockPayload | None = None


class IntakeOptionPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: str
    label: str


class IntakeQuestionPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_id: str
    type: str
    prompt: str
    profile_field: str | None = None
    options: list[IntakeOptionPayload] = Field(default_factory=list)
    #: For the documents question: id plus the engine's name for it.
    documents: list[IntakeOptionPayload] = Field(default_factory=list)
    min: float | None = None
    max: float | None = None


class IntakeSectionPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    section_id: str
    title: str
    questions: list[IntakeQuestionPayload] = Field(default_factory=list)


class IntakeFormResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int
    language: str
    #: None means every section; otherwise only this domain's.
    vertical: str | None = None
    sections: list[IntakeSectionPayload] = Field(default_factory=list)


class IntakeRequest(BaseModel):
    """What the citizen answered. Values only — nothing is interpreted."""

    model_config = ConfigDict(extra="forbid")

    vertical: str
    answers: dict[str, bool | int | float | str | None] = Field(default_factory=dict)
    documents_held: list[str] = Field(default_factory=list)
    language: str = "en"


class IntakeResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    vertical: str
    #: Always true: intake answers are the citizen's own account.
    declared: bool = True
    #: The engine-rendered sentence saying so. The UI shows this, never its own.
    declared_banner: str
    #: Documents she said she holds. NOT evidence — nothing here changed a verdict.
    #: Served so the UI can point her at the upload step for papers she already has.
    documents_held: list[IntakeOptionPayload] = Field(default_factory=list)
    #: Documents that would unlock something AND that she says she already holds. This
    #: is the whole point of an intake screen: "you have these — upload them."
    ready_to_upload: list[IntakeOptionPayload] = Field(default_factory=list)
    fields: list[ExtractedFieldPayload] = Field(default_factory=list)
    cards: list[CardPayload] = Field(default_factory=list)
    unlock: UnlockPayload | None = None


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
        window_lines=list(card.window_lines),
        window_state=verdict.window.state.value if verdict.window else None,
        source_url=scheme.source_url,
        lends=scheme.credit_terms is not None,
        authority=scheme.authority,
        retrieved_on=scheme.retrieved_on.isoformat(),
        last_amended=scheme.last_amended.isoformat() if scheme.last_amended else None,
        citations=[
            Citation(
                clause_id=p.clause_id,
                clause_text=p.clause_text,
                source_url=p.source_url,
                evaluation=p.evaluation,
                document_id=p.evidence.document_id if p.evidence else None,
                document_label=(
                    document_label(p.evidence.document_id) if p.evidence else None
                ),
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
        stack_group_id=verdict.stack_group_id,
        claimable=verdict.claimable,
        subsumed_by_scheme=verdict.subsumed_by_scheme,
    )


def to_unlock(option: UnlockOption | None) -> UnlockPayload | None:
    if option is None:
        return None
    return UnlockPayload(
        document_id=option.document_id,
        document_label=document_label(option.document_id),
        count=option.unlock_count,
        scheme_ids=list(option.unlocks),
    )


class EmiResponse(BaseModel):
    """One repayment illustration for one scheme.

    Deliberately NOT part of a card. A verdict says whether she qualifies; this says
    what the money would cost if she borrows. Keeping them on separate endpoints keeps
    them separate ideas, and means no card can accidentally start quoting a price.
    """

    scheme_id: str
    scheme_name: str
    principal: float
    annual_rate_pct: float
    frequency: str
    instalment_count: int
    instalment_amount: float
    monthly_equivalent: float
    total_repayable: float
    total_interest: float
    repayment_months: int
    moratorium_months: int | None
    max_loan: float | None
    #: Verbatim scheme wording the figures came from, so the arithmetic is citable the
    #: same way a verdict is.
    terms_text: str
    source_url: str
    #: What we had to decide because the source did not.
    assumptions: list[str]
    #: What the source never said, and which moves the real number.
    unknowns: list[str]


class PartnerPayload(BaseModel):
    name: str
    address: str | None
    state: str | None
    category: str
    category_label: str


class PartnersResponse(BaseModel):
    """Where to take one scheme, for one state.

    SIH26092 component three. `cannot_rank` is not an error field and is present on
    every successful response: the problem statement asks for partners filtered by fund
    utilisation and NPA, NSFDC publishes neither, and the UI is required to say so
    wherever it shows a partner.
    """

    scheme_id: str
    scheme_name: str
    state: str | None
    #: The partner type the scheme itself names, which for NSFDC credit is the State
    #: Channelising Agency.
    primary: list[PartnerPayload]
    #: Banks and other Channelising Agencies in the same state.
    also: list[PartnerPayload]
    #: Every state the partner corpus can place, for the picker.
    states: list[str]
    #: Partners held whose state the source did not make readable. Counted, never shown
    #: under a state we cannot support.
    unplaced: int
    #: Verbatim routing wording, cited the way a clause is.
    quote: str
    also_quote: str
    source_url: str
    cannot_rank: str
