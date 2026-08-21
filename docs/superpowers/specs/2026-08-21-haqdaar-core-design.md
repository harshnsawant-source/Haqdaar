# Haqdaar CORE (A + A+) — Architecture Design

**Date:** 2026-08-21
**Scope:** CORE only — A (Eligibility Engine) and A+ (Agentic Action Layer).
**Not in this spec:** legal vertical (E, stretch), disaster response (D, roadmap slide), portal/payment integration, voice, WhatsApp, login, admin.
**Sources of truth:** scope — `PROJECT-BRIEF.md` §4 · guard behaviour — `02-GUARD-DESIGN.md` · corpus contents and schema requirements — `01-DEMO-CORPUS.md` §8.

**Revised 2026-08-21 (post-review).** Six fixes applied so the spec is internally consistent before day 1:
1. Rendering is locked to **deterministic template slot-fill** — no generative model produces a sentence the citizen reads (was ambiguously "model writes the sentences"). §1, §2, §5.
2. **T4 is now a structural slot-binding check**, not a natural-language claim-matcher — cheap and provable instead of "the fiddliest." §5, §6.
3. Added the **unlock aggregator** that computes "one document away from K more." §5, §6.
4. Added **scheme-interaction resolution** (`subsumed_by` / `stacks_with`) in the evaluator. §4, §5.
5. The retrieval floor is **biased to refuse on ambiguity**. §5, §6.
6. Upload uses **live OCR with a confidence-gated fixture fallback** — genuinely reads the document, never pure animation. §7, §10.

The matching consistency edits to `02-GUARD-DESIGN.md` (§2, §3-T4, §6, §7) are applied.

---

## 1. The governing decision

The eligibility verdict is decided by neither a language model nor vector search. Code decides it; the model and the retriever decide nothing.

Six schemes and roughly twenty-five clauses is a structured rule set, not a haystack. If eligibility is decided by "retrieve chunks, ask the model," the refusal becomes a prompt behaviour and fails confidently on stage. So the engine splits into two lanes:

- **Deterministic lane** — pure code, no generative model, fully unit-testable: corpus → predicate evaluator → `Verdict` → Guard → template renderer → screen.
- **Model lane** — exactly **one generative call site**, temperature 0: documents → `CitizenProfile` (extraction, at the input boundary only). **Nothing the citizen reads is written by a model.** The verdict is turned into sentences by deterministic slot-fill over a fixed, human-translated template set; the model never phrases a verdict.

Retrieval exists, but it uses an embedding model for **query routing and trigger T3 only** — it never generates and never answers. It maps a free-text question to candidate `scheme_id`s and reports "nothing above the similarity floor," which is what makes the out-of-corpus refusal a *retrieval fact* rather than a model opinion. `clause_text` is never retrieved-and-summarised; it is copied verbatim from the corpus into the verdict, so a citation cannot drift from its source.

One generative call, at the input boundary only, means every fact the citizen sees is produced by code from typed data. That is why the anti-hallucination guarantee (T4) is **structural** rather than a post-hoc check, and why the whole output path is deterministic and snapshot-testable.

---

## 2. Locked decisions

| Decision | Choice | Why |
|---|---|---|
| Engine stack | Python 3.11 + FastAPI + pytest | OCR tooling, deterministic evaluator, golden tests |
| UI stack | React + Vite, mobile-first | Stitch designs implement cleanly; kept separate from the engine |
| Model provider | Cloud now, `llm/adapter.py` with a local Ollama implementation | Speed now; the offline claim gets proven on real hardware before 2 Sept or is downgraded to a vision slide honestly (judge Q6) |
| Output rendering | Deterministic slot-fill over a fixed, human-translated template set. **No generative model at render time.** | Makes T4 (no hallucination) a structural guarantee; makes every citizen-facing sentence snapshot-testable; removes the "model phrases the verdict" risk entirely |
| A+ output | Filled PDF of the real PM-KISAN form | Strongest stage moment; submission clearly labelled as simulated (judge Q4) |
| Languages | English + Marathi | Matches the Sunita persona and the Maharashtra corpus; one human translation pass over the fixed template set |

