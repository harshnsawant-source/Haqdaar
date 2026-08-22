"""Query routing. Picks candidate schemes; never decides a verdict.

Design doc s1: retrieval exists for routing and trigger T3 only. It maps a free-text
question to `scheme_id`s and reports when nothing clears the floor — which is what
makes the out-of-corpus refusal a *retrieval fact* rather than a model opinion.

Scoring is deterministic lexical overlap against scheme name and clause text. No
embeddings, no model, no network. That is not a placeholder for something smarter: with
five to eight schemes there is no haystack, and a scorer whose output can be reproduced
by hand is worth more on stage than one that cannot. An embedding backend can be added
behind `score()` later without touching T3.

The floor is biased to refuse (design doc s5 guarantee 8). A query landing between
clearly-in-corpus and clearly-out resolves outside-corpus. A false refusal is on-brand;
a false confident answer is disqualifying.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from haqdaar.corpus.schema import Scheme

#: Minimum overlap with a scheme before it is considered a candidate at all.
SIMILARITY_FLOOR = 0.18
#: A candidate must also be this much better than pure noise to be trusted alone.
DECISIVE_MARGIN = 0.08

_WORD = re.compile(r"[a-z0-9]+")

#: Words too common in this corpus to carry routing signal.
_STOPWORDS = frozenset(
    """
    a an and any are as at be by can do does for from get have how if in is it me
    my no not of on or that the their there this to what when where which who will
    with would you your applicant scheme rule verify source
    """.split()
)


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOPWORDS and len(w) > 2}


class SchemeScore(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme_id: str
    score: float


class RouteResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str
    scheme_ids: list[str] = Field(default_factory=list)
    scores: list[SchemeScore] = Field(default_factory=list)
    top_score: float = 0.0

    @property
    def outside_corpus(self) -> bool:
        """True when nothing cleared the floor. T3 reads this and nothing else."""
        return not self.scheme_ids


def score(query: str, scheme: Scheme) -> float:
    """Jaccard-style overlap of the query against the scheme's own words.

    Scheme name words count double: "Ayushman Bharat" naming the scheme is a far
    stronger routing signal than a clause happening to share a common word.
    """
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0

    name_tokens = _tokens(f"{scheme.name} {scheme.scheme_id.replace('-', ' ')}")
    body_tokens = _tokens(" ".join(c.clause_text for c in scheme.clauses()))

    name_hits = len(query_tokens & name_tokens)
    body_hits = len(query_tokens & (body_tokens - name_tokens))
    return (2 * name_hits + body_hits) / (2 * len(query_tokens))


def route(
    query: str,
    schemes: list[Scheme],
    *,
    floor: float = SIMILARITY_FLOOR,
    margin: float = DECISIVE_MARGIN,
) -> RouteResult:
    """Rank schemes for a query. Empty `scheme_ids` means outside corpus."""
    scored = sorted(
        (SchemeScore(scheme_id=s.scheme_id, score=score(query, s)) for s in schemes),
        key=lambda s: (-s.score, s.scheme_id),
    )
    top = scored[0].score if scored else 0.0

    # Bias to refuse: a top score that only just clears the floor is ambiguous, and
    # ambiguity resolves to "outside corpus" rather than to a confident match.
    keep: list[str] = []
    if top >= floor + margin:
        keep = [s.scheme_id for s in scored if s.score >= floor]

    return RouteResult(query=query, scheme_ids=keep, scores=scored, top_score=top)
