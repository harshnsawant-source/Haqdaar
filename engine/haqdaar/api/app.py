"""FastAPI surface. Thin on purpose.

Every endpoint does the same three things: load a vertical's corpus, run the
deterministic pipeline, serialize what came out. No branching on model output, because
there is no model in this path at all — the whole request is reproducible from the
checked-in corpus and persona fixtures.

Day 4 serves the checked-in fixture profiles. The OCR/extraction path is day 6; the
API shape does not change when it lands, because a profile is a profile.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.formparsers import MultiPartParser

from haqdaar.api.uploads import (
    MAX_UPLOAD_BYTES,
    UploadRejected,
    check_content_length,
    check_count,
    check_type,
    read_bounded,
)

# Keep an accepted upload in memory rather than on disk. Starlette spools a multipart
# part to a temp file once it exceeds this threshold; raising it to our own per-file
# cap means a file we accept never touches the filesystem, which is what lets the
# no-persistence test below be true rather than aspirational.
MultiPartParser.spool_max_size = MAX_UPLOAD_BYTES
MultiPartParser.max_part_size = MAX_UPLOAD_BYTES

from haqdaar.action.fill import ActionRefused, fill_form, missing_documents
from haqdaar.action.track import submit
from haqdaar.corpus.forms import load_form_for
from haqdaar.corpus.loader import load_corpus
from haqdaar.corpus.schema import Scheme
from haqdaar.eligibility.aggregate import best_unlock
from haqdaar.eligibility.evaluate import evaluate_corpus, evaluate_scheme
from haqdaar.guard.gate import gate, gate_all
from haqdaar.profile.extract import ExtractionMode, build_profile, extract_document
from haqdaar.profile.intake import build_intake_profile, load_intake
from haqdaar.profile.ocr import tesseract_available
from haqdaar.profile.schema import CitizenProfile, load_profile
from haqdaar.guard.triggers import t3_no_retrieval_support
from haqdaar.render.labels import document_label, field_label
from haqdaar.render.render import load_templates
from haqdaar.render.render import (
    audit_templates,
    render_action,
    render_card,
    render_outside_corpus,
)
from haqdaar.retrieval.route import route

from haqdaar.api.schemas import (
    ActionResponse,
    CardPayload,
    EvaluateResponse,
    ExtractedFieldPayload,
    ExtractionReportPayload,
    ExtractResponse,
    IntakeFormResponse,
    IntakeOptionPayload,
    IntakeQuestionPayload,
    IntakeRequest,
    IntakeResponse,
    IntakeSectionPayload,
    PersonaSummary,
    to_action,
    to_payload,
    to_unlock,
)

CORPUS_ROOT = Path(
    os.environ.get("HAQDAAR_CORPUS", Path(__file__).resolve().parents[3] / "corpus")
)

#: Which vertical each persona belongs to. Verticals are folders; this is the index.
PERSONAS = {
    "entrepreneur-01": "entrepreneur",
    "entrepreneur-02": "entrepreneur",
    "sunita": "welfare",
}

@asynccontextmanager
async def lifespan(_: FastAPI):
    """T4's build-time half, run before the server can serve anything.

    A template carrying an unbound factual claim must stop the process, not surface
    as a bad card mid-demo.
    """
    audit_templates("en")
    yield


app = FastAPI(
    title="Haqdaar",
    version="0.4.0",
    summary="Proof, not answers. It refuses. It acts.",
    lifespan=lifespan,
)

# The PWA is served from a different origin in dev (Vite on 5173). Localhost only:
# there is no deployment story for this round and no secret to leak.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _today() -> date:
    """Overridable so tests pin the clock and staleness stays deterministic."""
    override = os.environ.get("HAQDAAR_TODAY")
    return date.fromisoformat(override) if override else date.today()


def _load_vertical(vertical: str) -> list[Scheme]:
    schemes = load_corpus(CORPUS_ROOT / vertical / "schemes")
    if not schemes:
        raise HTTPException(status_code=503, detail=f"no corpus for {vertical}")
    return schemes


def _load_persona(persona_id: str) -> tuple[str, CitizenProfile]:
    vertical = PERSONAS.get(persona_id)
    if vertical is None:
        raise HTTPException(status_code=404, detail=f"unknown persona {persona_id}")
    path = CORPUS_ROOT / vertical / "personas" / f"{persona_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"missing fixture {persona_id}")
    return vertical, load_profile(path)


def _cards_for(profile: CitizenProfile, schemes: list[Scheme], today: date):
    """Run the pipeline and serialize. Shared so /evaluate and /extract cannot drift."""
    verdicts = evaluate_corpus(schemes, profile)
    unlock = best_unlock(verdicts)
    by_id = {s.scheme_id: s for s in schemes}
    cards = [
        to_payload(
            result,
            by_id[result.verdict.scheme_id],
            render_card(
                result, by_id[result.verdict.scheme_id], today=today, unlock=unlock
            ),
        )
        for result in gate_all(verdicts, schemes, today=today)
    ]
    return cards, unlock


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"ok": True, "verticals": sorted(set(PERSONAS.values()))}


@app.get("/api/personas", response_model=list[PersonaSummary])
def personas() -> list[PersonaSummary]:
    summaries: list[PersonaSummary] = []
    for persona_id, vertical in PERSONAS.items():
        _, profile = _load_persona(persona_id)
        summaries.append(
            PersonaSummary(
                persona_id=persona_id,
                vertical=vertical,
                description=profile.description or persona_id,
            )
        )
    return summaries


def _intake_spec():
    return load_intake(CORPUS_ROOT / "intake.yaml")


def _text(mapping: dict[str, str], language: str) -> str:
    """Prompt text in the requested language, falling back to English.

    The fallback is deliberate and visible: an untranslated prompt shows the English
    with its [NEEDS HUMAN TRANSLATION] marker rather than a blank question.
    """
    return mapping.get(language) or mapping["en"]


@app.get("/api/intake", response_model=IntakeFormResponse)
def intake_form(vertical: str | None = None, language: str = "en") -> IntakeFormResponse:
    """The question set for one domain, as declared in corpus/intake.yaml.

    Scoped by vertical because asking someone who came for business capital about
    widowhood, BPL status and landholding is noise, and asking a pension applicant
    whether this is their first business is worse. Which sections belong to which
    domain is declared in the YAML, not split here.
    """
    if vertical is not None and vertical not in set(PERSONAS.values()):
        raise HTTPException(status_code=404, detail=f"unknown vertical {vertical}")

    spec = _intake_spec()
    return IntakeFormResponse(
        version=spec.version,
        language=language,
        vertical=vertical,
        sections=[
            IntakeSectionPayload(
                section_id=section.section_id,
                title=_text(section.title, language),
                questions=[
                    IntakeQuestionPayload(
                        question_id=q.question_id,
                        type=q.type,
                        prompt=_text(q.prompt, language),
                        profile_field=q.profile_field,
                        options=[
                            IntakeOptionPayload(
                                value=o.value, label=_text(o.label, language)
                            )
                            for o in q.options
                        ],
                        documents=[
                            IntakeOptionPayload(value=d, label=document_label(d))
                            for d in q.documents
                        ],
                        min=q.min,
                        max=q.max,
                    )
                    for q in section.questions
                ],
            )
            for section in spec.sections_for(vertical)
        ],
    )


@app.post("/api/intake", response_model=IntakeResponse)
def intake(request: IntakeRequest) -> IntakeResponse:
    """Answers in, the same cards as every other entry point out.

    The decision path is untouched: intake produces an ordinary CitizenProfile and
    hands it to the same evaluator, Guard and renderer. What an answer is worth is
    decided by the corpus — `evaluate.py` checks evidence provenance, so a declaration
    settles exactly the clauses a declaration is allowed to settle and a
    certificate-gated clause stays blocked.
    """
    if request.vertical not in set(PERSONAS.values()):
        raise HTTPException(
            status_code=404, detail=f"unknown vertical {request.vertical}"
        )

    schemes = _load_vertical(request.vertical)
    spec = _intake_spec()
    # documents_held is deliberately NOT passed to build_intake_profile. What she says
    # she holds is not evidence of what it says; it only tells the UI which papers she
    # could upload next.
    profile = build_intake_profile(spec, dict(request.answers), schemes=schemes)
    cards, unlock = _cards_for(profile, schemes, _today())

    held = list(request.documents_held)
    blocking = [d for card in cards for d in card.unlocking_docs]
    ready = [d for d in held if d in blocking]

    return IntakeResponse(
        vertical=request.vertical,
        declared_banner=load_templates(request.language)["intake.declared_banner"],
        documents_held=[
            IntakeOptionPayload(value=d, label=document_label(d)) for d in held
        ],
        ready_to_upload=[
            IntakeOptionPayload(value=d, label=document_label(d))
            for d in dict.fromkeys(ready)
        ],
        fields=[
            ExtractedFieldPayload(
                profile_field=path,
                label=field_label(path),
                value=field.value,
                confidence=field.confidence,
                origin=field.origin.value,
                document_id=field.document_id,
                document_label=document_label(field.document_id),
                source_field=field.source_field,
            )
            for path, field in sorted(profile.fields.items())
        ],
        cards=cards,
        unlock=to_unlock(unlock),
    )


@app.post("/api/extract", response_model=ExtractResponse)
async def extract(
    request: Request,
    persona_id: str = Form(...),
    mode: str = Form(ExtractionMode.FIXTURE_BACKED.value),
    document_types: list[str] = Form(default=[]),
    files: list[UploadFile] = File(default=[]),
) -> ExtractResponse:
    """Read uploaded documents, then run the same pipeline on what was read.

    Nothing about the verdict path changes: extraction produces a CitizenProfile and
    that profile flows through the same evaluator, Guard and template renderer as a
    checked-in fixture would. A field the reader could not trust simply is not there,
    so it resolves UNKNOWN and the existing refusal logic handles it.

    `mode` is explicit and echoed back. LIVE shows only what was read; FIXTURE_BACKED
    fills the rest from the checked-in persona and labels every borrowed field. The
    caller chooses; the UI shows which happened. Neither is ever silently substituted.
    """
    try:
        check_content_length(request.headers.get("content-length"))
        check_count(files, document_types)
    except UploadRejected as rejected:
        raise HTTPException(
            status_code=rejected.status_code, detail=rejected.detail
        ) from None

    try:
        extraction_mode = ExtractionMode(mode)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"unknown mode {mode!r}") from None

    vertical, fixture = _load_persona(persona_id)
    schemes = _load_vertical(vertical)
    today = _today()

    reports = []
    for upload, document_type in zip(files, document_types):
        try:
            payload = await read_bounded(upload)
            check_type(upload, payload)
        except UploadRejected as rejected:
            raise HTTPException(
                status_code=rejected.status_code, detail=rejected.detail
            ) from None
        reports.append(
            extract_document(
                payload,
                document_type=document_type,
                documents_dir=CORPUS_ROOT / "documents",
                document_id=document_type,
            )
        )

    profile = build_profile(
        reports, profile_id=persona_id, fixture=fixture, mode=extraction_mode
    )
    cards, unlock = _cards_for(profile, schemes, today)

    return ExtractResponse(
        persona_id=persona_id,
        vertical=vertical,
        mode=extraction_mode.value,
        fixture_backed=profile.is_fixture_backed,
        ocr_available=tesseract_available(),
        reports=[
            ExtractionReportPayload(
                document_id=r.document_id,
                document_type=r.document_type,
                engine=r.engine,
                ocr_available=r.ocr_available,
                readable=r.readable,
                unread=list(r.unread),
                unread_labels=[field_label(f) for f in r.unread],
            )
            for r in reports
        ],
        fields=[
            ExtractedFieldPayload(
                profile_field=path,
                label=field_label(path),
                value=field.value,
                confidence=field.confidence,
                origin=field.origin.value,
                document_id=field.document_id,
                document_label=document_label(field.document_id),
                source_field=field.source_field,
            )
            for path, field in sorted(profile.fields.items())
        ],
        cards=cards,
        unlock=to_unlock(unlock),
    )


@app.post("/api/act", response_model=ActionResponse)
def act(persona_id: str, scheme_id: str) -> ActionResponse:
    """Fill the application for one eligible scheme. SIMULATED, end to end.

    Refuses with 409 when the engine did not clear eligibility: you do not file an
    application for someone the Guard could not clear. Nothing here touches a network,
    a portal, or a login, and it will not start to.
    """
    vertical, profile = _load_persona(persona_id)
    schemes = _load_vertical(vertical)
    today = _today()

    scheme = next((s for s in schemes if s.scheme_id == scheme_id), None)
    if scheme is None:
        raise HTTPException(status_code=404, detail=f"unknown scheme {scheme_id}")

    form = load_form_for(CORPUS_ROOT / vertical / "forms", scheme_id)
    if form is None:
        raise HTTPException(
            status_code=404, detail=f"no application form for {scheme_id}"
        )

    verdict = evaluate_scheme(scheme, profile)
    gate(verdict, scheme, today=today)  # never act on an unvalidated verdict

    try:
        filled_form = fill_form(form, verdict, profile)
    except ActionRefused as refusal:
        raise HTTPException(status_code=409, detail=str(refusal)) from refusal

    receipt = submit(filled_form, persona_id, today)
    rendered = render_action(filled_form, receipt, scheme)
    return to_action(
        filled_form, receipt, rendered, scheme, missing_documents(filled_form)
    )


@app.get("/api/evaluate", response_model=EvaluateResponse)
def evaluate(persona_id: str, query: str | None = None) -> EvaluateResponse:
    """Run the full pipeline for one persona and return rendered cards.

    With a `query`, routing runs first: if nothing clears the similarity floor, T3
    fires and the response is the outside-corpus refusal with no cards at all. That
    refusal is a retrieval fact, not a judgement.
    """
    vertical, profile = _load_persona(persona_id)
    schemes = _load_vertical(vertical)
    today = _today()

    considered = schemes
    if query:
        routed = route(query, schemes)
        if t3_no_retrieval_support(routed) is not None:
            card = render_outside_corpus()
            return EvaluateResponse(
                persona_id=persona_id,
                vertical=vertical,
                query=query,
                outside_corpus=True,
                cards=[
                    CardPayload(
                        scheme_id="",
                        scheme_name="",
                        status=card.status,
                        verification_status="PROVISIONAL",
                        lines=list(card.lines),
                    )
                ],
            )
        considered = [s for s in schemes if s.scheme_id in routed.scheme_ids]

    cards, unlock = _cards_for(profile, considered, today)

    return EvaluateResponse(
        persona_id=persona_id,
        vertical=vertical,
        query=query,
        cards=cards,
        unlock=to_unlock(unlock),
    )
