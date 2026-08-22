# Corpus

Data, not code. The engine is corpus-agnostic by design: a vertical is a folder of
scheme YAML plus a template set. Swapping the entrepreneur corpus for the welfare
corpus — the "same engine, new rules" reveal — must require **zero engine change**.

```
<vertical>/schemes/    one YAML per scheme, validated by engine/haqdaar/corpus/schema.py
<vertical>/personas/   checked-in fixture profiles (typed facts + provenance)
<vertical>/forms/      blank application PDFs + field maps (day 5)
```

Verticals: `entrepreneur/` is the primary demo (SIH26092), `welfare/` is the reveal.

---

## PROVISIONAL vs VERIFIED

Every scheme and every clause carries `verification_status` and `verify_note`.

- **`VERIFIED`** — a human has opened the official source and transcribed the rule
  verbatim. Only these may appear in a demo or on a slide.
- **`PROVISIONAL`** — placeholder. `clause_text` **must** contain the literal marker
  `[VERIFY AT SOURCE]`; the schema rejects the file otherwise.

`load_corpus(dir, strict=True)` returns VERIFIED schemes only. As of 2026-08-21 that
is an empty list, and `tests/unit/test_corpus_loader.py` asserts it. The assertion is
a tripwire, not decoration: it changes the day the content lane lands a real rule.

### Promoting a scheme to VERIFIED

1. Open the official source. Not a news article, not a summary, not an LLM.
2. Replace each `clause_text` with the verbatim official wording, marker removed.
3. Set `source_url` to the exact page, and `retrieved_on` to the date you opened it.
4. Set `last_amended` if the source states one (drives the T5 staleness banner).
5. Fill `verifiable_from` with the documents that actually evidence the clause.
6. Flip `verification_status` to `VERIFIED` on the clause and, once every clause is
   done, on the scheme.
7. Run `pytest engine/tests` — golden tests will fail because clause text changed.
   Read every diff before updating them. That failure is the system working.

### If you cannot source a figure, leave the clause out

Do not guess and do not "approximate." An absent clause makes the engine under-claim,
which is our accepted failure mode (judge Q&A Q3). An invented clause makes the demo a
lie. `nsfdc-term-loan.yaml` deliberately has **no income-ceiling clause** for exactly
this reason — the addendum says a ceiling exists but names no figure.

---

## Day 3 state

The corpus is now split by **vertical** — that is what makes "same engine, new corpus"
a folder swap rather than a claim:

```
corpus/
  entrepreneur/   PRIMARY (SIH26092)   schemes/ personas/ forms/
  welfare/        REVEAL vertical      schemes/ personas/
```

Nothing is demo-usable: every scheme in both verticals is PROVISIONAL.

| Vertical | Scheme | Persona | Verdict |
|---|---|---|---|
| entrepreneur | `stand-up-india` | entrepreneur-01 | ELIGIBLE with proof |
| entrepreneur | `nsfdc-term-loan` | entrepreneur-01 | ELIGIBLE + approval UNVERIFIABLE |
| entrepreneur | both | entrepreneur-02 | BLOCKED → one caste certificate unlocks 2 |
| welfare | `pmjay` | sunita | UNVERIFIABLE (SECC 2011, all six criteria) |
| welfare | `avvc` | sunita | NOT_ELIGIBLE — rule is 70+, she is 60, eligible 2036 |

Those five cover all four citizen-facing voices. `income_threshold`, `exclusion` and
staleness are covered by synthetic fixtures in `engine/tests/unit/` rather than by
inventing corpus clauses to exercise them.

---

## Approval is not eligibility (resolved day 2)

Every clause group carries `kind: ELIGIBILITY | APPROVAL`. It defaults to
`ELIGIBILITY`, so existing groups need no edit — but **any group holding a
discretionary clause must declare `kind: APPROVAL`, and the loader rejects the file
otherwise.**

```yaml
  - group_id: sanction
    kind: APPROVAL          # <- required when the group holds a discretionary clause
    satisfy: ALL
    clauses:
      - clause_id: NSF-C2
        rule_type: discretionary
        decided_by: "the lending institution's credit appraisal"
```

Why it is enforced rather than merely advised: a discretionary clause inside an
eligibility group drags a provably eligible applicant to UNVERIFIABLE and hides the
entitlement we could have proven — the opposite of the product. The schema makes that
shape unrepresentable.

| | eligibility | approval |
|---|---|---|
| `Verdict.status` | rolled up from ELIGIBILITY groups only | never affected |
| `Verdict.approval` | — | `UNVERIFIABLE`, naming `decided_by` |

So `entrepreneur-01` reads **ELIGIBLE, with her full proof chain**, plus a separate
refusal on approval. She keeps the proof; the bank keeps its discretion.

**Rule when writing the real corpus:** keep eligibility determinable. A discretionary
step (bank appraisal, credit assessment, officer's discretion) goes in an APPROVAL
group. Never inside eligibility.

---

## Repo location

This repo currently lives inside OneDrive. `.gitignore` keeps `.venv/`,
`__pycache__/` and `.pytest_cache/` out of sync, which removes the worst of the churn,
but OneDrive can still lock files mid-write and corrupt `.git/` objects.

**Ideally move the repo outside OneDrive** (e.g. `C:\dev\haqdaar`) before the crunch
week. Losing git history on 29 August is a failure mode with no recovery.
