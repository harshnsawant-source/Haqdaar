"""Deterministic slot-fill rendering, and T4 — the anti-hallucination net.

Design doc s5 guarantee 5 / guard doc s3-T4. No generative model runs after the
verdict, so there is no free-text claim to police. T4 is therefore two mechanical
assertions rather than a natural-language check:

* **Build time** (`audit_templates`) — no template string carries a factual claim that
  is not a bound slot. Operationally: template prose may contain no digits, and no
  banned hedging phrase. Every number a citizen reads must arrive through a slot that
  traces to a predicate.
* **Runtime** (`render_card`) — every `{slot}` in the chosen template resolves to a
  value carried by the verdict, and any slot carrying clause text matches a predicate's
  `clause_text` verbatim. An unbound or orphan slot voids the whole response.

"Voids" means raises. A card that cannot be proven is not rendered at all — degrading
to a blank or a placeholder would be exactly the silent failure this design forbids.
"""

from __future__ import annotations

import math
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from haqdaar.corpus.schema import GroupKind, NumericBound, Scheme, VerificationStatus
from haqdaar.eligibility.aggregate import UnlockOption
from haqdaar.eligibility.verdict import (
    ApprovalStatus,
    Evaluation,
    Predicate,
    Status,
    Verdict,
)
from haqdaar.guard.gate import GateResult
from haqdaar.guard.triggers import TriggerId

TEMPLATE_DIR = Path(__file__).parent / "templates"

#: Phrasings banned outright. These are the disease this project is curing: they sound
#: helpful and commit to nothing, and a citizen cannot act on them.
BANNED_PHRASES = (
    "you may qualify",
    "you might qualify",
    "it is possible that",
    "generally speaking",
    "it seems",
    "probably",
    "should be eligible",
)

_SLOT = re.compile(r"\{([a-z_]+)\}")
_DIGIT = re.compile(r"\d")


class RenderError(Exception):
    """A card that could not be rendered from the verdict. Never show a partial card."""