---

## 3. Folder structure

```
haqdaar/
├── corpus/                       # DATA, not code. This is the platform bet.
│   ├── schemes/
│   │   ├── sgnay.yaml
│   │   ├── ignwps.yaml
│   │   ├── pm-kisan.yaml
│   │   ├── pmjay.yaml
│   │   ├── avvc.yaml
│   │   └── pmay-g.yaml           # CONDITIONAL — only if the SOP is read end to end (§9)
│   ├── forms/
│   │   ├── pm-kisan.form.yaml    # form field -> profile path map
│   │   └── pm-kisan.blank.pdf    # the real government form
│   └── personas/sunita.json      # checked-in fixture profile
│
├── engine/
│   ├── haqdaar/
│   │   ├── corpus/       schema.py · loader.py
│   │   ├── profile/      schema.py · extract.py · ocr.py
│   │   ├── retrieval/    index.py · route.py
│   │   ├── eligibility/  verdict.py · evaluate.py · aggregate.py
│   │   ├── guard/        triggers.py · citation.py · gate.py
│   │   ├── render/       templates/{en,mr}/ · render.py
│   │   ├── action/       fill.py · track.py
│   │   ├── llm/          adapter.py · cloud.py · local.py
│   │   └── api/          app.py
│   └── tests/
│       ├── golden/       # 5 locked schemes (+PMAY-G if verified) x Sunita + 2 refusal fixtures
│       └── unit/         # one file per trigger T1-T5 + aggregator + interactions
│
├── web/                          # mobile-first UI, four card states
└── docs/superpowers/specs/
```

A vertical is a corpus folder plus a template set. Adding the legal vertical later requires **zero engine change** — that is the platform claim in §3 of the brief, made structurally true rather than rehearsed.

---

## 4. Data contracts

### Scheme (corpus YAML)

Fields are non-negotiable; each was forced by a real rule in `01-DEMO-CORPUS.md` §8.

```
Scheme:
  scheme_id, name, authority, benefit, source_url, retrieved_on, last_amended
  portal_url, filing_office
  clauses[]:
    clause_id
    clause_text        # verbatim, never paraphrased
    rule_type          # numeric_bound | enumerated_category | income_threshold
                       # | external_dataset | exclusion
    bound              # typed: {min,max} | [values] | {max_value,currency,period}
    profile_field      # which CitizenProfile path this predicate reads
    verifiable_from    # document ids that can supply it; [] = never citizen-obtainable
    note               # e.g. stale-threshold flag for SGNAY Rs 21,000
  stacks_with[] / subsumed_by[]   # scheme_ids; resolved by evaluate.py (see §5 guarantee 6)
```

`verifiable_from: []` is what makes PM-JAY D3 a permanent UNKNOWN. That single empty list is the on-stage refusal.

### CitizenProfile

Typed and schema-validated. Every field carries provenance:

```
ProfileField { value, document_id, source_field, confidence }
```

A field with no `document_id` cannot support a TRUE or FALSE predicate. Enforced by the type, not by convention. `confidence` gates the OCR fallback in §7.

### Verdict

Per `02-GUARD-DESIGN.md` §2:

```
Verdict   { scheme_id, status, predicates[], unlocking_docs[], staleness_flag }
status    ELIGIBLE | NOT_ELIGIBLE | UNVERIFIABLE | BLOCKED_ON_DOCUMENT
Predicate { clause_text, source_url, retrieved_on, evaluation, evidence }
evaluation TRUE | FALSE | UNKNOWN
evidence  { document_id, field, extracted_value } | null
```

**Invariant:** a predicate is TRUE or FALSE only if `evidence` is non-null; otherwise UNKNOWN. `evaluation` is written by `eligibility/evaluate.py` and by nothing else — no model output can become a truth value.

---

## 5. Flow

