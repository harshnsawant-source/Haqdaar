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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from haqdaar.action.fill import ActionRefused, fill_form, missing_documents
from haqdaar.action.track import submit
from haqdaar.corpus.forms import load_form_for
from haqdaar.corpus.loader import load_corpus
from haqdaar.corpus.schema import Scheme
from haqdaar.eligibility.aggregate import best_unlock
from haqdaar.eligibility.evaluate import evaluate_corpus, evaluate_scheme
from haqdaar.guard.gate import gate, gate_all
from haqdaar.profile.schema import CitizenProfile, load_profile
from haqdaar.guard.triggers import t3_no_retrieval_support
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

    verdicts = evaluate_corpus(considered, profile)
    unlock = best_unlock(verdicts)
    by_id = {s.scheme_id: s for s in considered}

    cards = [
        to_payload(
            result,
            by_id[result.verdict.scheme_id],
            render_card(
                result,
                by_id[result.verdict.scheme_id],
                today=today,
                unlock=unlock,
            ),
        )
        for result in gate_all(verdicts, considered, today=today)
    ]

    return EvaluateResponse(
        persona_id=persona_id,
        vertical=vertical,
        query=query,
        cards=cards,
        unlock=to_unlock(unlock),
    )