class RenderedCard(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme_id: str
    status: Status
    lines: list[str] = Field(default_factory=list)
    #: Rendered separately so the UI can colour it differently (guard doc s3-T2/T1).
    approval_lines: list[str] = Field(default_factory=list)
    banners: list[str] = Field(default_factory=list)

    def text(self) -> str:
        return "\n".join([*self.lines, *self.approval_lines, *self.banners])


@lru_cache(maxsize=None)
def load_templates(language: str = "en") -> dict[str, str]:
    path = TEMPLATE_DIR / f"{language}.yaml"
    if not path.is_file():
        raise RenderError(f"no template set for language {language!r}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {k: " ".join(str(v).split()) for k, v in raw.items()}


# --- T4, build time ---------------------------------------------------------


def audit_templates(language: str = "en") -> None:
    """Assert no template carries an unbound factual claim. Raises on violation.

    A digit in template prose is the tell: ages, amounts, years and counts are facts,
    and facts must arrive through slots that trace back to the corpus.
    """
    for key, template in load_templates(language).items():
        prose = _SLOT.sub("", template)
        if _DIGIT.search(prose):
            raise RenderError(
                f"{language}:{key} contains a literal number outside a slot — every "
                "number must arrive through a slot bound to the verdict"
            )
        lowered = prose.lower()
        for phrase in BANNED_PHRASES:
            if phrase in lowered:
                raise RenderError(f"{language}:{key} contains banned phrase {phrase!r}")


# --- T4, runtime ------------------------------------------------------------


def _fill(
    key: str,
    templates: dict[str, str],
    slots: dict[str, object],
    clause_texts: set[str],
) -> str:
    template = templates.get(key)
    if template is None:
        raise RenderError(f"no template {key!r}")

    required = set(_SLOT.findall(template))
    missing = required - set(slots)
    if missing:
        raise RenderError(
            f"{key}: slot(s) {sorted(missing)} unbound — the verdict carries no value "
            "for them, so this response is void"
        )

    for name in required:
        value = slots[name]
        if value is None or str(value) == "":
            raise RenderError(f"{key}: slot {name!r} resolved empty; response void")
        if name == "clause_text" and str(value) not in clause_texts:
            raise RenderError(
                f"{key}: clause_text does not match any predicate in the verdict "
                "verbatim; response void"
            )

    text = template
    for name in required:
        text = text.replace("{" + name + "}", str(slots[name]))

    lowered = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            raise RenderError(f"{key}: rendered output contains banned phrase {phrase!r}")
    return text


def _field_label(profile_field: str) -> str:
    return profile_field.rsplit(".", 1)[-1].replace("_", " ")


def _bound_text(bound: object) -> str | None:
    """Describe a numeric bound using only its own sourced numbers."""
    if not isinstance(bound, NumericBound):
        return None
    if bound.min is not None and bound.max is not None:
        return f"{_num(bound.min)} to {_num(bound.max)}"
    if bound.min is not None:
        return f"{_num(bound.min)} and above"
    if bound.max is not None:
        return f"{_num(bound.max)} and below"
    return None


def _num(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def render_card(
    result: GateResult,
    scheme: Scheme,
    *,
    today: date,
    language: str = "en",
    unlock: UnlockOption | None = None,
) -> RenderedCard:
    """Render one verdict. Takes a GateResult, so unvalidated output cannot reach here.

    `unlock` comes from the aggregator and supplies the "unlocks N more" count. Without
    it the blocked card names the one scheme it can prove, and never a count.
    """
    templates = load_templates(language)
    verdict = result.verdict
    clause_texts = {p.clause_text for p in verdict.predicates}
    by_group = {g.group_id: g for g in verdict.group_results}

    def eligibility_predicates() -> list[Predicate]:
        return [
            p
            for p in verdict.predicates
            if by_group[p.group_id].kind is GroupKind.ELIGIBILITY
        ]

    base = {
        "scheme_name": scheme.name,
        "source_url": scheme.source_url,
        "filing_office": scheme.filing_office or scheme.portal_url,
        "office": scheme.filing_office or scheme.portal_url,
    }
    lines: list[str] = []

    if verdict.status is Status.ELIGIBLE:
        lines.append(_fill("eligible.headline", templates, base, clause_texts))
        lines.append(_fill("eligible.proof_intro", templates, base, clause_texts))
        for predicate in eligibility_predicates():
            if predicate.evaluation is not Evaluation.TRUE:
                continue
            slots = {**base, "clause_text": predicate.clause_text}
            lines.append(_fill("eligible.proof_line", templates, slots, clause_texts))
            if predicate.evidence is not None:
                lines.append(
                    _fill(
                        "eligible.evidence_line",
                        templates,
                        {**base, "document": _label(predicate.evidence.document_id)},
                        clause_texts,
                    )
                )
        lines.append(_fill("eligible.proof_source", templates, base, clause_texts))
        if base["filing_office"]:
            lines.append(_fill("eligible.next_step", templates, base, clause_texts))

    elif verdict.status is Status.NOT_ELIGIBLE:
        lines.append(_fill("not_eligible.headline", templates, base, clause_texts))
        lines.extend(_not_eligible_reason(verdict, scheme, templates, base, clause_texts, today))

    elif verdict.status is Status.BLOCKED_ON_DOCUMENT:
        lines.append(_fill("blocked.headline", templates, base, clause_texts))
        document = _label(verdict.unlocking_docs[0]) if verdict.unlocking_docs else None
        if document is None:
            raise RenderError(f"{verdict.scheme_id}: blocked with no unlocking document")
        if unlock is not None and unlock.unlock_count > 1:
            lines.append(
                _fill(
                    "blocked.multiple",
                    templates,
                    {**base, "document": document, "count": unlock.unlock_count},
                    clause_texts,
                )
            )
        else:
            lines.append(
                _fill(
                    "blocked.single",
                    templates,
                    {**base, "document": document},
                    clause_texts,
                )
            )
        blocking = next(
            (
                p
                for p in eligibility_predicates()
                if p.evaluation is Evaluation.UNKNOWN and p.verifiable_from
            ),
            None,
        )
        if blocking is not None:
            lines.append(
                _fill(
                    "blocked.rule",
                    templates,
                    {**base, "clause_text": blocking.clause_text},
                    clause_texts,
                )
            )

    elif verdict.status is Status.UNVERIFIABLE:
        lines.append(_fill("unverifiable.headline", templates, base, clause_texts))
        unsettleables = [
            p
            for p in eligibility_predicates()
            if p.evaluation is Evaluation.UNKNOWN and not p.is_settleable
        ]
        if not unsettleables:
            raise RenderError(f"{verdict.scheme_id}: UNVERIFIABLE with no unsettleable clause")
        unsettleable = unsettleables[0]
        if unsettleable.decided_by:
            lines.append(
                _fill(
                    "unverifiable.reason_discretionary",
                    templates,
                    {**base, "decider": unsettleable.decided_by},
                    clause_texts,
                )
            )
        else:
            lines.append(
                _fill("unverifiable.reason_dataset", templates, base, clause_texts)
            )
        lines.append(
            _fill(
                "unverifiable.rule",
                templates,
                {**base, "clause_text": unsettleable.clause_text},
                clause_texts,
            )
        )
        # Quoting one of six criteria without saying so would imply it is the only one.
        if len(unsettleables) > 1:
            lines.append(
                _fill(
                    "unverifiable.also_unsettleable",
                    templates,
                    {**base, "count": len(unsettleables) - 1},
                    clause_texts,
                )
            )
        if base["office"]:
            lines.append(_fill("unverifiable.next_step", templates, base, clause_texts))
            lines.append(_fill("unverifiable.promise", templates, base, clause_texts))

    approval_lines = _render_approval(verdict, templates, base, clause_texts)
    banners = _render_banners(result, scheme, templates, base, clause_texts)

    return RenderedCard(
        scheme_id=verdict.scheme_id,
        status=verdict.status,
        lines=lines,
        approval_lines=approval_lines,
        banners=banners,
    )


def render_outside_corpus(language: str = "en") -> RenderedCard:
    """T3's card: no scheme, no clause, no verdict — so no claim of any kind.

    This is the backup refusal ("How much tax do I owe?"). It names nothing it cannot
    show, which is why it takes no slots at all.
    """
    templates = load_templates(language)
    return RenderedCard(
        scheme_id="",
        status=Status.UNVERIFIABLE,
        lines=[
            _fill("unverifiable.headline", templates, {}, set()),
            _fill("unverifiable.outside_corpus", templates, {}, set()),
        ],
    )


def _render_approval(
    verdict: Verdict,
    templates: dict[str, str],
    base: dict[str, object],
    clause_texts: set[str],
) -> list[str]:
    """The approval split, rendered beside eligibility and never instead of it."""
    approval = verdict.approval
    if approval is None or approval.status is ApprovalStatus.SETTLED:
        return []

    lines = [_fill("approval.headline", templates, base, clause_texts)]
    if approval.deciders:
        lines.append(
            _fill(
                "approval.refusal",
                templates,
                {**base, "decider": approval.deciders[0]},
                clause_texts,
            )
        )
    clause = next(
        (p for p in verdict.predicates if p.clause_id in approval.clause_ids), None
    )
    if clause is not None:
        lines.append(
            _fill(
                "approval.rule",
                templates,
                {**base, "clause_text": clause.clause_text},
                clause_texts,
            )
        )
    return lines


def _render_banners(
    result: GateResult,
    scheme: Scheme,
    templates: dict[str, str],
    base: dict[str, object],
    clause_texts: set[str],
) -> list[str]:
    banners: list[str] = []
    for finding in result.findings_for(TriggerId.T5_STALE_RULE):
        banners.append(
            _fill(
                "staleness.banner",
                templates,
                {**base, "retrieved_on": finding.retrieved_on},
                clause_texts,
            )
        )
        if finding.last_amended:
            banners.append(
                _fill(
                    "staleness.amended",
                    templates,
                    {**base, "last_amended": finding.last_amended},
                    clause_texts,
                )
            )
    if scheme.verification_status is VerificationStatus.PROVISIONAL:
        banners.append(_fill("provisional.banner", templates, base, clause_texts))
    return banners


def _not_eligible_reason(
    verdict: Verdict,
    scheme: Scheme,
    templates: dict[str, str],
    base: dict[str, object],
    clause_texts: set[str],
    today: date,
) -> list[str]:
    """Name the failing bound, and the year they become eligible when we can compute it.

    The year is arithmetic over two sourced numbers (the rule's lower bound and the age
    read from her document), not a prediction. It is emitted only for an age bound; for
    anything else the sentence is omitted rather than guessed at.
    """
    clauses = {c.clause_id: c for c in scheme.clauses()}
    failing = next(
        (p for p in verdict.predicates if p.evaluation is Evaluation.FALSE), None
    )
    if failing is None or failing.evidence is None:
        return []

    clause = clauses.get(failing.clause_id)
    bound_text = _bound_text(clause.bound) if clause else None
    if bound_text is None or clause is None or clause.profile_field is None:
        return []

    lines = [
        _fill(
            "not_eligible.reason",
            templates,
            {
                **base,
                "bound_text": bound_text,
                "field_label": _field_label(clause.profile_field),
                "value": failing.evidence.extracted_value,
            },
            clause_texts,
        )
    ]

    value = failing.evidence.extracted_value
    if (
        clause.profile_field.endswith("age")
        and isinstance(clause.bound, NumericBound)
        and clause.bound.min is not None
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value < clause.bound.min
    ):
        years = math.ceil(clause.bound.min - value)
        lines.append(
            _fill(
                "not_eligible.becomes_eligible",
                templates,
                {**base, "year": today.year + years},
                clause_texts,
            )
        )
    return lines


def _label(document_id: str) -> str:
    return document_id.replace("_", " ")