```
 docs / 4 answers ──► [EXTRACTOR  model, temp 0] ──► CitizenProfile (typed, validated)
                                                          │   (low-confidence field → fixture fallback, §7)
 query (mr/en) ──────► [ROUTER  retrieval] ──► candidate scheme_ids
                            │ nothing above similarity floor ──────► T3 → UNVERIFIABLE
                            │ (floor biased to refuse on ambiguity)
                            ▼
                     [EVALUATOR  pure code]      profile × clauses
                            │  resolves subsumed_by / stacks_with
                            ▼
                     Verdict[] { status, predicates[], unlocking_docs[] }
                            ▼
                     [AGGREGATOR  pure code]   group BLOCKED verdicts by missing doc
                            │                  → "one <doc> unlocks N"
                            ▼
              ╔═════════ GUARD  T1–T5 ═════════╗   fail ──► forced refusal verdict
                            ▼                          (timeout lands here too)
                     [RENDERER  deterministic slot-fill over fixed templates — NO model]
                            ▼
                     [T4 slot-binding check: every slot bound from the verdict]
                            ▼
              UI card: ELIGIBLE · NOT_ELIGIBLE · BLOCKED_ON_DOCUMENT · UNVERIFIABLE
                            │ citizen picks a scheme
                            ▼
                     [ACTION  form map → filled PDF + gap list + tracking ref (SIMULATED)]
```

Structural guarantees:

1. The renderer accepts a `ValidatedVerdict` type it cannot construct itself. There is no code path from an unvalidated verdict to the screen.
2. `BLOCKED_ON_DOCUMENT` and `UNVERIFIABLE` render in different colours with different copy. Conflating them destroys both the "one document away" beat and the refusal beat.
3. Any exception or model timeout produces an UNVERIFIABLE verdict, never a hang. A network failure on stage then looks like the product working as designed.
4. The renderer enforces a phrase blocklist ("you may qualify", "it is possible that", "generally speaking"). Those phrasings are the disease being cured.
5. **Output is produced only by deterministic slot-fill over the fixed template set. No generative model runs after the verdict.** T4 is therefore a build-time assertion (no template string carries a factual claim that is not a bound slot) plus a runtime assertion (every slot in the chosen template resolves from the verdict), not a natural-language parse.
6. **Scheme interactions resolve in `evaluate.py`.** A scheme named in another's `subsumed_by` is not shown as separately claimable; `stacks_with` schemes are grouped so benefit totals are never double-counted. (Instance: IGNWPS + SGNAY.)
7. **The unlock aggregator is computed, not narrated.** `aggregate.py` groups `BLOCKED_ON_DOCUMENT` verdicts by the missing document and ranks by how many schemes each one unlocks — that is exactly what produces "one caste certificate away from 4 more." It reads off the verdict set; it is not a phrasing the model chose.
8. **The retrieval floor is biased to refuse.** A query that lands between clearly-in-corpus and clearly-out resolves to UNVERIFIABLE (T3), never to a confident answer. A false refusal is on-brand; a false confident answer is disqualifying. Judges are never handed an open text box — redirect to the six rehearsed schemes (`02-GUARD-DESIGN.md` §5, "the trap to avoid").

---

## 6. Guard triggers

All five are pure functions over the verdict object, each with its own unit test file.

- **T1 Unsupported predicate** — UNKNOWN with `verifiable_from: []` → UNVERIFIABLE. Instance: PM-JAY D3 / SECC 2011. This is the demo refusal.
- **T2 Missing but obtainable** — UNKNOWN with a named obtainable document → BLOCKED_ON_DOCUMENT, document appended to `unlocking_docs`. Instance: IGNWPS BPL status. The aggregator (§5 guarantee 7) turns a set of these into the "one document away from K more" headline.
- **T3 No retrieval support** — router returned nothing above the floor → UNVERIFIABLE, reason "outside corpus." The floor is biased to refuse: anything not clearly matching a corpus scheme resolves UNVERIFIABLE rather than guessing. Instance: the tax-liability backup query.
- **T4 Citation integrity** — output is deterministic slot-fill over a fixed template set, so there is no free-text model claim to police. The guarantee is two assertions: **(build time)** no template string contains a factual claim that is not a bound slot; **(runtime)** every slot in the chosen template resolves to a value carried by a predicate in the verdict, and that value's `clause_text` is present verbatim. An unbound or orphan slot voids the whole response. Structural, not an NLI check — which is why it is cheap and provable rather than "the fiddliest."
- **T5 Stale or amended rule** — `last_amended` newer than `retrieved_on`, or `retrieved_on` outside a configured window → answer shown with a visible staleness banner.

---

## 7. Testing

- **Golden verdict tests.** Sunita against the five locked schemes (plus PMAY-G only if it is verified per §9) and the two refusal queries, asserting exact `status` and the exact predicate set. Red test means no deploy. Run as the last action before walking on stage.
- **Trigger unit tests.** One file per trigger, plus one for the aggregator and one for scheme-interaction resolution. Written before 30 Aug.
- **Rendering is deterministic, so assert it directly.** Because no model runs at render time, golden tests assert the exact rendered `en` and `mr` strings for each card state — no snapshot fuzz, no temperature.
- **Live OCR, fixture as gated fallback.** On demo day the upload runs the real OCR + extraction path and genuinely populates the profile. Any field whose `confidence` is below threshold falls back to the checked-in `sunita.json` value, and the profile is flagged as partially fixture-backed. The upload is never pure animation: if a judge asks "did it actually read the document," the honest answer is yes, with a named fallback for low-confidence fields. OCR variance is the likeliest thing to break the demo, which is why the fallback exists — but the demo is not built on pretending OCR ran.
- **Pinned extraction prompt, temperature 0**, with the extraction output snapshotted.
- **Rehearse the failure.** A test asserts the timeout path emits UNVERIFIABLE.

---

## 8. Build order (21 Aug → 30 Aug freeze)

| Day | Build | Done means |
|---|---|---|
| 1 | Corpus schema + SGNAY & IGNWPS encoded + `Verdict`/`Predicate` + evaluator | First two golden tests pass, no model involved |
| 2 | PM-KISAN, PM-JAY, AVVC encoded + T1/T2 + `unlocking_docs` + aggregator + `subsumed_by`/`stacks_with` resolution | The stage refusal fires from real corpus data; "one doc unlocks N" computes |
| 3 | T4 slot-binding check (structural, cheap) + English templates + T3/T5 | Guard complete; project de-risked |
| 4 | FastAPI endpoints + web shell, four card states | Clickable demo on the fixture profile |
| 5 | A+ on PM-KISAN only: form map, PDF fill, tracking reference (labelled SIMULATED) | The action beat exists |
| 6 | Extraction path: OCR + model → profile, live populate with confidence-gated fixture fallback | Upload genuinely reads the doc and cannot break the demo |
| 7 | Marathi templates, human-translated, plus polish | Demo language complete |
| 8–9 | Harden, rehearse, local-model check on constrained hardware | Build freeze 30 Aug |

Rationale: the Guard and evaluator are the product. UI and extraction are replaceable. By end of day 3 the thing that wins the room exists; everything after is presentation.

---

## 9. Out of scope for CORE

Legal vertical, disaster response, real portal submission, schemes beyond the six, voice, WhatsApp, accounts, admin dashboards. PMAY-G is included only if a teammate reads `SOP_AwaasPlus2024.pdf` end to end — unverified rules are worse than no rules.

---

## 10. Open items owned outside the engine lane

These block content, not architecture. Tracked here so they do not get lost.

- Document lists for SGNAY and IGNWPS are marked `[VERIFY AT SOURCE]` in the corpus doc. The engine can encode `verifiable_from` provisionally, but the demo cannot claim a document list that nobody opened.
- PM-KISAN blank form PDF must be obtained before day 5.
- Marathi translation of the template set — human, not model, and not live on stage.
- **Marathi-language documents** (income certificate, 7/12 extract) are harder to OCR than English. The confidence-gated fixture fallback (§7) covers this, but do not claim clean Marathi OCR unless it is tested on the real document images.
- Treatment of a 70+ person already covered under standard PM-JAY is unverified. Do not guess on stage.
